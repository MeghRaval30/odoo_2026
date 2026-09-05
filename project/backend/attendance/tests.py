"""
Graded attendance behaviour: derived worked hours and the one-open-session rule.

Three things are proved here, against a throwaway database inside a rolled-back
transaction so the cases can be run selectively and in any order:

1. **Hours are derived, never stored.** ``worked_hours`` and ``elapsed_hours``
   are properties over ``check_in`` / ``check_out`` (product-spec §4,
   Attendance: *"System-generated from check in/out"*). The serializer exposes
   them read-only, so a client can never post a number of hours.
2. **Exactly one open session per employee.** The model carries a
   ``one_open_attendance_session_per_employee`` unique constraint;
   ``Attendance.check_in_employee`` is idempotent and hands back the existing
   open row instead of tripping it.
3. **Ownership is forced server-side.** product-spec §2 gives the Employee role
   "own records only; may create own attendance". ``perform_create`` rewrites
   the ``employee`` field from the authenticated user rather than trusting the
   payload, so posting someone else's employee id cannot plant a record on them.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, User
from core.models import Company
from employees.models import Employee

from .models import Attendance


class AttendanceFixtureMixin:
    """Employees, and user accounts linked to them, built the cheap way."""

    @staticmethod
    def build_employee(company, first, last):
        return Employee.objects.create(
            first_name=first, last_name=last,
            work_email=f"{first.lower()}.{last.lower()}@example.com",
            company=company, date_of_joining=date(2026, 1, 1),
        )

    @staticmethod
    def build_user(email, employee=None, role_codes=()):
        user = User.objects.create_user(email=email, password="demo1234",
                                        employee=employee)
        for code in role_codes:
            role, _ = Role.objects.get_or_create(
                code=code, defaults={"name": code.replace("_", " ").title()})
            user.roles.add(role)
        return user


# ==========================================================================
# Derived hours — worked_hours and elapsed_hours
# ==========================================================================

class WorkedHoursTests(AttendanceFixtureMixin, TestCase):
    """worked_hours is a property over the two timestamps, not a column."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.employee = Employee.objects.create(
            first_name="Asha", last_name="Rao",
            work_email="asha.rao@example.com",
            company=cls.company, date_of_joining=date(2026, 1, 1),
        )

    def _session(self, hours_ago, duration=None):
        check_in = timezone.now() - timedelta(hours=hours_ago)
        return Attendance.objects.create(
            employee=self.employee, check_in=check_in,
            check_out=check_in + duration if duration else None,
        )

    def test_worked_hours_is_the_span_between_check_in_and_check_out(self):
        session = self._session(9, timedelta(hours=8))
        self.assertEqual(session.worked_hours, Decimal("8.00"))

    def test_worked_hours_keeps_two_decimal_places_for_part_hours(self):
        session = self._session(9, timedelta(hours=6, minutes=56))
        # 6h56m == 6.9333h, rounded to the model's two decimal places.
        self.assertEqual(session.worked_hours, Decimal("6.93"))

    def test_worked_hours_is_zero_while_the_session_is_still_open(self):
        session = self._session(3)
        self.assertIsNone(session.check_out)
        self.assertTrue(session.is_open)
        self.assertEqual(session.worked_hours, Decimal("0.00"))

    def test_elapsed_hours_ticks_on_an_open_session(self):
        session = self._session(2.5)
        self.assertEqual(session.worked_hours, Decimal("0.00"))
        self.assertAlmostEqual(float(session.elapsed_hours), 2.5, places=2)

    def test_elapsed_hours_freezes_at_worked_hours_once_closed(self):
        session = self._session(9, timedelta(hours=8))
        self.assertEqual(session.elapsed_hours, session.worked_hours)

    def test_worked_hours_is_not_a_writable_serializer_field(self):
        """Derived values must never be accepted as input (product-spec 4)."""
        from .api import AttendanceSerializer

        serializer = AttendanceSerializer()
        self.assertTrue(serializer.fields["worked_hours"].read_only)
        self.assertTrue(serializer.fields["elapsed_hours"].read_only)


# ==========================================================================
# The check-in widget — one open session per employee
# ==========================================================================

