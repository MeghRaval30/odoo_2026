"""
The seed command (T-028, T-089).

Two things have to stay true of `manage.py seed`. The default run is what the
demo script quotes verbatim, so its shape is pinned here — if a change moves the
headcount, the contract count or the December/January/February nets, the demo is
wrong and this fails first. And `--employees N` has to grow the roster *around*
that fixed set rather than replacing it, which is what makes the large dataset
safe to seed on the demo machine.

The generated-roster case is run at a small N: the shapes it produces are what
matter, not the volume, and 250 employees inside a test transaction is thirty
seconds nobody gets back.
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from attendance.models import Attendance
from employees.models import Contract, Employee
from payroll.models import Payrun, Payslip, PayslipWarning, SalaryStructure
from payroll import engine
from timeoff.models import Allocation


class SeedDefaultTests(TestCase):
    """The 22-person roster the demo script is written against."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed", stdout=StringIO(), stderr=StringIO())

    def test_roster_shape_matches_the_demo_script(self):
        self.assertEqual(Employee.objects.count(), 22)
        self.assertEqual(Contract.objects.count(), 24)
        self.assertEqual(Attendance.objects.count(), 1746)
        self.assertEqual(Payrun.objects.count(), 3)
        self.assertEqual(Payslip.objects.count(), 60)

    def test_the_named_demo_people_are_present_and_unchanged(self):
        john = Employee.objects.get(work_email="john@oxp.com")
        self.assertEqual(john.employee_code, "EMP/2025/0003")
        self.assertEqual(john.full_name, "John Dsouza")

        periods = [(date(2025, 12, 1), date(2025, 12, 31), Decimal("103000")),
                   (date(2026, 1, 1), date(2026, 1, 31), Decimal("110000"))]
        for start, end, wage in periods:
            with self.subTest(period=start):
                self.assertEqual(john.contract_for_period(start, end).wage, wage)

        # The two warnings the demo reads out loud, by name.
        without_bank = sorted(e.full_name for e in Employee.objects.all()
                              if not e.has_bank_details)
        self.assertEqual(without_bank, ["Anita Oliver", "Meera Iyer"])

    def test_the_three_seeded_payruns_are_paid_and_hold_their_totals(self):
        expected = {"December 2025": Decimal("1473360.00"),
                    "January 2026": Decimal("1482320.00"),
                    "February 2026": Decimal("1558667.87")}
        for name, net in expected.items():
            with self.subTest(payrun=name):
                run = Payrun.objects.get(name=name)
                self.assertEqual(run.state, Payrun.PAID)
                self.assertEqual(run.payslip_count, 20)
                self.assertEqual(run.total_net, net)

        # December below January is the headline evidence for graded rule #1 —
        # two people resolve to their older, cheaper contract.
        self.assertLess(expected["December 2025"], expected["January 2026"])


class SeedGeneratedRosterTests(TestCase):
    """`--employees N` — the large dataset (T-089)."""

    N = 60

    @classmethod
    def setUpTestData(cls):
        call_command("seed", employees=cls.N, stdout=StringIO(), stderr=StringIO())

    def test_the_fixed_roster_survives_the_expansion(self):
        self.assertEqual(Employee.objects.count(), self.N)
        john = Employee.objects.get(work_email="john@oxp.com")
        self.assertEqual(john.employee_code, "EMP/2025/0003")
        self.assertEqual(john.contracts.count(), 2)

        priya = Employee.objects.get(work_email="priya@oxp.com")
        allocation = priya.allocations.get(time_off_type__code="PTO")
        self.assertEqual(allocation.allocated, Decimal("20.00"))
        self.assertEqual(allocation.remaining, Decimal("20.00"))

    def test_generated_rows_carry_their_own_references(self):
        """bulk_create never calls save(), so the sequences are minted by hand."""
        codes = list(Employee.objects.values_list("employee_code", flat=True))
        self.assertEqual(len(codes), len(set(codes)))
        self.assertTrue(all(c and c.startswith("EMP/") for c in codes))

        refs = list(Contract.objects.values_list("reference", flat=True))
        self.assertEqual(len(refs), len(set(refs)))
        self.assertTrue(all(r and r.startswith("CON/") for r in refs))

    def test_everybody_gets_a_contract_and_a_leave_allocation(self):
        self.assertEqual(
            Employee.objects.filter(contracts__isnull=True).count(), 0)
        self.assertEqual(Allocation.objects.count(), self.N)

    def test_the_seeded_history_still_validates(self):
        """
        A joiner or leaver with no contract for the period would raise a
        NO_CONTRACT error, and an errored payrun cannot be validated — the
        seeded history would sit at Computed instead of Paid.
        """
        for run in Payrun.objects.all():
            with self.subTest(payrun=run.name):
                self.assertEqual(run.state, Payrun.PAID)
                self.assertEqual(run.error_count, 0)

    def test_a_march_payrun_surfaces_two_distinct_warnings(self):
        """
        PRD success criterion 4. The fixed roster alone only ever raises
        AC_MISSING; a generated roster carries leavers, so a payrun for a
        period after they left raises NO_CONTRACT alongside it.
        """
        start, end = date(2026, 3, 1), date(2026, 3, 31)
        regular = SalaryStructure.objects.get(code="REGULAR")
        run = Payrun.objects.create(
            name="March 2026", company=regular.company,
            salary_structure=regular, period_start=start, period_end=end)

        engine.create_payrun_payslips(
            run, list(Employee.objects.filter(active=True)))
        engine.compute_payrun(run)

        codes = set(run.warnings.values_list("code", flat=True))
        self.assertIn(PayslipWarning.AC_MISSING, codes)
        self.assertGreaterEqual(len(codes), 2)

    def test_a_mid_period_joiner_is_prorated(self):
        """
        A contract that starts part-way through a month must not draw a full
        month's pay.

        The payrun is built around whichever month the joiner actually landed
        in rather than around a hard-coded March. Pinning the month made the
        test depend on where in a Feb–Mar window one random draw fell, which is
        a property of the generator, not of proration — and it duly failed once
        the suite ran as a whole.
        """
        joiner = (Contract.objects
                  .filter(start_date__gte=date(2026, 2, 1))
                  .exclude(start_date__day=1)
                  .order_by("start_date")
                  .first())
        self.assertIsNotNone(
            joiner, "the generated roster should contain a mid-month joiner")

        start = joiner.start_date.replace(day=1)
        end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        regular = SalaryStructure.objects.get(code="REGULAR")
        run = Payrun.objects.create(
            name=f"{start:%B %Y}", company=regular.company,
            salary_structure=regular, period_start=start, period_end=end)
        engine.create_payrun_payslips(run, [joiner.employee])
        engine.compute_payrun(run)

        payslip = run.payslips.get()
        self.assertGreater(payslip.gross, Decimal("0"))
        self.assertLess(payslip.gross, joiner.wage)
