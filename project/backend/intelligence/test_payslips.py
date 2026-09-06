"""
Tests for the historical payslip import.

Weighted towards the two things that can corrupt a customer's payroll silently
rather than towards coverage. A payslip import that refuses a file is annoying;
a payslip import that writes plausible wrong numbers is the thing you find out
about a year later, from an employee, in writing.

So the two heaviest tests here are:

  * `TotalsAreNotComponents` -- a column headed "Total Deductions" must never
    become a deduction line. It is the sum of the other deduction columns, and
    storing it alongside them doubles every deduction and halves every net.
  * `ReconciliationTests` -- the sheet states a gross and a net, so the sheet
    can be checked against itself, and a dropped component has to be caught
    before it is written rather than after.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from core.models import Company
from employees.models import Contract, Employee, WorkingSchedule
from payroll.models import Payrun, Payslip, PayslipLine, SalaryStructure

from . import payslip_schema as ps
from . import payslips


class FakeTable:
    """The two attributes `build_records` and `evaluate` actually read."""

    def __init__(self, headers, rows):
        self.headers = headers
        self.rows = rows
        self.row_count = len(rows)


def plan_for(headers):
    """A plan that maps each header by name, the way `build_plan` would."""
    columns = []
    for index, header in enumerate(headers):
        candidates = ps.match_header(header)
        top = candidates[0] if candidates else None
        columns.append({
            "index": index,
            "header": header,
            "field": top["field"] if top and top["confidence"] >= 0.5 else None,
            "confidence": top["confidence"] if top else 0.0,
            "reason": top["reason"] if top else "",
        })
    payslips._enforce_uniqueness(columns)
    return {"columns": columns, "gaps": ps.missing_required(columns)}


# ==========================================================================
# The vocabulary
# ==========================================================================

class TotalsAreNotComponents(TestCase):
    """
    A stated total must never be stored as a component.

    This is a regression test with a real defect behind it. "total deduction"
    and "total deductions" were briefly synonyms of `other_deductions`, which
    meant a sheet carrying a Total Deductions column -- which most payroll
    exports do -- had that total written as an extra DEDUCTION line beside the
    components it was the sum of. Every net on the import would have come out
    roughly half of what the employee was actually paid, on a payslip that
    looked entirely ordinary.
    """

    def test_total_deductions_is_its_own_field(self):
        for header in ("Total Deductions", "Total Ded", "Deduction Total",
                       "Gross Deductions"):
            with self.subTest(header=header):
                top = ps.match_header(header)[0]
                self.assertEqual(top["field"], "total_deductions",
                                 "%r should be read as the stated total" % header)

    def test_the_stated_total_is_never_a_payslip_line(self):
        self.assertNotIn("total_deductions", ps.COMPONENT_KEYS)
        self.assertNotIn("gross", ps.COMPONENT_KEYS)
        self.assertNotIn("net", ps.COMPONENT_KEYS)
        for key in ("total_deductions", "gross", "net"):
            self.assertIsNone(ps.FIELDS_BY_KEY[key]["category"],
                              "%s is a total, so it has no rule category" % key)

    def test_other_deductions_still_reads_its_own_column(self):
        # The fix must not cost the component it was confused with.
        self.assertEqual(ps.match_header("Other Deductions")[0]["field"],
                         "other_deductions")

    def test_every_component_has_a_code_and_a_category(self):
        codes = set()
        for field in ps.COMPONENT_FIELDS:
            self.assertTrue(field["code"], "%s has no rule code" % field["key"])
            self.assertIn(field["category"],
                          ("BASIC", "ALLOWANCE", "DEDUCTION"))
            self.assertNotIn(field["code"], codes,
                             "two components share the code %s" % field["code"])
            codes.add(field["code"])


class HeaderMatchingTests(TestCase):
    def test_the_abbreviations_real_payroll_sheets_use(self):
        expected = {
            "Emp Code": "employee_code", "Employee Name": "full_name",
            "Month": "period_month", "Basic": "basic", "HRA": "hra",
            "Conveyance": "conveyance", "Spl Allow": "special_allowance",
            "PF": "pf_employee", "P.Tax": "professional_tax",
            "TDS": "income_tax", "Net Pay": "net", "Gross Salary": "gross",
            "LOP": "lop_days", "Paid Days": "worked_days",
            "ESIC": "esic_employee", "OT Amount": "overtime_amount",
        }
        for header, field in expected.items():
            with self.subTest(header=header):
                top = ps.match_header(header)[0]
                self.assertEqual(top["field"], field)

    def test_a_column_of_day_counts_is_not_read_as_money(self):
        # Days and rupees are both numbers; only their size separates them.
        profile = {"best_kind": "integer", "numeric_median": 30.0}
        top = ps.match_header("Days", profile)
        self.assertNotIn(top[0]["field"], ps.EARNING_KEYS)

    def test_one_field_cannot_be_claimed_by_two_columns(self):
        plan = plan_for(["Basic", "Basic Salary", "HRA"])
        basics = [c for c in plan["columns"] if c["field"] == "basic"]
        self.assertEqual(len(basics), 1,
                         "summing the same component twice doubles it")


class GapTests(TestCase):
    def test_a_sheet_with_no_identity_column_cannot_import(self):
        gaps = ps.missing_required(plan_for(["Month", "Basic"])["columns"])
        self.assertIn("identity", [g["key"] for g in gaps])

    def test_a_sheet_with_no_period_cannot_import(self):
        gaps = ps.missing_required(plan_for(["Emp Code", "Basic"])["columns"])
        self.assertIn("period", [g["key"] for g in gaps])

    def test_a_start_and_an_end_together_fix_the_period(self):
        gaps = ps.missing_required(
            plan_for(["Emp Code", "From Date", "To Date", "Basic"])["columns"])
        self.assertNotIn("period", [g["key"] for g in gaps])

    def test_a_complete_sheet_has_no_gaps(self):
        self.assertEqual(
            ps.missing_required(plan_for(["Emp Code", "Month", "Basic"])["columns"]),
            [])


class MonthParsingTests(TestCase):
    def test_the_forms_payroll_sheets_write_a_month_in(self):
        for raw in ("Dec-2025", "December 2025", "Dec 2025", "12/2025",
                    "2025-12", "Dec 25"):
            with self.subTest(raw=raw):
                self.assertEqual(payslips.parse_month(raw), (2025, 12), raw)

    def test_a_month_expands_to_the_whole_month(self):
        self.assertEqual(payslips.month_bounds(2025, 2),
                         (date(2025, 2, 1), date(2025, 2, 28)))
        self.assertEqual(payslips.month_bounds(2024, 2)[1], date(2024, 2, 29))

    def test_nonsense_is_refused_rather_than_guessed(self):
        for raw in ("", "n/a", "Quarter 3", "13/2025"):
            self.assertIsNone(payslips.parse_month(raw), raw)


class MoneyTests(TestCase):
    def test_the_ways_a_sheet_writes_rupees(self):
        self.assertEqual(payslips.money("1,08,000"), Decimal("108000.00"))
        self.assertEqual(payslips.money("Rs. 45000"), Decimal("45000.00"))
        self.assertEqual(payslips.money(" 85000.50 "), Decimal("85000.50"))
        self.assertEqual(payslips.money("(500)"), Decimal("-500.00"))

    def test_a_blank_is_absent_rather_than_zero(self):
        # The distinction matters: a blank allowance column is a gap in the
        # data, and a zero is a decision the old payroll made.
        for blank in ("", "   ", None, "NULL", "-"):
            self.assertIsNone(payslips.money(blank), repr(blank))


# ==========================================================================
# The arithmetic
# ==========================================================================

class ReconciliationTests(TestCase):
    def _parts(self, **kw):
        return {k: Decimal(str(v)) for k, v in kw.items()}

    def test_components_that_add_up_reconcile(self):
        record = {"gross": "50000", "net": "44000"}
        parts = self._parts(basic=20000, hra=8000, special_allowance=22000,
                            pf_employee=2400, professional_tax=200,
                            income_tax=3400)
        check = payslips.reconcile(record, parts)
        self.assertIs(check["ok"], True)
        self.assertEqual(check["computed_net"], Decimal("44000.00"))

    def test_a_dropped_allowance_is_caught(self):
        # The defect this whole check exists for: every cell present and
        # plausible, one component silently missing, totals left untouched.
        record = {"gross": "50000", "net": "44000"}
        parts = self._parts(basic=20000, hra=8000,
                            pf_employee=2400, professional_tax=200,
                            income_tax=3400)
        check = payslips.reconcile(record, parts)
        self.assertIs(check["ok"], False)
        self.assertIn("22000", check["message"])
        self.assertEqual(check["gross_delta"], Decimal("-22000.00"))

    def test_the_stated_total_deductions_is_checked_too(self):
        record = {"total_deductions": "9999"}
        parts = self._parts(basic=20000, pf_employee=2400,
                            professional_tax=200)
        check = payslips.reconcile(record, parts)
        self.assertIs(check["ok"], False)
        self.assertIn("total deductions", check["message"])

    def test_rounding_of_a_rupee_is_not_a_disagreement(self):
        record = {"net": "17400.60"}
        parts = self._parts(basic=20000, pf_employee=2400, professional_tax=200)
        self.assertIs(payslips.reconcile(record, parts)["ok"], True)

    def test_a_sheet_with_no_stated_total_is_unchecked_not_wrong(self):
        # Three outcomes, not two: agreed, disagreed, and nothing to compare.
        check = payslips.reconcile({}, self._parts(basic=20000))
        self.assertIsNone(check["ok"])


# ==========================================================================
# Resolving and writing
# ==========================================================================

class PayslipImportTestCase(TestCase):
    """A company, a structure and three employees to import pay against."""

    def setUp(self):
        self.company = Company.objects.create(name="Oxpayroll")
        self.structure = SalaryStructure.objects.create(
            name="India Monthly", code="IND", company=self.company)
        self.schedule = WorkingSchedule.objects.create(
            company=self.company, name="40 Hours / Week")
        self.alice = Employee.objects.create(
            company=self.company, first_name="Alice", last_name="Roy",
            work_email="alice@oxp.com", employee_code="EMP/2025/0001",
            date_of_joining=date(2024, 1, 1))
        self.bob = Employee.objects.create(
            company=self.company, first_name="Bob", last_name="Nair",
            work_email="bob@oxp.com", employee_code="EMP/2025/0002",
            date_of_joining=date(2024, 1, 1))
        Contract.objects.create(
            employee=self.alice, salary_structure=self.structure,
            working_schedule=self.schedule, wage=Decimal("50000"),
            start_date=date(2024, 1, 1), state=Contract.RUNNING)

    def evaluate(self, headers, rows):
        table = FakeTable(headers, rows)
        return payslips.evaluate(table, plan_for(headers), self.company)


class ResolutionTests(PayslipImportTestCase):
    HEADERS = ["Emp Code", "Employee Name", "Email", "Month", "Basic"]

    def test_the_employee_code_is_trusted_first(self):
        rows = self.evaluate(
            self.HEADERS,
            [["EMP/2025/0001", "Someone Else", "", "Sep-2025", "20000"]])
        self.assertEqual(rows[0]["employee_id"], self.alice.id)
        self.assertEqual(rows[0]["matched_by"], "code")

    def test_email_resolves_when_there_is_no_code(self):
        rows = self.evaluate(
            self.HEADERS, [["", "", "bob@oxp.com", "Sep-2025", "20000"]])
        self.assertEqual(rows[0]["employee_id"], self.bob.id)
        self.assertEqual(rows[0]["matched_by"], "email")

    def test_a_name_match_imports_but_says_so(self):
        rows = self.evaluate(
            self.HEADERS, [["", "Alice Roy", "", "Sep-2025", "20000"]])
        self.assertEqual(rows[0]["matched_by"], "name")
        self.assertTrue(rows[0]["importable"])
        self.assertTrue(any("name alone" in w for w in rows[0]["warnings"]))

    def test_an_unknown_person_is_refused_not_created(self):
        # A payslip import matches; it must never invent the employee.
        before = Employee.objects.count()
        rows = self.evaluate(
            self.HEADERS, [["", "Nobody Here", "", "Sep-2025", "20000"]])
        self.assertFalse(rows[0]["importable"])
        self.assertEqual(Employee.objects.count(), before)

    def test_an_ambiguous_name_is_refused_rather_than_guessed(self):
        Employee.objects.create(
            company=self.company, first_name="Alice", last_name="Roy",
            work_email="alice2@oxp.com", employee_code="EMP/2025/0003",
            date_of_joining=date(2024, 1, 1))
        rows = self.evaluate(
            self.HEADERS, [["", "Alice Roy", "", "Sep-2025", "20000"]])
        self.assertFalse(rows[0]["importable"])
        self.assertTrue(any("more than one" in p for p in rows[0]["problems"]))


class DuplicateTests(PayslipImportTestCase):
    HEADERS = ["Emp Code", "Month", "Basic"]

    def test_the_same_person_twice_in_one_file(self):
        rows = self.evaluate(self.HEADERS, [
            ["EMP/2025/0001", "Sep-2025", "20000"],
            ["EMP/2025/0001", "Sep-2025", "20000"],
        ])
        self.assertTrue(rows[0]["importable"])
        self.assertFalse(rows[1]["importable"])

    def test_a_month_already_paid_in_this_system(self):
        payrun = Payrun.objects.create(
            company=self.company, salary_structure=self.structure,
            name="September 2025", period_start=date(2025, 9, 1),
            period_end=date(2025, 9, 30), state=Payrun.PAID)
        Payslip.objects.create(
            payrun=payrun, employee=self.alice, salary_structure=self.structure,
            period_start=date(2025, 9, 1), period_end=date(2025, 9, 30))
        rows = self.evaluate(self.HEADERS,
                             [["EMP/2025/0001", "Sep-2025", "20000"]])
        self.assertFalse(rows[0]["importable"])
        self.assertTrue(any("already has a payslip" in p
                            for p in rows[0]["problems"]))

    def test_the_same_person_in_two_different_months_is_not_a_duplicate(self):
        rows = self.evaluate(self.HEADERS, [
            ["EMP/2025/0001", "Sep-2025", "20000"],
            ["EMP/2025/0001", "Oct-2025", "20000"],
        ])
        self.assertTrue(all(r["importable"] for r in rows))


class CommitTests(PayslipImportTestCase):
    HEADERS = ["Emp Code", "Month", "Paid Days", "LOP", "Basic", "HRA",
               "PF", "P.Tax", "Gross Salary", "Net Pay"]

    def rows(self):
        return [
            ["EMP/2025/0001", "Sep-2025", "30", "0",
             "20000", "8000", "2400", "200", "28000", "25400"],
            ["EMP/2025/0002", "Sep-2025", "28", "2",
             "18000", "7200", "2160", "200", "25200", "22840"],
            ["EMP/2025/0001", "Oct-2025", "31", "0",
             "20000", "8000", "2400", "200", "28000", "25400"],
        ]

    def commit(self):
        evaluated = self.evaluate(self.HEADERS, self.rows())
        return evaluated, payslips.commit(evaluated, self.company,
                                          structure=self.structure)

    def test_one_payrun_per_period(self):
        _, created = self.commit()
        self.assertEqual(created["payruns"], 2)
        self.assertEqual(created["payslips"], 3)
        self.assertEqual(
            sorted(Payrun.objects.values_list("period_start", flat=True)),
            [date(2025, 9, 1), date(2025, 10, 1)])

    def test_imported_pay_is_filed_as_already_paid(self):
        # Historical pay is settled. A DRAFT run would put months of finished
        # money back into the payroll operator's queue.
        self.commit()
        self.assertTrue(all(p.state == Payrun.PAID
                            for p in Payrun.objects.all()))

    def test_totals_derive_exactly_as_a_computed_payslip_does(self):
        self.commit()
        slip = Payslip.objects.get(employee=self.alice,
                                   period_start=date(2025, 9, 1))
        self.assertEqual(slip.basic, Decimal("20000"))
        self.assertEqual(slip.allowances, Decimal("8000"))
        self.assertEqual(slip.deductions, Decimal("2600"))
        self.assertEqual(slip.gross, Decimal("28000"))
        self.assertEqual(slip.net, Decimal("25400"))

    def test_the_stated_totals_are_read_but_not_stored(self):
        self.commit()
        slip = Payslip.objects.get(employee=self.alice,
                                   period_start=date(2025, 9, 1))
        codes = set(slip.lines.values_list("code", flat=True))
        self.assertEqual(codes, {"BASIC", "HRA", "PF", "PT"})

    def test_attendance_on_the_sheet_reaches_the_payslip(self):
        self.commit()
        slip = Payslip.objects.get(employee=self.bob,
                                   period_start=date(2025, 9, 1))
        self.assertEqual(slip.worked_days, Decimal("28.00"))
        self.assertEqual(slip.lop_days, Decimal("2.00"))

    def test_a_blocked_row_writes_nothing(self):
        evaluated = self.evaluate(
            self.HEADERS + ["Employee Name"],
            [["", "Sep-2025", "30", "0", "20000", "8000", "2400", "200",
              "28000", "25400", "Nobody Here"]])
        created = payslips.commit(evaluated, self.company,
                                  structure=self.structure)
        self.assertEqual(created["payslips"], 0)
        self.assertEqual(Payslip.objects.count(), 0)

    def test_every_line_carries_a_category_so_the_register_can_read_it(self):
        self.commit()
        self.assertFalse(
            PayslipLine.objects.filter(category="").exists(),
            "a line with no category cannot be totalled by the register")

    def test_a_second_commit_of_the_same_file_adds_nothing(self):
        self.commit()
        again = self.evaluate(self.HEADERS, self.rows())
        self.assertTrue(all(not r["importable"] for r in again),
                        "every row should now trip the duplicate guard")
        created = payslips.commit(again, self.company, structure=self.structure)
        self.assertEqual(created["payslips"], 0)
        self.assertEqual(Payslip.objects.count(), 3)


class SummaryTests(PayslipImportTestCase):
    def test_the_counts_the_screen_shows(self):
        rows = self.evaluate(
            ["Emp Code", "Employee Name", "Month", "Basic", "Net Pay"],
            [["EMP/2025/0001", "", "Sep-2025", "20000", "20000"],
             ["EMP/2025/0002", "", "Oct-2025", "18000", "18000"],
             ["", "Nobody Here", "Sep-2025", "10000", "10000"]])
        summary = payslips.summarise(rows)
        self.assertEqual(summary["rows"], 3)
        self.assertEqual(summary["importable"], 2)
        self.assertEqual(summary["blocked"], 1)
        self.assertEqual(summary["period_count"], 2)
        self.assertEqual(summary["matched_by_code"], 2)