class CheckInSessionTests(AttendanceFixtureMixin, TestCase):
    """
    ``one_open_attendance_session_per_employee`` allows a single open row.
    check_in_employee must therefore be idempotent, not a second INSERT.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.employee = cls.build_employee(cls.company, "Ravi", "Kumar")
        cls.colleague = cls.build_employee(cls.company, "Nina", "Das")

    def test_check_in_creates_an_open_session(self):
        session, created = Attendance.check_in_employee(self.employee)

        self.assertTrue(created)
        self.assertTrue(session.is_open)
        self.assertIsNone(session.check_out)
        self.assertEqual(session.employee, self.employee)
        self.assertEqual(self.employee.attendances.count(), 1)

    def test_checking_in_twice_returns_the_same_open_session(self):
        first, first_created = Attendance.check_in_employee(self.employee)
        second, second_created = Attendance.check_in_employee(self.employee)

        self.assertTrue(first_created)
        self.assertFalse(second_created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            Attendance.objects.filter(employee=self.employee).count(), 1)

    def test_open_session_for_finds_only_the_unclosed_row(self):
        closed_in = timezone.now() - timedelta(days=1)
        Attendance.objects.create(
            employee=self.employee, check_in=closed_in,
            check_out=closed_in + timedelta(hours=8))
        self.assertIsNone(Attendance.open_session_for(self.employee))

        opened, _ = Attendance.check_in_employee(self.employee)
        self.assertEqual(Attendance.open_session_for(self.employee), opened)

    def test_the_constraint_is_per_employee_not_global(self):
        mine, _ = Attendance.check_in_employee(self.employee)
        theirs, created = Attendance.check_in_employee(self.colleague)

        self.assertTrue(created)
        self.assertNotEqual(mine.pk, theirs.pk)
        self.assertEqual(Attendance.objects.filter(check_out__isnull=True).count(), 2)

    def test_check_out_closes_the_open_session_and_stamps_check_out(self):
        opened, _ = Attendance.check_in_employee(self.employee)
        opened.check_in = timezone.now() - timedelta(hours=8)
        opened.save(update_fields=["check_in"])

        closed = Attendance.check_out_employee(self.employee)

        self.assertEqual(closed.pk, opened.pk)
        self.assertIsNotNone(closed.check_out)
        self.assertFalse(closed.is_open)
        self.assertAlmostEqual(float(closed.worked_hours), 8.0, places=1)
        self.assertIsNone(Attendance.open_session_for(self.employee))

    def test_check_out_with_no_open_session_returns_none(self):
        self.assertIsNone(Attendance.check_out_employee(self.employee))

    def test_a_closed_session_frees_the_slot_for_a_new_check_in(self):
        first, _ = Attendance.check_in_employee(self.employee)
        first.check_in = timezone.now() - timedelta(hours=4)
        first.save(update_fields=["check_in"])
        Attendance.check_out_employee(self.employee)

        second, created = Attendance.check_in_employee(self.employee)

        self.assertTrue(created)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(self.employee.attendances.count(), 2)


# ==========================================================================
# The widget endpoints — an employee may act on their own attendance
# ==========================================================================

class AttendanceWidgetEndpointTests(AttendanceFixtureMixin, APITestCase):
    """PRD-5.5.5: the check-in widget is explicitly employee-facing."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.employee = cls.build_employee(cls.company, "Asha", "Rao")
        cls.user = cls.build_user("asha.rao@example.com", cls.employee,
                                  [Role.EMPLOYEE])

    def setUp(self):
        self.client.force_authenticate(user=self.user)

    def test_an_employee_can_check_themselves_in(self):
        response = self.client.post(reverse("attendance-check-in"))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["created"])
        session = Attendance.open_session_for(self.employee)
        self.assertIsNotNone(session)
        self.assertEqual(response.data["session"]["id"], session.pk)

    def test_checking_in_twice_over_http_reuses_the_open_session(self):
        first = self.client.post(reverse("attendance-check-in"))
        second = self.client.post(reverse("attendance-check-in"))

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertFalse(second.data["created"])
        self.assertEqual(first.data["session"]["id"],
                         second.data["session"]["id"])
        self.assertEqual(self.employee.attendances.count(), 1)

    def test_check_out_closes_the_session_over_http(self):
        self.client.post(reverse("attendance-check-in"))
        response = self.client.post(reverse("attendance-check-out"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["check_out"])
        self.assertFalse(response.data["is_open"])

    def test_check_out_without_an_open_session_is_a_bad_request(self):
        response = self.client.post(reverse("attendance-check-out"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_status_endpoint_drives_the_red_green_indicator(self):
        before = self.client.get(reverse("attendance-status"))
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        self.assertFalse(before.data["checked_in"])

        self.client.post(reverse("attendance-check-in"))
        after = self.client.get(reverse("attendance-status"))
        self.assertTrue(after.data["checked_in"])
        self.assertIsNotNone(after.data["session"])

    def test_an_account_with_no_employee_link_gets_a_clear_error(self):
        orphan = self.build_user("orphan@example.com", None, [Role.EMPLOYEE])
        self.client.force_authenticate(user=orphan)

        response = self.client.post(reverse("attendance-check-in"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================================
# perform_create forces ownership — the important one
# ==========================================================================

class AttendanceOwnershipTests(AttendanceFixtureMixin, APITestCase):
    """
    product-spec §2: the Employee role may create *own* attendance only.

    A malicious or careless payload naming another employee must not be
    honoured — the record has to land on the caller.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.employee = cls.build_employee(cls.company, "Asha", "Rao")
        cls.victim = cls.build_employee(cls.company, "Ravi", "Kumar")
        cls.user = cls.build_user("asha.rao@example.com", cls.employee,
                                  [Role.EMPLOYEE])
        cls.hr_user = cls.build_user("hr@example.com", None, [Role.HR_MANAGER])

    def _payload(self, employee):
        check_in = timezone.now() - timedelta(hours=8)
        return {
            "employee": employee.pk,
            "check_in": check_in.isoformat(),
            "check_out": (check_in + timedelta(hours=8)).isoformat(),
        }

    def test_posting_someone_elses_employee_id_records_it_against_yourself(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(reverse("attendance-list"),
                                    self._payload(self.victim), format="json")

        self.assertIn(response.status_code,
                      (status.HTTP_200_OK, status.HTTP_201_CREATED))
        self.assertEqual(self.victim.attendances.count(), 0)
        self.assertEqual(self.employee.attendances.count(), 1)
        created = Attendance.objects.get()
        self.assertEqual(created.employee, self.employee)
        self.assertEqual(response.data["employee"], self.employee.pk)

    def test_posting_your_own_employee_id_is_of_course_still_yours(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(reverse("attendance-list"),
                                    self._payload(self.employee), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attendance.objects.get().employee, self.employee)

    def test_hr_may_still_create_attendance_for_anyone(self):
        """The override applies to non-HR callers only."""
        self.client.force_authenticate(user=self.hr_user)

        response = self.client.post(reverse("attendance-list"),
                                    self._payload(self.victim), format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Attendance.objects.get().employee, self.victim)

    def test_an_account_with_no_employee_link_cannot_create_attendance(self):
        orphan = self.build_user("orphan@example.com", None, [Role.EMPLOYEE])
        self.client.force_authenticate(user=orphan)

        response = self.client.post(reverse("attendance-list"),
                                    self._payload(self.victim), format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Attendance.objects.count(), 0)


# ==========================================================================
# Role gating on the HR-facing actions
# ==========================================================================

class AttendancePermissionTests(AttendanceFixtureMixin, APITestCase):
    """
    ``CanManageHR`` guards everything outside ``SELF_SERVICE_ACTIONS``, and
    ``get_queryset`` narrows reads to the caller's own rows.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.employee = cls.build_employee(cls.company, "Asha", "Rao")
        cls.colleague = cls.build_employee(cls.company, "Ravi", "Kumar")
        cls.user = cls.build_user("asha.rao@example.com", cls.employee,
                                  [Role.EMPLOYEE])
        cls.hr_user = cls.build_user("hr@example.com", None, [Role.HR_MANAGER])

        yesterday = timezone.now() - timedelta(days=1)
        cls.my_record = Attendance.objects.create(
            employee=cls.employee, check_in=yesterday,
            check_out=yesterday + timedelta(hours=8))
        cls.their_record = Attendance.objects.create(
            employee=cls.colleague, check_in=yesterday,
            check_out=yesterday + timedelta(hours=7))

    def test_an_employee_is_refused_the_hr_only_write_actions(self):
        self.client.force_authenticate(user=self.user)
        detail = reverse("attendance-detail", args=[self.my_record.pk])

        patched = self.client.patch(detail, {"notes": "fiddled"}, format="json")
        deleted = self.client.delete(detail)

        self.assertEqual(patched.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(deleted.status_code, status.HTTP_403_FORBIDDEN)

    def test_the_same_employee_is_allowed_the_check_in_action(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse("attendance-check-in"))
        self.assertIn(response.status_code,
                      (status.HTTP_200_OK, status.HTTP_201_CREATED))

    def test_an_employees_list_is_filtered_to_their_own_records(self):
        # Reads are permitted (product-spec §2 grants "own records only"), but
        # get_queryset does the narrowing — the row count is the assertion.
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("attendance-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in response.data["results"]]
        self.assertEqual(ids, [self.my_record.pk])
        self.assertNotIn(self.their_record.pk, ids)

    def test_an_employee_cannot_reach_a_colleagues_detail_row(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("attendance-detail", args=[self.their_record.pk]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_hr_lists_every_employees_attendance(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get(reverse("attendance-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {self.my_record.pk, self.their_record.pk})

    def test_hr_may_correct_a_record_and_the_edit_is_attributed(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.patch(
            reverse("attendance-detail", args=[self.their_record.pk]),
            {"notes": "Corrected by HR"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.their_record.refresh_from_db()
        self.assertTrue(self.their_record.is_manually_edited)
        self.assertEqual(self.their_record.edited_by, self.hr_user)

    def test_anonymous_callers_get_nothing(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(reverse("attendance-list")).status_code,
                      (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertIn(self.client.post(reverse("attendance-check-in")).status_code,
                      (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
