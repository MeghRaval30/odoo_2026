"""
Graded rule #1 (period-based contract resolution) and #2 (derived weekly hours).

These cover what verify_rules.py proves against the seeded dev database, but
against a throwaway database inside a rolled-back transaction, so they can be
run selectively and in any order.
"""

from datetime import date, time
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Company, Department
from employees.models import Contract, Employee, ScheduleLine, WorkingSchedule


class ScheduleFactoryMixin:
    """A 5-day 09:00-18:00 schedule with a 60-minute break — 8h/day, 40h/week."""

    @staticmethod
    def build_schedule(company, name="Standard 40h", break_minutes=60):
        schedule = WorkingSchedule.objects.create(name=name, company=company)
        for day in range(5):
            ScheduleLine.objects.create(
                schedule=schedule, day_of_week=day,
                start_time=time(9, 0), end_time=time(18, 0),
                break_minutes=break_minutes,
            )
        return schedule


# ==========================================================================
# Graded rule #1 — contract resolution by period, not by recency
# ==========================================================================

class ContractResolutionTests(ScheduleFactoryMixin, TestCase):
    """
    The trap that cost session 01 a zero payrun: filtering to RUNNING only.
    An EXPIRED contract still governs the period it covered.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.schedule = cls.build_schedule(cls.company)
        cls.employee = Employee.objects.create(
            first_name="Asha", last_name="Rao",
            work_email="asha.rao@example.com",
            company=cls.company, date_of_joining=date(2024, 1, 1),
            working_schedule=cls.schedule,
        )
        # The employee's contract history: one closed, one open.
        cls.old_contract = Contract.objects.create(
            employee=cls.employee, start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31), wage=Decimal("50000.00"),
            working_schedule=cls.schedule, state=Contract.EXPIRED,
        )
        cls.new_contract = Contract.objects.create(
            employee=cls.employee, start_date=date(2026, 1, 1),
            end_date=None, wage=Decimal("75000.00"),
            working_schedule=cls.schedule, state=Contract.RUNNING,
        )

    def test_past_period_resolves_the_expired_contract(self):
        resolved = self.employee.contract_for_period(
            date(2025, 12, 1), date(2025, 12, 31))
        self.assertEqual(resolved, self.old_contract)
        self.assertEqual(resolved.state, Contract.EXPIRED)
        self.assertEqual(resolved.wage, Decimal("50000.00"))

    def test_current_period_resolves_the_running_contract(self):
        resolved = self.employee.contract_for_period(
            date(2026, 2, 1), date(2026, 2, 28))
        self.assertEqual(resolved, self.new_contract)
        self.assertEqual(resolved.state, Contract.RUNNING)
        self.assertEqual(resolved.wage, Decimal("75000.00"))

    def test_both_periods_resolve_differently_on_the_same_employee(self):
        """The whole point of the rule, asserted as one statement."""
        december = self.employee.contract_for_period(
            date(2025, 12, 1), date(2025, 12, 31))
        february = self.employee.contract_for_period(
            date(2026, 2, 1), date(2026, 2, 28))
        self.assertNotEqual(december, february)
        self.assertLess(december.wage, february.wage)

    def test_period_before_any_contract_resolves_nothing(self):
        self.assertIsNone(self.employee.contract_for_period(
            date(2023, 1, 1), date(2023, 1, 31)))

    def test_draft_and_cancelled_contracts_never_pay(self):
        other = Employee.objects.create(
            first_name="Dev", last_name="Sharma",
            work_email="dev.sharma@example.com",
            company=self.company, date_of_joining=date(2026, 1, 1),
            working_schedule=self.schedule,
        )
        Contract.objects.create(
            employee=other, start_date=date(2026, 1, 1),
            wage=Decimal("40000.00"), working_schedule=self.schedule,
            state=Contract.DRAFT,
        )
        Contract.objects.create(
            employee=other, start_date=date(2026, 1, 1),
            wage=Decimal("40000.00"), working_schedule=self.schedule,
            state=Contract.CANCELLED,
        )
        self.assertIsNone(other.contract_for_period(
            date(2026, 2, 1), date(2026, 2, 28)))

    def test_open_ended_contract_covers_a_period_after_its_start(self):
        self.assertTrue(self.new_contract.covers(
            date(2030, 6, 1), date(2030, 6, 30)))


class ContractOverlapTests(ScheduleFactoryMixin, TestCase):
    """Two RUNNING contracts may not overlap (PRD-4.1.1)."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.schedule = cls.build_schedule(cls.company)
        cls.employee = Employee.objects.create(
            first_name="Ravi", last_name="Kumar",
            work_email="ravi.kumar@example.com",
            company=cls.company, date_of_joining=date(2025, 1, 1),
            working_schedule=cls.schedule,
        )
        cls.running = Contract.objects.create(
            employee=cls.employee, start_date=date(2025, 1, 1),
            end_date=date(2026, 12, 31), wage=Decimal("60000.00"),
            working_schedule=cls.schedule, state=Contract.RUNNING,
        )

    def _candidate(self, start, end, state=Contract.RUNNING):
        return Contract(
            employee=self.employee, start_date=start, end_date=end,
            wage=Decimal("70000.00"), working_schedule=self.schedule,
            state=state,
        )

    def test_overlapping_running_contract_is_rejected(self):
        clash = self._candidate(date(2026, 6, 1), date(2027, 6, 1))
        with self.assertRaises(ValidationError) as caught:
            clash.clean()
        self.assertIn("Overlaps running contract", str(caught.exception))
        self.assertIn(self.running.reference, str(caught.exception))

    def test_open_ended_overlapping_contract_is_rejected(self):
        clash = self._candidate(date(2026, 6, 1), None)
        with self.assertRaises(ValidationError):
            clash.clean()

    def test_contract_starting_after_the_first_ends_is_allowed(self):
        successor = self._candidate(date(2027, 1, 1), None)
        successor.clean()  # must not raise
        successor.save()
        self.assertEqual(
            self.employee.contracts.filter(state=Contract.RUNNING).count(), 2)

    def test_a_draft_contract_may_overlap(self):
        """Only RUNNING contracts are exclusive — history and drafts are not."""
        draft = self._candidate(date(2026, 6, 1), None, state=Contract.DRAFT)
        draft.clean()  # must not raise

    def test_editing_the_contract_itself_is_not_a_self_clash(self):
        self.running.wage = Decimal("65000.00")
        self.running.clean()  # excluding its own pk — must not raise


