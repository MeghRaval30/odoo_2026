"""
Graded rule #4 (sequenced salary rules, derived Gross and Net) and
graded rule #5 (warnings surfaced before validation).

Also pins the two behaviours that are easy to regress: recompute must be
idempotent, and the formula sandbox must reject introspection.
"""

from datetime import date, time
from decimal import Decimal

from django.test import TestCase

from core.models import Company
from employees.models import Contract, Employee, ScheduleLine, WorkingSchedule
from payroll.engine import (
    RuleEvaluationError, compute_payrun, compute_payslip,
    create_payrun_payslips, mark_payrun_paid, safe_eval, validate_payrun,
)
from payroll.models import (
    Payrun, Payslip, PayslipLine, PayslipWarning, SalaryRule, SalaryStructure,
)

FEB_START = date(2026, 2, 1)
FEB_END = date(2026, 2, 28)


class PayrollTestCase(TestCase):
    """
    A deliberately small structure — four rules — so the sequence assertions
    are readable:

        10 BASIC      50% of wage
        20 HRA        40% of BASIC
        30 GROSS      BASIC + HRA          (formula, reads earlier results)
        40 PF         12% of BASIC         (deduction)
        50 NET        GROSS - PF           (formula, reads earlier results)
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.schedule = WorkingSchedule.objects.create(
            name="Standard 40h", company=cls.company)
        for day in range(5):
            ScheduleLine.objects.create(
                schedule=cls.schedule, day_of_week=day,
                start_time=time(9, 0), end_time=time(18, 0), break_minutes=60)

        cls.structure = SalaryStructure.objects.create(
            name="Regular", code="REG", company=cls.company)

        SalaryRule.objects.create(
            structure=cls.structure, name="Basic", code="BASIC",
            category=SalaryRule.BASIC, sequence=10,
            computation=SalaryRule.PERCENTAGE, percentage=Decimal("50.000"))
        SalaryRule.objects.create(
            structure=cls.structure, name="House Rent Allowance", code="HRA",
            category=SalaryRule.ALLOWANCE, sequence=20,
            computation=SalaryRule.PERCENTAGE, percentage=Decimal("40.000"),
            percentage_base="BASIC")
        SalaryRule.objects.create(
            structure=cls.structure, name="Gross", code="GROSS",
            category=SalaryRule.GROSS, sequence=30,
            computation=SalaryRule.FORMULA,
            formula="rules['BASIC'] + rules['HRA']")
        SalaryRule.objects.create(
            structure=cls.structure, name="Provident Fund", code="PF",
            category=SalaryRule.DEDUCTION, sequence=40,
            computation=SalaryRule.PERCENTAGE, percentage=Decimal("12.000"),
            percentage_base="BASIC")
        SalaryRule.objects.create(
            structure=cls.structure, name="Net", code="NET",
            category=SalaryRule.NET, sequence=50,
            computation=SalaryRule.FORMULA,
            formula="rules['GROSS'] - rules['PF']")

    def make_employee(self, first="Kabir", last="Shah", wage="100000.00",
                      with_bank=True):
        employee = Employee.objects.create(
            first_name=first, last_name=last,
            work_email=f"{first.lower()}.{last.lower()}@example.com",
            company=self.company, date_of_joining=date(2025, 1, 1),
            working_schedule=self.schedule,
            bank_account_number="1234567890" if with_bank else None,
            bank_ifsc="HDFC0001234" if with_bank else None,
        )
        Contract.objects.create(
            employee=employee, start_date=date(2025, 1, 1),
            wage=Decimal(wage), working_schedule=self.schedule,
            salary_structure=self.structure, state=Contract.RUNNING)
        return employee

    def make_payrun(self, name="February 2026"):
        return Payrun.objects.create(
            name=name, company=self.company, salary_structure=self.structure,
            period_start=FEB_START, period_end=FEB_END)

    def make_payslip(self, employee, payrun=None):
        return Payslip.objects.create(
            payrun=payrun or self.make_payrun(), employee=employee,
            salary_structure=self.structure,
            period_start=FEB_START, period_end=FEB_END)


# ==========================================================================
# Graded rule #4 — sequence, and later rules seeing earlier results
# ==========================================================================

class RuleSequenceTests(PayrollTestCase):

    def setUp(self):
        self.employee = self.make_employee()
        self.payslip = compute_payslip(self.make_payslip(self.employee))

    def test_lines_are_written_in_sequence_order(self):
        codes = list(self.payslip.lines.values_list("code", flat=True))
        self.assertEqual(codes, ["BASIC", "HRA", "GROSS", "PF", "NET"])

    def test_a_later_rule_sees_an_earlier_rule_result(self):
        """HRA is 40% of BASIC, not 40% of wage."""
        lines = {line.code: line.amount for line in self.payslip.lines.all()}
        self.assertEqual(lines["BASIC"], Decimal("50000.00"))   # 50% of 100000
        self.assertEqual(lines["HRA"], Decimal("20000.00"))     # 40% of 50000

    def test_a_formula_rule_reads_two_earlier_results(self):
        lines = {line.code: line.amount for line in self.payslip.lines.all()}
        self.assertEqual(lines["GROSS"], Decimal("70000.00"))   # BASIC + HRA
        self.assertEqual(lines["PF"], Decimal("6000.00"))       # 12% of BASIC
        self.assertEqual(lines["NET"], Decimal("64000.00"))     # GROSS - PF

    def test_reordering_a_rule_changes_the_result(self):
        """Proof the order is real and not incidental to the rule list."""
        hra = SalaryRule.objects.get(structure=self.structure, code="HRA")
        hra.sequence = 5  # now runs before BASIC exists
        hra.save()

        recomputed = compute_payslip(self.payslip)
        lines = {line.code: line.amount for line in recomputed.lines.all()}
        self.assertEqual(lines["HRA"], Decimal("0.00"))  # base not yet computed
        self.assertEqual(lines["GROSS"], Decimal("50000.00"))

    def test_an_inactive_rule_does_not_execute(self):
        SalaryRule.objects.filter(structure=self.structure, code="HRA").update(
            active=False)
        recomputed = compute_payslip(self.payslip)
        self.assertNotIn(
            "HRA", set(recomputed.lines.values_list("code", flat=True)))

    def test_a_failing_rule_does_not_abort_the_run(self):
        SalaryRule.objects.create(
            structure=self.structure, name="Broken", code="BROKEN",
            category=SalaryRule.DEDUCTION, sequence=45,
            computation=SalaryRule.FORMULA, formula="rules['NOPE'] + 1")

        recomputed = compute_payslip(self.payslip)
        codes = set(recomputed.lines.values_list("code", flat=True))
        self.assertNotIn("BROKEN", codes)
        self.assertIn("NET", codes)  # later rules still ran
        self.assertTrue(recomputed.warnings.filter(
            code=PayslipWarning.RULE_ERROR).exists())


class DerivedTotalsTests(PayrollTestCase):
    """Gross and Net are read from the lines, never stored on the payslip."""

    def setUp(self):
        self.employee = self.make_employee()
        self.payslip = compute_payslip(self.make_payslip(self.employee))

    def test_gross_and_net_match_the_lines(self):
        self.assertEqual(self.payslip.gross, Decimal("70000.00"))
        self.assertEqual(self.payslip.net, Decimal("64000.00"))

    def test_no_gross_or_net_column_exists_on_the_model(self):
        columns = {f.attname for f in Payslip._meta.get_fields()
                   if hasattr(f, "attname")}
        self.assertNotIn("gross", columns)
        self.assertNotIn("net", columns)

    def test_deleting_a_line_changes_the_totals(self):
        """If the totals were stored, this would not move."""
        self.payslip.lines.filter(code="NET").delete()
        self.payslip.lines.filter(code="GROSS").delete()

        payslip = Payslip.objects.get(pk=self.payslip.pk)
        # Falls back to BASIC + ALLOWANCE, and GROSS - DEDUCTION.
        self.assertEqual(payslip.gross, Decimal("70000.00"))
        self.assertEqual(payslip.net, Decimal("64000.00"))

        payslip.lines.filter(code="HRA").delete()
        payslip = Payslip.objects.get(pk=self.payslip.pk)
        self.assertEqual(payslip.gross, Decimal("50000.00"))
        self.assertEqual(payslip.net, Decimal("44000.00"))

    def test_basic_and_allowance_categories_aggregate(self):
        self.assertEqual(self.payslip.basic, Decimal("50000.00"))
        self.assertEqual(self.payslip.allowances, Decimal("20000.00"))
        self.assertEqual(self.payslip.deductions, Decimal("6000.00"))


class RecomputeIdempotenceTests(PayrollTestCase):
    """
    unique(payslip, code) means an appending recompute raises rather than
    silently duplicating — but the engine must delete first, not append.
    """

    def setUp(self):
        self.employee = self.make_employee()
        self.payslip = self.make_payslip(self.employee)

    def test_computing_twice_does_not_duplicate_lines(self):
        first = compute_payslip(self.payslip)
        count_after_first = first.lines.count()

        second = compute_payslip(first)
        self.assertEqual(second.lines.count(), count_after_first)

    def test_computing_three_times_leaves_totals_unchanged(self):
        totals = []
        for _ in range(3):
            payslip = compute_payslip(self.payslip)
            totals.append((payslip.gross, payslip.net))
        self.assertEqual(len(set(totals)), 1)

    def test_line_codes_stay_unique_per_payslip(self):
        compute_payslip(self.payslip)
        compute_payslip(self.payslip)

        codes = list(PayslipLine.objects.filter(
            payslip=self.payslip).values_list("code", flat=True))
        self.assertEqual(len(codes), len(set(codes)))

    def test_recompute_does_not_duplicate_warnings(self):
        employee = self.make_employee("Meera", "Iyer", with_bank=False)
        payslip = self.make_payslip(employee, payrun=self.payslip.payrun)

        compute_payslip(payslip)
        compute_payslip(payslip)

        self.assertEqual(payslip.warnings.filter(
            code=PayslipWarning.AC_MISSING).count(), 1)

    def test_payrun_recompute_preserves_payrun_level_warnings(self):
        """
        A warning that records an employee skipped as a duplicate carries an
        employee but no payslip. Recompute must not delete it, or the operator
        loses the record of who was skipped.
        """
        payrun = self.payslip.payrun
        skipped = self.make_employee("Anita", "Oliver")
        PayslipWarning.objects.create(
            payrun=payrun, employee=skipped, code=PayslipWarning.DUPLICATE,
            message="Anita Oliver already has a payslip and was skipped.")

        compute_payrun(payrun)

        self.assertTrue(payrun.warnings.filter(
            employee=skipped, code=PayslipWarning.DUPLICATE).exists())


# ==========================================================================
# The formula sandbox
# ==========================================================================

class FormulaSandboxTests(PayrollTestCase):

    def test_dunder_import_is_blocked(self):
        with self.assertRaises(RuleEvaluationError) as caught:
            safe_eval("__import__('os').system('echo pwned')", {})
        self.assertIn("Forbidden token", str(caught.exception))

    def test_bare_import_keyword_is_blocked(self):
        with self.assertRaises(RuleEvaluationError):
            safe_eval("import os", {})

    def test_introspection_helpers_are_blocked(self):
        for expression in ("getattr(employee, 'company')",
                           "globals()",
                           "locals()",
                           "eval('1+1')",
                           "open('/etc/passwd')",
                           "().__class__.__bases__"):
            with self.subTest(expression=expression):
                with self.assertRaises(RuleEvaluationError):
                    safe_eval(expression, {})

    def test_an_empty_expression_is_rejected(self):
        with self.assertRaises(RuleEvaluationError):
            safe_eval("   ", {})

    def test_arithmetic_over_the_allowed_context_still_works(self):
        result = safe_eval("max(wage * Decimal('0.5'), Decimal('1000'))",
                           {"wage": Decimal("100000"), "Decimal": Decimal})
        self.assertEqual(result, Decimal("50000.0"))

    def test_a_blocked_formula_surfaces_as_a_rule_error_not_a_crash(self):
        SalaryRule.objects.create(
            structure=self.structure, name="Exploit", code="EXPLOIT",
            category=SalaryRule.DEDUCTION, sequence=60,
            computation=SalaryRule.FORMULA,
            formula="__import__('os').getcwd()")

        employee = self.make_employee()
        payslip = compute_payslip(self.make_payslip(employee))

        self.assertNotIn(
            "EXPLOIT", set(payslip.lines.values_list("code", flat=True)))
        self.assertTrue(payslip.warnings.filter(
            code=PayslipWarning.RULE_ERROR).exists())


# ==========================================================================
# Graded rule #5 — warnings before validation
# ==========================================================================

class PreValidationWarningTests(PayrollTestCase):

    def test_missing_bank_account_raises_ac_missing_before_validation(self):
        employee = self.make_employee("Meera", "Iyer", with_bank=False)
        payrun = self.make_payrun()
        payslip = compute_payslip(self.make_payslip(employee, payrun=payrun))

        warning = payslip.warnings.get(code=PayslipWarning.AC_MISSING)
        self.assertEqual(warning.severity, PayslipWarning.WARNING)
        self.assertIn("no bank account", warning.message)
        # The run is still only COMPUTED — the warning arrived first.
        self.assertEqual(payrun.state, Payrun.DRAFT)

    def test_an_employee_with_a_bank_account_raises_no_warning(self):
        employee = self.make_employee()
        payslip = compute_payslip(self.make_payslip(employee))
        self.assertFalse(
            payslip.warnings.filter(code=PayslipWarning.AC_MISSING).exists())

    def test_a_second_payslip_for_the_same_period_raises_duplicate(self):
        employee = self.make_employee()
        first_run = self.make_payrun("February 2026 — first")
        self.make_payslip(employee, payrun=first_run)

        second_run = self.make_payrun("February 2026 — rerun")
        created = create_payrun_payslips(second_run, [employee])

        self.assertEqual(created, [])
        warning = second_run.warnings.get(code=PayslipWarning.DUPLICATE)
        self.assertEqual(warning.employee, employee)
        self.assertIn("already has a payslip", warning.message)

    def test_no_contract_for_the_period_is_a_blocking_error(self):
        employee = Employee.objects.create(
            first_name="Zara", last_name="Sheikh",
            work_email="zara.sheikh@example.com",
            company=self.company, date_of_joining=date(2025, 1, 1),
            working_schedule=self.schedule)
        payrun = self.make_payrun()
        payslip = compute_payslip(self.make_payslip(employee, payrun=payrun))

        warning = payslip.warnings.get(code=PayslipWarning.NO_CONTRACT)
        self.assertEqual(warning.severity, PayslipWarning.ERROR)
        self.assertEqual(payslip.lines.count(), 0)

    def test_a_blocking_error_prevents_validation(self):
        employee = Employee.objects.create(
            first_name="Zara", last_name="Sheikh",
            work_email="zara.sheikh@example.com",
            company=self.company, date_of_joining=date(2025, 1, 1),
            working_schedule=self.schedule)
        payrun = self.make_payrun()
        self.make_payslip(employee, payrun=payrun)
        compute_payrun(payrun)

        self.assertEqual(payrun.error_count, 1)
        self.assertFalse(payrun.can_validate)
        with self.assertRaises(ValueError):
            validate_payrun(payrun)

    def test_a_warning_alone_does_not_block_validation(self):
        employee = self.make_employee("Meera", "Iyer", with_bank=False)
        payrun = self.make_payrun()
        self.make_payslip(employee, payrun=payrun)
        compute_payrun(payrun)

        self.assertEqual(payrun.warning_count, 1)
        self.assertEqual(payrun.error_count, 0)
        self.assertTrue(payrun.can_validate)


class PayrunStateMachineTests(PayrollTestCase):

    def setUp(self):
        self.employee = self.make_employee()
        self.payrun = self.make_payrun()
        self.make_payslip(self.employee, payrun=self.payrun)

    def test_the_happy_path_walks_draft_to_paid(self):
        self.assertEqual(self.payrun.state, Payrun.DRAFT)

        compute_payrun(self.payrun)
        self.assertEqual(self.payrun.state, Payrun.COMPUTED)

        validate_payrun(self.payrun)
        self.assertEqual(self.payrun.state, Payrun.VALIDATED)

        mark_payrun_paid(self.payrun)
        self.assertEqual(self.payrun.state, Payrun.PAID)

    def test_a_draft_payrun_cannot_be_validated(self):
        with self.assertRaises(ValueError):
            validate_payrun(self.payrun)

    def test_a_computed_payrun_cannot_be_marked_paid(self):
        compute_payrun(self.payrun)
        with self.assertRaises(ValueError):
            mark_payrun_paid(self.payrun)

    def test_a_paid_payrun_is_read_only(self):
        compute_payrun(self.payrun)
        validate_payrun(self.payrun)
        mark_payrun_paid(self.payrun)

        self.assertTrue(self.payrun.is_locked)
        with self.assertRaises(ValueError):
            compute_payrun(self.payrun)

    def test_validating_cascades_state_to_the_payslips(self):
        compute_payrun(self.payrun)
        validate_payrun(self.payrun)
        self.assertEqual(
            set(self.payrun.payslips.values_list("state", flat=True)),
            {Payrun.VALIDATED})

    def test_payrun_totals_aggregate_the_payslips(self):
        compute_payrun(self.payrun)
        self.assertEqual(self.payrun.total_gross, Decimal("70000.00"))
        self.assertEqual(self.payrun.total_net, Decimal("64000.00"))


class WizardStepTests(PayrollTestCase):
    """Step 1 collects scope and creates nothing; step 2 creates the shells."""

    def test_creating_a_payrun_creates_no_payslips(self):
        payrun = self.make_payrun()
        self.assertEqual(payrun.payslip_count, 0)

    def test_step_two_creates_one_payslip_per_employee(self):
        employees = [self.make_employee("Kabir", "Shah"),
                     self.make_employee("Nisha", "Rao")]
        payrun = self.make_payrun()
        created = create_payrun_payslips(payrun, employees)

        self.assertEqual(len(created), 2)
        self.assertEqual(payrun.payslip_count, 2)

    def test_step_two_resolves_the_contract_for_that_period(self):
        employee = self.make_employee()
        # Close the running contract and open a better-paid successor.
        Contract.objects.filter(employee=employee).update(
            end_date=date(2025, 12, 31), state=Contract.EXPIRED)
        Contract.objects.create(
            employee=employee, start_date=date(2026, 1, 1),
            wage=Decimal("150000.00"), working_schedule=self.schedule,
            salary_structure=self.structure, state=Contract.RUNNING)

        december = Payrun.objects.create(
            name="December 2025", company=self.company,
            salary_structure=self.structure,
            period_start=date(2025, 12, 1), period_end=date(2025, 12, 31))
        [payslip] = create_payrun_payslips(december, [employee])

        self.assertEqual(payslip.contract.wage, Decimal("100000.00"))


class EmployerCostTests(PayrollTestCase):
    """
    `is_employer_cost` must keep a rule out of the employee's gross and net.

    The flag was stored on the model, serialized by the API and editable as a
    checkbox in the Salary Rule form, and the engine never read it — so an
    employer-side PF rule categorised DEDUCTION reduced the employee's take-home
    pay. These tests pin the corrected behaviour.
    """

    def setUp(self):
        self.employee = self.make_employee()
        # Employer PF: 12% of BASIC, charged to the company, not the employee.
        SalaryRule.objects.create(
            structure=self.structure, name="Provident Fund (Employer)",
            code="PF_ER", category=SalaryRule.DEDUCTION, sequence=60,
            computation=SalaryRule.PERCENTAGE, percentage=Decimal("12.000"),
            percentage_base="BASIC", is_employer_cost=True)
        self.payslip = compute_payslip(self.make_payslip(self.employee))

    def test_the_employer_line_is_computed_and_stored(self):
        line = self.payslip.lines.get(code="PF_ER")
        self.assertEqual(line.amount, Decimal("6000.00"))
        self.assertTrue(line.is_employer_cost)

    def test_employer_cost_does_not_reduce_net(self):
        """The whole point: net is what it was before the rule existed."""
        self.assertEqual(self.payslip.net, Decimal("64000.00"))

    def test_employer_cost_is_excluded_from_deductions(self):
        # Employee PF alone, not employee PF + employer PF.
        self.assertEqual(self.payslip.deductions, Decimal("6000.00"))

    def test_employer_cost_does_not_reach_gross(self):
        self.assertEqual(self.payslip.gross, Decimal("70000.00"))

    def test_employer_cost_and_ctc_are_exposed(self):
        self.assertEqual(self.payslip.employer_cost, Decimal("6000.00"))
        self.assertEqual(self.payslip.ctc, Decimal("76000.00"))
        self.assertEqual(self.payslip.ctc,
                         self.payslip.gross + self.payslip.employer_cost)

    def test_an_employer_rule_is_still_visible_to_later_rules(self):
        """Kept in `rules` by code even though it is out of `categories`."""
        SalaryRule.objects.create(
            structure=self.structure, name="Echo Employer PF", code="ECHO",
            category=SalaryRule.ALLOWANCE, sequence=70,
            computation=SalaryRule.FORMULA, formula="rules['PF_ER']")
        payslip = compute_payslip(self.make_payslip(
            self.make_employee(first="Echo", last="Test")))
        self.assertEqual(payslip.lines.get(code="ECHO").amount,
                         Decimal("6000.00"))


class PayslipVisibilityTests(PayrollTestCase):
    """`appears_on_payslip` lets a rule compute without being printed."""

    def setUp(self):
        self.employee = self.make_employee()
        SalaryRule.objects.create(
            structure=self.structure, name="Internal Working Figure",
            code="INTERNAL", category=SalaryRule.ALLOWANCE, sequence=25,
            computation=SalaryRule.FIXED, amount=Decimal("1000.00"),
            appears_on_payslip=False)
        self.payslip = compute_payslip(self.make_payslip(self.employee))

    def test_a_hidden_rule_still_computes_and_still_counts(self):
        line = self.payslip.lines.get(code="INTERNAL")
        self.assertEqual(line.amount, Decimal("1000.00"))
        self.assertFalse(line.appears_on_payslip)
        # Hiding a line must not hide its money: it is a real allowance and
        # still aggregates into the ALLOWANCE category. (This fixture's GROSS
        # is an explicit BASIC + HRA formula rather than a category sum, so
        # gross itself does not move — that is the rule's definition, not the
        # visibility flag.)
        self.assertEqual(self.payslip.allowances, Decimal("21000.00"))
        self.assertEqual(self.payslip.gross, Decimal("70000.00"))

    def test_a_hidden_rule_is_left_out_of_the_printed_lines(self):
        printed = {l.code for l in self.payslip.visible_lines}
        self.assertNotIn("INTERNAL", printed)
        self.assertIn("BASIC", printed)
