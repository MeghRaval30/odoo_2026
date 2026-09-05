"""
Graded rule #3 — allocation-gated leave, with a derived balance.

Remaining = Allocated - Taken, computed over approved consuming requests.
Nothing about the balance is stored, so every assertion here reads it back
through the property rather than trusting a column.
"""

from datetime import date, time
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Company, Holiday
from employees.models import Employee, ScheduleLine, WorkingSchedule
from timeoff.models import Allocation, TimeOffRequest, TimeOffType


class TimeOffTestCase(TestCase):
    """Shared fixture: one employee on a Mon-Fri schedule, two leave types."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.schedule = WorkingSchedule.objects.create(
            name="Standard 40h", company=cls.company)
        for day in range(5):
            ScheduleLine.objects.create(
                schedule=cls.schedule, day_of_week=day,
                start_time=time(9, 0), end_time=time(18, 0), break_minutes=60)

        cls.employee = Employee.objects.create(
            first_name="Priya", last_name="Nair",
            work_email="priya.nair@example.com",
            company=cls.company, date_of_joining=date(2025, 1, 1),
            working_schedule=cls.schedule,
        )

        cls.gated = TimeOffType.objects.create(
            name="Paid Time Off", code="PTO",
            requires_allocation=True, is_paid=True)
        cls.ungated = TimeOffType.objects.create(
            name="Unpaid Leave", code="UNPAID",
            requires_allocation=False, is_paid=False)

    def make_request(self, date_from, date_to, time_off_type=None, **extra):
        return TimeOffRequest(
            employee=self.employee,
            time_off_type=time_off_type or self.gated,
            date_from=date_from, date_to=date_to, **extra)

    def approve_allocation(self, allocated="20.00", valid_from=date(2026, 1, 1),
                           valid_to=date(2026, 12, 31), state=Allocation.APPROVED):
        return Allocation.objects.create(
            employee=self.employee, time_off_type=self.gated,
            name="2026 PTO", allocated=Decimal(allocated),
            valid_from=valid_from, valid_to=valid_to, state=state)


# ==========================================================================
# The gate itself
# ==========================================================================

class AllocationGateTests(TimeOffTestCase):

    def test_request_without_any_allocation_is_refused(self):
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 4))
        with self.assertRaises(ValidationError) as caught:
            request.clean()
        self.assertIn("No approved Paid Time Off allocation",
                      str(caught.exception))

    def test_request_against_an_unapproved_allocation_is_refused(self):
        self.approve_allocation(state=Allocation.TO_APPROVE)
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 4))
        with self.assertRaises(ValidationError):
            request.clean()

    def test_the_same_request_succeeds_once_the_allocation_is_approved(self):
        allocation = self.approve_allocation(state=Allocation.TO_APPROVE)
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 4))
        with self.assertRaises(ValidationError):
            request.clean()

        allocation.state = Allocation.APPROVED
        allocation.save()

        request.clean()  # must not raise
        self.assertEqual(request.allocation_used, allocation)
        self.assertEqual(request.duration, Decimal("3"))

    def test_a_type_that_does_not_require_allocation_is_ungated(self):
        request = self.make_request(
            date(2026, 3, 2), date(2026, 3, 4), time_off_type=self.ungated)
        request.clean()  # must not raise
        self.assertIsNone(request.allocation_used)

    def test_allocation_not_covering_the_dates_does_not_satisfy_the_gate(self):
        self.approve_allocation(valid_from=date(2026, 1, 1),
                                valid_to=date(2026, 2, 28))
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 4))
        with self.assertRaises(ValidationError):
            request.clean()

    def test_request_larger_than_the_balance_is_refused(self):
        self.approve_allocation(allocated="2.00")
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 6))
        with self.assertRaises(ValidationError) as caught:
            request.clean()
        self.assertIn("Insufficient balance", str(caught.exception))


# ==========================================================================
# Remaining = Allocated - Taken
# ==========================================================================

class AllocationBalanceTests(TimeOffTestCase):

    def setUp(self):
        self.allocation = self.approve_allocation(allocated="20.00")

    def _approved_request(self, date_from, date_to):
        request = self.make_request(date_from, date_to)
        request.clean()
        request.save()
        return request.approve()

    def test_a_fresh_allocation_has_taken_zero_and_remaining_all(self):
        self.assertEqual(self.allocation.allocated, Decimal("20.00"))
        self.assertEqual(self.allocation.taken, Decimal("0.00"))
        self.assertEqual(self.allocation.remaining, Decimal("20.00"))

    def test_approving_a_request_decrements_remaining(self):
        self._approved_request(date(2026, 3, 2), date(2026, 3, 4))  # 3 days

        allocation = Allocation.objects.get(pk=self.allocation.pk)
        self.assertEqual(allocation.taken, Decimal("3.00"))
        self.assertEqual(allocation.remaining, Decimal("17.00"))

    def test_cancelling_an_approved_request_restores_the_balance(self):
        request = self._approved_request(date(2026, 3, 2), date(2026, 3, 4))
        self.assertEqual(
            Allocation.objects.get(pk=self.allocation.pk).remaining,
            Decimal("17.00"))

        request.state = TimeOffRequest.CANCELLED
        request.save(update_fields=["state", "updated_at"])

        allocation = Allocation.objects.get(pk=self.allocation.pk)
        self.assertEqual(allocation.taken, Decimal("0.00"))
        self.assertEqual(allocation.remaining, Decimal("20.00"))

    def test_refusing_a_request_does_not_consume_balance(self):
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 4))
        request.clean()
        request.save()
        request.refuse()

        self.assertEqual(
            Allocation.objects.get(pk=self.allocation.pk).remaining,
            Decimal("20.00"))

    def test_only_approved_requests_count_as_taken(self):
        pending = self.make_request(date(2026, 3, 2), date(2026, 3, 4))
        pending.clean()
        pending.state = TimeOffRequest.TO_APPROVE
        pending.save()

        self.assertEqual(
            Allocation.objects.get(pk=self.allocation.pk).taken, Decimal("0.00"))

    def test_balance_accumulates_across_several_approved_requests(self):
        self._approved_request(date(2026, 3, 2), date(2026, 3, 4))   # 3
        self._approved_request(date(2026, 3, 9), date(2026, 3, 11))  # 3

        allocation = Allocation.objects.get(pk=self.allocation.pk)
        self.assertEqual(allocation.taken, Decimal("6.00"))
        self.assertEqual(allocation.remaining, Decimal("14.00"))

    def test_remaining_is_derived_not_stored(self):
        """No column on Allocation holds the balance."""
        columns = {f.name for f in Allocation._meta.get_fields()
                   if hasattr(f, "attname")}
        self.assertNotIn("remaining", columns)
        self.assertNotIn("taken", columns)


# ==========================================================================
# Duration
# ==========================================================================

class DurationTests(TimeOffTestCase):

    def test_duration_counts_working_days_only(self):
        # 2026-03-02 Mon .. 2026-03-08 Sun — 5 working days.
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 8))
        self.assertEqual(request.compute_duration(), Decimal("5"))

    def test_duration_excludes_company_holidays(self):
        Holiday.objects.create(
            name="Holi", date=date(2026, 3, 4), company=self.company)
        request = self.make_request(date(2026, 3, 2), date(2026, 3, 6))
        self.assertEqual(request.compute_duration(), Decimal("4"))

    def test_half_day_on_a_single_date_is_half(self):
        request = self.make_request(
            date(2026, 3, 2), date(2026, 3, 2), half_day="FIRST")
        self.assertEqual(request.compute_duration(), Decimal("0.5"))

    def test_a_request_covering_no_working_days_is_rejected(self):
        # 2026-03-07 Sat .. 2026-03-08 Sun
        request = self.make_request(
            date(2026, 3, 7), date(2026, 3, 8), time_off_type=self.ungated)
        with self.assertRaises(ValidationError) as caught:
            request.clean()
        self.assertIn("no working days", str(caught.exception))

    def test_unpaid_leave_is_flagged_for_loss_of_pay(self):
        request = self.make_request(
            date(2026, 3, 2), date(2026, 3, 4), time_off_type=self.ungated)
        request.clean()
        request.save()
        self.assertTrue(request.is_unpaid)