# ==========================================================================
# Graded rule #2 — weekly hours derived from the day lines
# ==========================================================================

class WorkingScheduleHoursTests(ScheduleFactoryMixin, TestCase):
    """
    hours_per_week is a property over the lines, never a stored column.
    Removing one 60-minute break must move 40h to 41h with no other edit.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")

    def setUp(self):
        self.schedule = self.build_schedule(self.company)

    def test_baseline_is_forty_hours(self):
        self.assertEqual(self.schedule.hours_per_week, Decimal("40.00"))
        self.assertEqual(self.schedule.days_per_week, 5)

    def test_removing_one_break_recomputes_forty_to_forty_one(self):
        line = self.schedule.lines.first()
        line.break_minutes = 0
        line.save()

        refreshed = WorkingSchedule.objects.get(pk=self.schedule.pk)
        self.assertEqual(refreshed.hours_per_week, Decimal("41.00"))

    def test_line_hours_are_net_of_the_break(self):
        line = self.schedule.lines.first()
        self.assertEqual(line.hours, Decimal("8.00"))  # 9h span - 60m
        line.break_minutes = 30
        self.assertEqual(line.hours, Decimal("8.50"))

    def test_adding_a_sixth_day_adds_its_hours(self):
        ScheduleLine.objects.create(
            schedule=self.schedule, day_of_week=5,
            start_time=time(9, 0), end_time=time(13, 0), break_minutes=0)
        refreshed = WorkingSchedule.objects.get(pk=self.schedule.pk)
        self.assertEqual(refreshed.hours_per_week, Decimal("44.00"))
        self.assertEqual(refreshed.days_per_week, 6)

    def test_split_shifts_on_one_day_count_once_as_a_day(self):
        ScheduleLine.objects.create(
            schedule=self.schedule, day_of_week=0,
            start_time=time(19, 0), end_time=time(21, 0), break_minutes=0)
        refreshed = WorkingSchedule.objects.get(pk=self.schedule.pk)
        self.assertEqual(refreshed.hours_per_week, Decimal("42.00"))
        self.assertEqual(refreshed.days_per_week, 5)

    def test_expected_working_days_excludes_weekends_and_holidays(self):
        from core.models import Holiday

        # February 2026: 20 weekdays.
        self.assertEqual(
            self.schedule.expected_working_days(
                date(2026, 2, 1), date(2026, 2, 28)), 20)

        Holiday.objects.create(
            name="Test Holiday", date=date(2026, 2, 4), company=self.company)
        holidays = {date(2026, 2, 4)}
        self.assertEqual(
            self.schedule.expected_working_days(
                date(2026, 2, 1), date(2026, 2, 28), holidays), 19)


class EmployeeRecordTests(ScheduleFactoryMixin, TestCase):
    """Employee code sequencing, derived name fields and the bank-details gate."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.department = Department.objects.create(
            name="Engineering", company=cls.company)

    def _employee(self, first, last, **extra):
        return Employee.objects.create(
            first_name=first, last_name=last,
            work_email=f"{first.lower()}.{last.lower()}@example.com",
            company=self.company, date_of_joining=date(2026, 1, 1), **extra)

    def test_employee_code_is_generated_and_sequential(self):
        first = self._employee("Nina", "Das")
        second = self._employee("Omar", "Khan")
        self.assertEqual(first.employee_code, "EMP/2026/0001")
        self.assertEqual(second.employee_code, "EMP/2026/0002")

    def test_full_name_and_initials_are_derived(self):
        employee = self._employee("Nina", "Das")
        self.assertEqual(employee.full_name, "Nina Das")
        self.assertEqual(employee.initials, "ND")

    def test_has_bank_details_requires_both_account_and_ifsc(self):
        employee = self._employee("Nina", "Das")
        self.assertFalse(employee.has_bank_details)

        employee.bank_account_number = "1234567890"
        self.assertFalse(employee.has_bank_details)  # IFSC still missing

        employee.bank_ifsc = "HDFC0001234"
        self.assertTrue(employee.has_bank_details)

    def test_circular_management_chain_is_rejected(self):
        boss = self._employee("Nina", "Das")
        report = self._employee("Omar", "Khan", manager=boss)
        boss.manager = report
        with self.assertRaises(ValidationError):
            boss.clean()
