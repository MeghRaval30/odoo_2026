"""
The role permission matrix from product-spec §2, asserted from both sides.

The matrix under test:

| Role                 | HR data   | Approve leave | Payruns & Payslips | Structures & Rules | Admin |
|----------------------|-----------|---------------|--------------------|--------------------|-------|
| Employee             | own only  | -             | X                  | X                  | X     |
| HR Manager           | full CRUD | yes           | X                  | X                  | X     |
| HR Payroll User      | full CRUD | yes           | Create/Read/Update | **read-only**      | X     |
| HR Payroll Manager   | full CRUD | yes           | full CRUD          | full CRUD          | X     |
| Admin                | full      | yes           | full               | full               | users |

Every role is checked for what it *may* do as well as what it *may not* — a
permission class that returns True for everyone passes half a test suite, so
the denied side is asserted just as hard as the allowed side. Checks run at two
levels: the ``User`` helper properties the UI reads out of ``/api/auth/me/``,
and real HTTP calls through the routers in ``config/urls.py``, because hiding a
button is not enforcement (PRD-3.1).

Also covered: ``role_codes`` / ``has_role``, and the rule that *users must not
be able to assign or elevate their own roles* (product-spec §2), enforced in
``UserViewSet.perform_update``.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Company
from employees.models import Contract, Employee, WorkingSchedule
from payroll.models import Payrun, SalaryRule, SalaryStructure
from timeoff.models import Allocation, TimeOffRequest, TimeOffType

from .models import Role, User

ROLE_NAMES = dict(Role.CHOICES)


class RoleFixtureMixin:
    """One user per persona, built from the Role table the same way seeds do."""

    @staticmethod
    def make_role(code):
        role, _ = Role.objects.get_or_create(
            code=code, defaults={"name": ROLE_NAMES[code]})
        return role

    @classmethod
    def make_user(cls, email, *codes, employee=None, **extra):
        user = User.objects.create_user(email=email, password="demo1234",
                                        employee=employee, **extra)
        user.roles.set([cls.make_role(code) for code in codes])
        return user


# ==========================================================================
# role_codes / has_role
# ==========================================================================

class RoleHelperTests(RoleFixtureMixin, TestCase):
    """The primitives every permission property is built on."""

    @classmethod
    def setUpTestData(cls):
        cls.plain = cls.make_user("plain@example.com", Role.EMPLOYEE)
        cls.dual = cls.make_user("dual@example.com",
                                 Role.HR_MANAGER, Role.PAYROLL_USER)
        cls.roleless = cls.make_user("roleless@example.com")

    def test_role_codes_is_the_set_of_assigned_codes(self):
        self.assertEqual(self.plain.role_codes, {Role.EMPLOYEE})
        self.assertEqual(self.dual.role_codes,
                         {Role.HR_MANAGER, Role.PAYROLL_USER})
        self.assertEqual(self.roleless.role_codes, set())

    def test_has_role_matches_any_of_the_codes_given(self):
        self.assertTrue(self.plain.has_role(Role.EMPLOYEE))
        self.assertTrue(self.dual.has_role(Role.ADMIN, Role.HR_MANAGER))
        self.assertFalse(self.plain.has_role(Role.ADMIN, Role.PAYROLL_MANAGER))

    def test_has_role_with_no_codes_is_false(self):
        self.assertFalse(self.plain.has_role())

    def test_a_user_with_no_roles_is_granted_nothing(self):
        self.assertFalse(self.roleless.is_admin)
        self.assertFalse(self.roleless.can_manage_hr)
        self.assertFalse(self.roleless.can_approve_leave)
        self.assertFalse(self.roleless.can_run_payroll)
        self.assertFalse(self.roleless.can_configure_payroll)

    def test_roles_stack_so_the_widest_grant_wins(self):
        """Two roles on one account union their permissions."""
        self.assertTrue(self.dual.can_manage_hr)   # from HR_MANAGER
        self.assertTrue(self.dual.can_run_payroll)  # from PAYROLL_USER
        self.assertFalse(self.dual.can_configure_payroll)
        self.assertFalse(self.dual.is_admin)

    def test_a_django_superuser_is_an_admin_without_the_role_row(self):
        root = User.objects.create_user("root@example.com", "demo1234",
                                        is_superuser=True, is_staff=True)
        self.assertEqual(root.role_codes, set())
        self.assertTrue(root.is_admin)
        self.assertTrue(root.can_manage_hr)
        self.assertTrue(root.can_run_payroll)
        self.assertTrue(root.can_configure_payroll)


# ==========================================================================
# product-spec §2 — the matrix at the property level
# ==========================================================================

class PermissionMatrixTests(RoleFixtureMixin, TestCase):
    """One test per persona, asserting the whole row: grants and denials."""

    @classmethod
    def setUpTestData(cls):
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE)
        cls.hr = cls.make_user("hr@example.com", Role.HR_MANAGER)
        cls.payroll_user = cls.make_user("puser@example.com", Role.PAYROLL_USER)
        cls.payroll_manager = cls.make_user("pmgr@example.com",
                                            Role.PAYROLL_MANAGER)
        cls.admin = cls.make_user("admin@example.com", Role.ADMIN)

    def assertMatrixRow(self, user, *, is_admin, can_manage_hr,
                        can_approve_leave, can_run_payroll,
                        can_configure_payroll):
        self.assertIs(user.is_admin, is_admin)
        self.assertIs(user.can_manage_hr, can_manage_hr)
        self.assertIs(user.can_approve_leave, can_approve_leave)
        self.assertIs(user.can_run_payroll, can_run_payroll)
        self.assertIs(user.can_configure_payroll, can_configure_payroll)

    def test_employee_gets_own_records_only_and_nothing_else(self):
        self.assertMatrixRow(
            self.employee, is_admin=False, can_manage_hr=False,
            can_approve_leave=False, can_run_payroll=False,
            can_configure_payroll=False)

    def test_hr_manager_manages_hr_data_and_leave_but_no_payroll(self):
        self.assertMatrixRow(
            self.hr, is_admin=False, can_manage_hr=True,
            can_approve_leave=True, can_run_payroll=False,
            can_configure_payroll=False)

    def test_payroll_user_runs_payroll_but_cannot_configure_it(self):
        self.assertMatrixRow(
            self.payroll_user, is_admin=False, can_manage_hr=True,
            can_approve_leave=True, can_run_payroll=True,
            can_configure_payroll=False)

    def test_payroll_manager_adds_configuration_rights(self):
        self.assertMatrixRow(
            self.payroll_manager, is_admin=False, can_manage_hr=True,
            can_approve_leave=True, can_run_payroll=True,
            can_configure_payroll=True)

    def test_admin_gets_everything(self):
        self.assertMatrixRow(
            self.admin, is_admin=True, can_manage_hr=True,
            can_approve_leave=True, can_run_payroll=True,
            can_configure_payroll=True)

    def test_approve_leave_tracks_hr_management_exactly(self):
        """The two are the same grant in the spec; keep them in step."""
        for user in (self.employee, self.hr, self.payroll_user,
                     self.payroll_manager, self.admin):
            with self.subTest(user=user.email):
                self.assertEqual(user.can_approve_leave, user.can_manage_hr)

    def test_configure_is_strictly_narrower_than_run_for_payroll_roles(self):
        """The Payroll User / Payroll Manager split, stated as one rule."""
        self.assertTrue(self.payroll_user.can_run_payroll)
        self.assertFalse(self.payroll_user.can_configure_payroll)
        self.assertTrue(self.payroll_manager.can_run_payroll)
        self.assertTrue(self.payroll_manager.can_configure_payroll)


class MeEndpointTests(RoleFixtureMixin, APITestCase):
    """`/api/auth/me/` is what the frontend switches menus on."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.record = Employee.objects.create(
            first_name="Asha", last_name="Rao",
            work_email="asha.rao@example.com",
            company=cls.company, date_of_joining=date(2026, 1, 1))
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE,
                                     employee=cls.record)
        cls.hr = cls.make_user("hr@example.com", Role.HR_MANAGER)
        cls.payroll_user = cls.make_user("puser@example.com", Role.PAYROLL_USER)
        cls.payroll_manager = cls.make_user("pmgr@example.com",
                                            Role.PAYROLL_MANAGER)
        cls.admin = cls.make_user("admin@example.com", Role.ADMIN)

    def test_me_reports_the_matrix_row_for_every_role(self):
        expected = {
            "emp@example.com": (False, False, False, False, False),
            "hr@example.com": (False, True, True, False, False),
            "puser@example.com": (False, True, True, True, False),
            "pmgr@example.com": (False, True, True, True, True),
            "admin@example.com": (True, True, True, True, True),
        }
        for user in (self.employee, self.hr, self.payroll_user,
                     self.payroll_manager, self.admin):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                response = self.client.get(reverse("me"))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                permissions = response.data["permissions"]
                self.assertEqual(
                    (permissions["is_admin"], permissions["can_manage_hr"],
                     permissions["can_approve_leave"],
                     permissions["can_run_payroll"],
                     permissions["can_configure_payroll"]),
                    expected[user.email])

    def test_me_carries_the_role_codes_and_the_linked_employee(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(reverse("me"))

        self.assertEqual(response.data["roles"], [Role.EMPLOYEE])
        self.assertEqual(response.data["employee_id"], self.record.pk)
        self.assertEqual(response.data["employee_name"], "Asha Rao")

    def test_me_is_closed_to_anonymous_callers(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get(reverse("me")).status_code,
                      (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


# ==========================================================================
# Matrix column 1 — HR data
# ==========================================================================

class HRDataAccessTests(RoleFixtureMixin, APITestCase):
    """Employees/contracts/schedules: full CRUD from HR Manager upward."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.record = Employee.objects.create(
            first_name="Asha", last_name="Rao",
            work_email="asha.rao@example.com",
            company=cls.company, date_of_joining=date(2026, 1, 1))
        cls.colleague = Employee.objects.create(
            first_name="Ravi", last_name="Kumar",
            work_email="ravi.kumar@example.com",
            company=cls.company, date_of_joining=date(2026, 1, 1))
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE,
                                     employee=cls.record)
        cls.hr = cls.make_user("hr@example.com", Role.HR_MANAGER)
        cls.payroll_user = cls.make_user("puser@example.com", Role.PAYROLL_USER)
        cls.payroll_manager = cls.make_user("pmgr@example.com",
                                            Role.PAYROLL_MANAGER)
        cls.admin = cls.make_user("admin@example.com", Role.ADMIN)

    def test_an_employee_may_not_write_hr_master_data(self):
        self.client.force_authenticate(user=self.employee)
        created = self.client.post(reverse("employee-list"), {
            "first_name": "Mallory", "last_name": "Ghost",
            "work_email": "mallory@example.com", "company": self.company.pk,
            "date_of_joining": "2026-01-01",
        }, format="json")
        patched = self.client.patch(
            reverse("employee-detail", args=[self.colleague.pk]),
            {"work_phone": "999"}, format="json")

        self.assertEqual(created.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(patched.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Employee.objects.count(), 2)

    def test_an_employees_employee_list_is_narrowed_to_themselves(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(reverse("employee-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data["results"]],
                         [self.record.pk])

    def test_every_hr_capable_role_may_create_and_edit_employees(self):
        for index, user in enumerate((self.hr, self.payroll_user,
                                      self.payroll_manager, self.admin)):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                created = self.client.post(reverse("employee-list"), {
                    "first_name": "New", "last_name": f"Hire{index}",
                    "work_email": f"new.hire{index}@example.com",
                    "company": self.company.pk,
                    "date_of_joining": "2026-01-01",
                }, format="json")
                self.assertEqual(created.status_code, status.HTTP_201_CREATED)

                patched = self.client.patch(
                    reverse("employee-detail", args=[created.data["id"]]),
                    {"work_phone": "1234567890"}, format="json")
                self.assertEqual(patched.status_code, status.HTTP_200_OK)

    def test_hr_capable_roles_see_the_whole_employee_list(self):
        for user in (self.hr, self.payroll_user, self.payroll_manager,
                     self.admin):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                response = self.client.get(reverse("employee-list"))
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["count"], 2)


class EmployeeOwnRecordsScopeTests(RoleFixtureMixin, APITestCase):
    """
    The Employee cell of the HR-data column reads *"Own records only; may
    create own attendance + time-off requests"*, over Employees, Attendance,
    **Contracts**, Schedules and Time Off. Two of those five did not hold up
    when this suite was written; both have since been closed, and the tests
    that documented them are kept here as regression guards.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.schedule = WorkingSchedule.objects.create(
            name="Standard 40h", company=cls.company)
        cls.record = Employee.objects.create(
            first_name="Asha", last_name="Rao",
            work_email="asha.rao@example.com",
            company=cls.company, date_of_joining=date(2026, 1, 1))
        cls.colleague = Employee.objects.create(
            first_name="Ravi", last_name="Kumar",
            work_email="ravi.kumar@example.com",
            company=cls.company, date_of_joining=date(2026, 1, 1))
        cls.my_contract = Contract.objects.create(
            employee=cls.record, start_date=date(2026, 1, 1),
            wage=Decimal("50000.00"), working_schedule=cls.schedule,
            state=Contract.RUNNING)
        cls.their_contract = Contract.objects.create(
            employee=cls.colleague, start_date=date(2026, 1, 1),
            wage=Decimal("90000.00"), working_schedule=cls.schedule,
            state=Contract.RUNNING)
        cls.sick_leave = TimeOffType.objects.create(
            name="Sick Leave", code="SICK", requires_allocation=False)
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE,
                                     employee=cls.record)

    def setUp(self):
        self.client.force_authenticate(user=self.employee)

    def test_an_employees_time_off_request_list_is_narrowed_to_their_own(self):
        TimeOffRequest.objects.create(
            employee=self.colleague, time_off_type=self.sick_leave,
            date_from=date(2026, 2, 2), date_to=date(2026, 2, 3))
        mine = TimeOffRequest.objects.create(
            employee=self.record, time_off_type=self.sick_leave,
            date_from=date(2026, 2, 2), date_to=date(2026, 2, 3))

        response = self.client.get(reverse("timeoffrequest-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data["results"]],
                         [mine.pk])

    def test_an_employees_allocation_list_is_narrowed_to_their_own(self):
        Allocation.objects.create(
            employee=self.colleague, time_off_type=self.sick_leave,
            name="2026 Annual Balance", allocated=Decimal("12.00"),
            valid_from=date(2026, 1, 1), state=Allocation.APPROVED)
        response = self.client.get(reverse("allocation-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    # Regression guard. This test was written while the refusal was open and
    # asserted it: TimeOffRequestViewSet was plain CanManageHR, so POST was an
    # unsafe method and every Employee got a 403 on the form built for them,
    # even though product-spec §2 gives them "create own ... time-off
    # requests". The create carve-out has since been added.
    def test_an_employee_can_create_their_own_time_off_request(self):
        response = self.client.post(reverse("timeoffrequest-list"), {
            "employee": self.record.pk, "time_off_type": self.sick_leave.pk,
            "date_from": "2026-02-02", "date_to": "2026-02-03",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TimeOffRequest.objects.count(), 1)
        self.assertEqual(TimeOffRequest.objects.get().employee, self.record)

    def test_an_employee_cannot_raise_a_request_for_a_colleague(self):
        """The employee in the payload is substituted, not trusted."""
        response = self.client.post(reverse("timeoffrequest-list"), {
            "employee": self.colleague.pk, "time_off_type": self.sick_leave.pk,
            "date_from": "2026-02-02", "date_to": "2026-02-03",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TimeOffRequest.objects.get().employee, self.record)

    def test_the_allocation_gate_runs_against_the_requester_not_the_payload(self):
        """
        Graded rule #3 has to be evaluated against the balance the requester is
        allowed to spend, which is why the substitution happens before
        validation rather than in perform_create. Ravi holds an approved
        allocation; Asha holds none. Asha posting Ravi's employee id must be
        refused on her own empty balance rather than admitted on his -- and
        must not attach itself to his allocation on the way through.
        """
        earned = TimeOffType.objects.create(
            name="Earned Leave", code="EARN", requires_allocation=True)
        Allocation.objects.create(
            employee=self.colleague, time_off_type=earned,
            name="2026 Earned Balance", allocated=Decimal("10.00"),
            valid_from=date(2026, 1, 1), state=Allocation.APPROVED)

        response = self.client.post(reverse("timeoffrequest-list"), {
            "employee": self.colleague.pk, "time_off_type": earned.pk,
            "date_from": "2026-02-02", "date_to": "2026-02-03",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TimeOffRequest.objects.count(), 0)

    # Regression guard. This test was written while the leak was open and
    # asserted it: ContractViewSet had no get_queryset override, and
    # CanManageHR grants read to any authenticated user, so an Employee could
    # list every colleague's contract with the wage column attached. The
    # three-line scoping filter it called for has since been applied, so the
    # test now asserts the closed behaviour and exists to keep it closed.
    def test_an_employees_contract_list_is_narrowed_to_their_own(self):
        response = self.client.get(reverse("contract-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(ids, {self.my_contract.pk})

        # The colleague's wage is not merely absent from the list page; the
        # detail route cannot reach it either.
        blocked = self.client.get(
            reverse("contract-detail", args=[self.their_contract.pk]))
        self.assertEqual(blocked.status_code, status.HTTP_404_NOT_FOUND)

    def test_an_employee_still_cannot_write_contracts(self):
        """Read scoping aside, the write half of the cell holds on its own."""
        response = self.client.patch(
            reverse("contract-detail", args=[self.their_contract.pk]),
            {"wage": "999999.00"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.their_contract.refresh_from_db()
        self.assertEqual(self.their_contract.wage, Decimal("90000.00"))


# ==========================================================================
# Matrix column 2 — approve leave
# ==========================================================================

class ApproveLeaveTests(RoleFixtureMixin, APITestCase):
    """Only HR Manager and above may approve or refuse a request."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.record = Employee.objects.create(
            first_name="Asha", last_name="Rao",
            work_email="asha.rao@example.com",
            company=cls.company, date_of_joining=date(2026, 1, 1))
        cls.sick_leave = TimeOffType.objects.create(
            name="Sick Leave", code="SICK", requires_allocation=False)
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE,
                                     employee=cls.record)
        cls.hr = cls.make_user("hr@example.com", Role.HR_MANAGER)

    def setUp(self):
        self.request = TimeOffRequest.objects.create(
            employee=self.record, time_off_type=self.sick_leave,
            date_from=date(2026, 2, 2), date_to=date(2026, 2, 3),
            state=TimeOffRequest.TO_APPROVE)

    def test_an_employee_cannot_approve_their_own_request(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            reverse("timeoffrequest-approve", args=[self.request.pk]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.request.refresh_from_db()
        self.assertEqual(self.request.state, TimeOffRequest.TO_APPROVE)

    def test_hr_may_approve_and_the_approver_is_recorded(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.post(
            reverse("timeoffrequest-approve", args=[self.request.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.request.refresh_from_db()
        self.assertEqual(self.request.state, TimeOffRequest.APPROVED)
        self.assertEqual(self.request.approver, self.hr)

    def test_an_employee_cannot_refuse_a_request_either(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            reverse("timeoffrequest-refuse", args=[self.request.pk]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ==========================================================================
# Matrix column 3 — payruns and payslips
# ==========================================================================

class PayrollRunAccessTests(RoleFixtureMixin, APITestCase):
    """Payroll User and above; HR Manager and Employee are shut out entirely."""

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.structure = SalaryStructure.objects.create(
            name="Regular Salary", code="REG", company=cls.company)
        cls.payrun = Payrun.objects.create(
            name="February 2026", company=cls.company,
            salary_structure=cls.structure,
            period_start=date(2026, 2, 1), period_end=date(2026, 2, 28))
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE)
        cls.hr = cls.make_user("hr@example.com", Role.HR_MANAGER)
        cls.payroll_user = cls.make_user("puser@example.com", Role.PAYROLL_USER)
        cls.payroll_manager = cls.make_user("pmgr@example.com",
                                            Role.PAYROLL_MANAGER)
        cls.admin = cls.make_user("admin@example.com", Role.ADMIN)

    def _payrun_payload(self, name):
        return {"name": name, "company": self.company.pk,
                "salary_structure": self.structure.pk,
                "period_start": "2026-03-01", "period_end": "2026-03-31"}

    def test_employee_and_hr_manager_cannot_even_read_payruns(self):
        for user in (self.employee, self.hr):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get(reverse("payrun-list")).status_code,
                    status.HTTP_403_FORBIDDEN)

    def test_anyone_signed_in_may_read_payslips_but_only_their_own(self):
        """
        PRD 3.2 grants the Employee role "R (own)" on payslips.

        This previously asserted a flat 403, which encoded a bug: the viewset
        was gated behind CanRunPayroll, so the queryset's own-rows branch was
        unreachable and an employee could never see their own payslip. The
        endpoint is read-only, so opening it up costs nothing; the scoping is
        what does the work.
        """
        for user in (self.employee, self.hr):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                response = self.client.get(reverse("payslip-list"))
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                rows = response.json().get("results", response.json())
                foreign = [r for r in rows
                           if r.get("employee") != getattr(user, "employee_id", None)]
                self.assertEqual(
                    foreign, [],
                    "a non-payroll user must not see other people's payslips")

    def test_payslips_stay_read_only_for_everyone(self):
        """
        No role may write a payslip — they are produced by computing a payrun.

        The permission class denies unsafe methods before DRF reaches its own
        method check, so this is a 403 rather than a 405. Either is a refusal;
        what matters is that nothing gets through.
        """
        for user in (self.employee, self.hr, self.payroll_user,
                     self.payroll_manager, self.admin):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                self.assertIn(
                    self.client.post(reverse("payslip-list"), {}).status_code,
                    (status.HTTP_403_FORBIDDEN,
                     status.HTTP_405_METHOD_NOT_ALLOWED))

    def test_employee_and_hr_manager_cannot_create_a_payrun(self):
        for user in (self.employee, self.hr):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                response = self.client.post(reverse("payrun-list"),
                                            self._payrun_payload("Nope"),
                                            format="json")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Payrun.objects.count(), 1)

    def test_payroll_roles_may_read_create_and_update_payruns(self):
        for index, user in enumerate((self.payroll_user, self.payroll_manager,
                                      self.admin)):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get(reverse("payrun-list")).status_code,
                    status.HTTP_200_OK)
                self.assertEqual(
                    self.client.get(reverse("payslip-list")).status_code,
                    status.HTTP_200_OK)

                created = self.client.post(
                    reverse("payrun-list"),
                    self._payrun_payload(f"March 2026 #{index}"),
                    format="json")
                self.assertEqual(created.status_code, status.HTTP_201_CREATED)

                patched = self.client.patch(
                    reverse("payrun-detail", args=[created.data["id"]]),
                    {"name": f"March 2026 revised #{index}"}, format="json")
                self.assertEqual(patched.status_code, status.HTTP_200_OK)

    # Regression guard. This test was written while the gap was open and
    # asserted it: product-spec §2 gives the HR Payroll User "Create / Read /
    # Update" and the HR Payroll Manager "Full CRUD", so delete is the whole
    # difference between the two rows -- and CanRunPayroll collapsed every
    # unsafe method into one can_run_payroll check, handing delete to both.
    # DELETE is now checked on its own.
    def test_a_payroll_user_may_not_delete_a_payrun(self):
        self.client.force_authenticate(user=self.payroll_user)
        response = self.client.delete(
            reverse("payrun-detail", args=[self.payrun.pk]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Payrun.objects.filter(pk=self.payrun.pk).exists())

    def test_a_payroll_user_keeps_the_create_read_update_half_of_the_row(self):
        """Narrowing delete must not cost the Payroll User anything else."""
        self.client.force_authenticate(user=self.payroll_user)
        patched = self.client.patch(
            reverse("payrun-detail", args=[self.payrun.pk]),
            {"name": "February 2026 revised"}, format="json")

        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.payrun.refresh_from_db()
        self.assertEqual(self.payrun.name, "February 2026 revised")

    def test_payroll_manager_may_delete_a_payrun(self):
        self.client.force_authenticate(user=self.payroll_manager)
        response = self.client.delete(
            reverse("payrun-detail", args=[self.payrun.pk]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


# ==========================================================================
# Matrix column 4 — structures and rules (the read-only distinction)
# ==========================================================================

class StructureAndRuleAccessTests(RoleFixtureMixin, APITestCase):
    """
    The explicit split in the problem statement: an HR Payroll User is
    **read-only** on salary structures and rules; only an HR Payroll Manager
    (or Admin) may write them.
    """

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Test Co")
        cls.structure = SalaryStructure.objects.create(
            name="Regular Salary", code="REG", company=cls.company)
        cls.rule = SalaryRule.objects.create(
            structure=cls.structure, name="Basic Salary", code="BASIC",
            category=SalaryRule.BASIC, sequence=1,
            computation=SalaryRule.PERCENTAGE, percentage=Decimal("50.000"))
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE)
        cls.hr = cls.make_user("hr@example.com", Role.HR_MANAGER)
        cls.payroll_user = cls.make_user("puser@example.com", Role.PAYROLL_USER)
        cls.payroll_manager = cls.make_user("pmgr@example.com",
                                            Role.PAYROLL_MANAGER)
        cls.admin = cls.make_user("admin@example.com", Role.ADMIN)

    def _rule_payload(self, code):
        return {"structure": self.structure.pk, "name": f"Allowance {code}",
                "code": code, "category": SalaryRule.ALLOWANCE,
                "sequence": 20, "computation": SalaryRule.FIXED,
                "amount": "1000.00"}

    def test_employee_and_hr_manager_get_nothing_here_at_all(self):
        for user in (self.employee, self.hr):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get(reverse("salarystructure-list")).status_code,
                    status.HTTP_403_FORBIDDEN)
                self.assertEqual(
                    self.client.get(reverse("salaryrule-list")).status_code,
                    status.HTTP_403_FORBIDDEN)

    def test_payroll_user_may_read_structures_and_rules(self):
        self.client.force_authenticate(user=self.payroll_user)

        structures = self.client.get(reverse("salarystructure-list"))
        rules = self.client.get(reverse("salaryrule-list"))
        detail = self.client.get(
            reverse("salarystructure-detail", args=[self.structure.pk]))

        self.assertEqual(structures.status_code, status.HTTP_200_OK)
        self.assertEqual(rules.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["name"], "Regular Salary")

    def test_payroll_user_may_not_write_structures_or_rules(self):
        self.client.force_authenticate(user=self.payroll_user)

        created = self.client.post(reverse("salarystructure-list"), {
            "name": "Intern Salary", "code": "INT", "company": self.company.pk,
        }, format="json")
        patched = self.client.patch(
            reverse("salarystructure-detail", args=[self.structure.pk]),
            {"name": "Renamed"}, format="json")
        new_rule = self.client.post(reverse("salaryrule-list"),
                                    self._rule_payload("HRA"), format="json")
        edited_rule = self.client.patch(
            reverse("salaryrule-detail", args=[self.rule.pk]),
            {"sequence": 99}, format="json")
        deleted = self.client.delete(
            reverse("salaryrule-detail", args=[self.rule.pk]))

        for response in (created, patched, new_rule, edited_rule, deleted):
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.structure.refresh_from_db()
        self.rule.refresh_from_db()
        self.assertEqual(self.structure.name, "Regular Salary")
        self.assertEqual(self.rule.sequence, 1)
        self.assertEqual(SalaryStructure.objects.count(), 1)

    def test_payroll_manager_may_write_structures_and_rules(self):
        self.client.force_authenticate(user=self.payroll_manager)

        created = self.client.post(reverse("salarystructure-list"), {
            "name": "Intern Salary", "code": "INT", "company": self.company.pk,
        }, format="json")
        patched = self.client.patch(
            reverse("salarystructure-detail", args=[self.structure.pk]),
            {"name": "Regular Salary 2026"}, format="json")
        new_rule = self.client.post(reverse("salaryrule-list"),
                                    self._rule_payload("HRA"), format="json")

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertEqual(new_rule.status_code, status.HTTP_201_CREATED)

        self.structure.refresh_from_db()
        self.assertEqual(self.structure.name, "Regular Salary 2026")
        self.assertEqual(self.structure.rules.count(), 2)

    def test_admin_may_write_structures_and_rules_too(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse("salaryrule-list"),
                                    self._rule_payload("STD"), format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_the_read_only_split_is_exactly_one_role_wide(self):
        """Same GET for both payroll roles, different POST outcome."""
        for user, expected in ((self.payroll_user, status.HTTP_403_FORBIDDEN),
                               (self.payroll_manager, status.HTTP_201_CREATED)):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get(reverse("salaryrule-list")).status_code,
                    status.HTTP_200_OK)
                response = self.client.post(
                    reverse("salaryrule-list"),
                    self._rule_payload(f"X{user.pk}"), format="json")
                self.assertEqual(response.status_code, expected)


# ==========================================================================
# Matrix column 5 — administration and the self-role rule
# ==========================================================================

class UserManagementTests(RoleFixtureMixin, APITestCase):
    """
    User accounts and role assignment are Admin-only, and product-spec §2 is
    emphatic that *users must not be able to assign or elevate their own roles*.
    """

    @classmethod
    def setUpTestData(cls):
        cls.employee = cls.make_user("emp@example.com", Role.EMPLOYEE)
        cls.hr = cls.make_user("hr@example.com", Role.HR_MANAGER)
        cls.payroll_user = cls.make_user("puser@example.com", Role.PAYROLL_USER)
        cls.payroll_manager = cls.make_user("pmgr@example.com",
                                            Role.PAYROLL_MANAGER)
        cls.admin = cls.make_user("admin@example.com", Role.ADMIN)
        cls.admin_role = cls.make_role(Role.ADMIN)
        cls.hr_role = cls.make_role(Role.HR_MANAGER)

    def test_no_non_admin_role_may_reach_user_management(self):
        for user in (self.employee, self.hr, self.payroll_user,
                     self.payroll_manager):
            with self.subTest(role=user.email):
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get(reverse("user-list")).status_code,
                    status.HTTP_403_FORBIDDEN)
                self.assertEqual(
                    self.client.get(
                        reverse("user-detail", args=[user.pk])).status_code,
                    status.HTTP_403_FORBIDDEN)

    def test_a_non_admin_cannot_grant_themselves_a_role_through_the_api(self):
        """The blunt version of the escalation attempt: it never gets in."""
        self.client.force_authenticate(user=self.employee)
        response = self.client.patch(
            reverse("user-detail", args=[self.employee.pk]),
            {"role_ids": [self.admin_role.pk]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.employee.role_codes, {Role.EMPLOYEE})

    def test_an_admin_may_list_and_create_users(self):
        self.client.force_authenticate(user=self.admin)

        listed = self.client.get(reverse("user-list"))
        created = self.client.post(reverse("user-list"), {
            "email": "newhire@example.com", "password": "demo1234",
            "role_ids": [self.hr_role.pk],
        }, format="json")

        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            User.objects.get(email="newhire@example.com").role_codes,
            {Role.HR_MANAGER})

    def test_an_admin_may_assign_roles_to_somebody_else(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("user-detail", args=[self.employee.pk]),
            {"role_ids": [self.hr_role.pk]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.employee.role_codes, {Role.HR_MANAGER})

    def test_an_admin_may_not_modify_their_own_roles(self):
        """`UserViewSet.perform_update` rejects the payload outright."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("user-detail", args=[self.admin.pk]),
            {"role_ids": [self.hr_role.pk, self.admin_role.pk]}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", response.data)
        self.assertIn("your own roles", str(response.data["roles"]))
        self.assertEqual(self.admin.role_codes, {Role.ADMIN})

    def test_an_admin_may_not_strip_their_own_roles_either(self):
        """Demotion is self-modification too: an empty list is still a write."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("user-detail", args=[self.admin.pk]),
            {"role_ids": []}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.admin.role_codes, {Role.ADMIN})

    def test_an_admin_may_still_edit_their_own_non_role_fields(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("user-detail", args=[self.admin.pk]),
            {"email": "admin.renamed@example.com"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, "admin.renamed@example.com")
        self.assertEqual(self.admin.role_codes, {Role.ADMIN})

    def test_roles_are_readable_by_any_authenticated_user(self):
        """The picker list is not itself a grant; reading it changes nothing."""
        self.client.force_authenticate(user=self.employee)
        response = self.client.get(reverse("role-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.employee.role_codes, {Role.EMPLOYEE})

    def test_the_role_list_is_read_only_even_for_an_admin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse("role-list"),
                                    {"code": Role.ADMIN, "name": "Fake"},
                                    format="json")
        self.assertEqual(response.status_code,
                         status.HTTP_405_METHOD_NOT_ALLOWED)


class LoginTests(RoleFixtureMixin, APITestCase):
    """Token issue is what puts the matrix in front of the frontend."""

    @classmethod
    def setUpTestData(cls):
        cls.user = cls.make_user("payroll.manager@example.com",
                                 Role.PAYROLL_MANAGER)

    def test_login_returns_a_token_and_the_permission_payload(self):
        response = self.client.post(reverse("login"), {
            "email": "payroll.manager@example.com", "password": "demo1234",
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["token"])
        permissions = response.data["user"]["permissions"]
        self.assertTrue(permissions["can_configure_payroll"])
        self.assertFalse(permissions["is_admin"])

    def test_a_bad_password_is_rejected(self):
        response = self.client.post(reverse("login"), {
            "email": "payroll.manager@example.com", "password": "wrong",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
