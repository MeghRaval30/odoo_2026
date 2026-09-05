"""
The security controls, and the ways somebody would try to get round them.

Each test here names an attack rather than a function: point a salary at your
own account, punch a clock you were not at, approve your own request, grant
yourself a role, sign in from somewhere you should not be, or keep using a
token after the account was disabled. A control with no test is a control that
works until the day it matters.
"""

from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from core.models import Company
from employees.models import Employee
from .models import (AuditLog, LoginAttempt, NetworkPolicy, ProfileChangeRequest,
                     Role, SecuritySetting, User)
from .security_session import SessionActivity

ROLE_NAMES = dict(Role.CHOICES)


class SecurityFixture(APITestCase):
    @classmethod
    def make_role(cls, code):
        role, _ = Role.objects.get_or_create(code=code,
                                             defaults={"name": ROLE_NAMES[code]})
        return role

    @classmethod
    def make_employee(cls, first, last, **extra):
        return Employee.objects.create(
            first_name=first, last_name=last, company=cls.company,
            work_email=f"{first}.{last}@oxp.com".lower(),
            date_of_joining=date(2025, 1, 1), **extra)

    @classmethod
    def make_user(cls, email, *codes, employee=None):
        user = User.objects.create_user(email=email, password="demo1234pw",
                                        employee=employee)
        user.roles.set([cls.make_role(c) for c in codes])
        return user

    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(name="OXP Pvt Ltd")
        cls.alice = cls.make_employee("Alice", "Kaur",
                                      bank_account_number="50111234567890",
                                      bank_ifsc="HDFC0001234")
        cls.bob = cls.make_employee("Bob", "Rao")
        cls.employee = cls.make_user("alice@oxp.com", Role.EMPLOYEE,
                                     employee=cls.alice)
        cls.hr = cls.make_user("hr@oxp.com", Role.HR_MANAGER, employee=cls.bob)
        cls.admin = cls.make_user("admin@oxp.com", Role.ADMIN)

    def setUp(self):
        SecuritySetting.objects.all().delete()


# ==========================================================================
# Capabilities
# ==========================================================================

class CapabilityMatrixTests(SecurityFixture):

    def test_holding_two_roles_grants_the_union_of_both(self):
        """
        The mockup's access note says an account may be given "one or more
        roles". A user with HR Manager *and* Payroll User must therefore be
        able to do everything either can — not merely what the higher one can.
        """
        from . import capabilities as caps
        combined = self.make_user("both@oxp.com", Role.HR_MANAGER,
                                  Role.PAYROLL_USER)
        self.assertIn(caps.EMPLOYEE_WRITE, combined.capabilities)
        self.assertIn(caps.PAYRUN_WRITE, combined.capabilities)
        self.assertNotIn(caps.PAYRUN_DELETE, combined.capabilities)
        self.assertNotIn(caps.USER_MANAGE, combined.capabilities)

    def test_an_hr_manager_has_no_payroll_capability_at_all(self):
        """PDF §3: HR Manager, "with no access to payroll features"."""
        from . import capabilities as caps
        held = self.hr.capabilities
        for capability in (caps.PAYRUN_READ, caps.PAYRUN_WRITE,
                           caps.PAYSLIP_READ_ALL, caps.SALARY_CONFIG_READ,
                           caps.DASHBOARD_PAYROLL):
            with self.subTest(capability=capability):
                self.assertNotIn(capability, held)

    def test_a_payroll_user_may_write_a_payrun_but_never_delete_one(self):
        """
        "Create, Read, and Update access to Payruns and Payslips" — the absent
        D is the entire difference from the Payroll Manager row.
        """
        from . import capabilities as caps
        user = self.make_user("puser@oxp.com", Role.PAYROLL_USER)
        self.assertIn(caps.PAYRUN_WRITE, user.capabilities)
        self.assertNotIn(caps.PAYRUN_DELETE, user.capabilities)
        self.assertIn(caps.SALARY_CONFIG_READ, user.capabilities)
        self.assertNotIn(caps.SALARY_CONFIG_WRITE, user.capabilities)

    def test_navigation_hides_what_the_role_cannot_reach(self):
        self.client.force_authenticate(user=self.employee)
        nav = self.client.get(reverse("me")).data["navigation"]
        keys = {group["key"] for group in nav}
        self.assertIn("dashboard", keys)
        self.assertIn("attendance", keys)
        self.assertIn("timeoff", keys)
        self.assertNotIn("payroll", keys)
        self.assertNotIn("employees", keys)
        self.assertNotIn("admin", keys)

    def test_an_admin_sees_every_menu(self):
        self.client.force_authenticate(user=self.admin)
        nav = self.client.get(reverse("me")).data["navigation"]
        keys = {group["key"] for group in nav}
        for expected in ("employees", "contracts", "attendance", "timeoff",
                         "payroll", "admin"):
            with self.subTest(menu=expected):
                self.assertIn(expected, keys)

    def test_each_role_lands_on_its_own_dashboard(self):
        cases = [(self.employee, "employee"), (self.hr, "hr"),
                 (self.admin, "admin")]
        for user, expected in cases:
            with self.subTest(user=user.email):
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get(reverse("me")).data["home_dashboard"],
                    expected)


# ==========================================================================
# Self service
# ==========================================================================

class SelfServiceTests(SecurityFixture):

    def test_an_employee_edits_their_own_phone_directly(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.patch(reverse("my-profile-update"),
                                     {"work_phone": "+91 90000 00001"},
                                     format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.work_phone, "+91 90000 00001")
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.PROFILE_EDITED).exists())

    def test_a_bank_account_cannot_be_changed_directly(self):
        """
        The attack this closes: quietly repoint your salary the day before a
        payrun. The field must go through review, and the refusal has to say so
        rather than silently dropping the value.
        """
        self.client.force_authenticate(user=self.employee)
        response = self.client.patch(reverse("my-profile-update"),
                                     {"bank_account_number": "99999999999999"},
                                     format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("change request", response.data["detail"])
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.bank_account_number, "50111234567890")

    def test_a_bank_change_goes_through_review_and_is_flagged_sensitive(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(
            reverse("my-profile-request"),
            {"field": "bank_account_number", "new_value": "99999999999999",
             "reason": "Changed banks"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_sensitive"])

        # Not applied until somebody approves it.
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.bank_account_number, "50111234567890")

        change = ProfileChangeRequest.objects.get()
        self.client.force_authenticate(user=self.hr)
        approve = self.client.post(
            reverse("profilechangerequest-approve", args=[change.pk]),
            {"note": "ID checked"}, format="json")
        self.assertEqual(approve.status_code, status.HTTP_200_OK)

        self.alice.refresh_from_db()
        self.assertEqual(self.alice.bank_account_number, "99999999999999")

    def test_nobody_approves_a_change_to_their_own_record(self):
        """
        An HR Manager holds `profile.approve`. Without this check they could
        approve their own bank-account change and the control would be
        decorative.
        """
        change = ProfileChangeRequest.objects.create(
            employee=self.bob, requested_by=self.hr,
            field="bank_account_number", old_value="", new_value="123")
        self.client.force_authenticate(user=self.hr)
        response = self.client.post(
            reverse("profilechangerequest-approve", args=[change.pk]),
            {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("your own record", response.data["detail"])
        change.refresh_from_db()
        self.assertEqual(change.state, ProfileChangeRequest.PENDING)

    def test_an_employee_sees_only_their_own_change_requests(self):
        ProfileChangeRequest.objects.create(employee=self.bob, field="last_name",
                                            new_value="Rao-Smith")
        mine = ProfileChangeRequest.objects.create(
            employee=self.alice, field="last_name", new_value="Kaur-Singh")

        self.client.force_authenticate(user=self.employee)
        rows = self.client.get(reverse("profilechangerequest-list")).data["results"]
        self.assertEqual([r["id"] for r in rows], [mine.pk])

    def test_raising_the_same_field_twice_replaces_the_open_request(self):
        self.client.force_authenticate(user=self.employee)
        for value in ("Kaur-Singh", "Kaur-Sandhu"):
            self.client.post(reverse("my-profile-request"),
                             {"field": "last_name", "new_value": value},
                             format="json")
        pending = ProfileChangeRequest.objects.filter(
            employee=self.alice, state=ProfileChangeRequest.PENDING)
        self.assertEqual(pending.count(), 1)
        self.assertEqual(pending.get().new_value, "Kaur-Sandhu")


class PasswordChangeTests(SecurityFixture):

    def test_changing_a_password_needs_the_current_one(self):
        """A borrowed unlocked laptop must not become a permanent takeover."""
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(reverse("my-password"), {
            "current_password": "wrong", "new_password": "brand-new-pw-99",
            "confirm_password": "brand-new-pw-99"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_password("demo1234pw"))

    def test_a_successful_change_ends_every_other_session(self):
        stale = Token.objects.create(user=self.employee)
        SessionActivity.objects.create(token_key=stale.key, user=self.employee)

        self.client.force_authenticate(user=self.employee)
        response = self.client.post(reverse("my-password"), {
            "current_password": "demo1234pw", "new_password": "brand-new-pw-99",
            "confirm_password": "brand-new-pw-99"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.employee.refresh_from_db()
        self.assertTrue(self.employee.check_password("brand-new-pw-99"))
        self.assertFalse(Token.objects.filter(key=stale.key).exists())
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.PASSWORD_CHANGED).exists())

    def test_a_short_password_is_refused(self):
        self.client.force_authenticate(user=self.employee)
        response = self.client.post(reverse("my-password"), {
            "current_password": "demo1234pw", "new_password": "abc",
            "confirm_password": "abc"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ==========================================================================
# Sign-in hardening
# ==========================================================================

class LoginHardeningTests(SecurityFixture):

    def test_repeated_failures_lock_the_account_out(self):
        row = SecuritySetting.load()
        for _ in range(row.max_failed_logins):
            self.client.post(reverse("login"),
                             {"email": "alice@oxp.com", "password": "nope"},
                             format="json")

        response = self.client.post(
            reverse("login"),
            {"email": "alice@oxp.com", "password": "demo1234pw"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Too many failed attempts", response.data["detail"])

    def test_a_wrong_email_and_a_wrong_password_read_the_same(self):
        """Telling an attacker which half they got right halves their work."""
        bad_email = self.client.post(
            reverse("login"), {"email": "nobody@oxp.com", "password": "x"},
            format="json")
        bad_password = self.client.post(
            reverse("login"), {"email": "alice@oxp.com", "password": "x"},
            format="json")
        self.assertEqual(bad_email.status_code, bad_password.status_code)
        self.assertTrue(bad_email.data["detail"].startswith(
            "Invalid email or password."))
        self.assertTrue(bad_password.data["detail"].startswith(
            "Invalid email or password."))

    def test_a_deactivated_account_cannot_sign_in_and_the_attempt_is_recorded(self):
        """
        The refusal must not say *why*. "This account is deactivated" confirms
        the address exists, which is an enumeration oracle; an administrator
        gets the detail through the audit log instead.
        """
        self.employee.is_active = False
        self.employee.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("login"),
            {"email": "alice@oxp.com", "password": "demo1234pw"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(response.data["detail"].startswith(
            "Invalid email or password."))
        self.assertTrue(AuditLog.objects.filter(
            action=AuditLog.SIGN_IN_FAILED,
            summary__contains="deactivated account").exists())

    def test_sign_in_is_refused_from_outside_the_permitted_network(self):
        row = SecuritySetting.load()
        row.enforce_network_policy = True
        row.save()
        NetworkPolicy.objects.create(name="Head office Wi-Fi",
                                     cidr="10.20.0.0/24", is_active=True)

        refused = self.client.post(
            reverse("login"),
            {"email": "alice@oxp.com", "password": "demo1234pw"},
            format="json", REMOTE_ADDR="203.0.113.9")
        self.assertEqual(refused.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Head office Wi-Fi", refused.data["detail"])

        allowed = self.client.post(
            reverse("login"),
            {"email": "alice@oxp.com", "password": "demo1234pw"},
            format="json", REMOTE_ADDR="10.20.0.55")
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)

    def test_a_policy_scoped_to_a_role_leaves_other_roles_alone(self):
        """
        The realistic shape of this rule: pin payroll staff to the office
        because they can move money, and leave everyone else free.
        """
        row = SecuritySetting.load()
        row.enforce_network_policy = True
        row.save()
        NetworkPolicy.objects.create(name="Payroll room", cidr="10.20.0.0/24",
                                     role=self.make_role(Role.ADMIN))

        from_home = self.client.post(
            reverse("login"),
            {"email": "alice@oxp.com", "password": "demo1234pw"},
            format="json", REMOTE_ADDR="203.0.113.9")
        self.assertEqual(from_home.status_code, status.HTTP_200_OK)

        admin_from_home = self.client.post(
            reverse("login"),
            {"email": "admin@oxp.com", "password": "demo1234pw"},
            format="json", REMOTE_ADDR="203.0.113.9")
        self.assertEqual(admin_from_home.status_code, status.HTTP_403_FORBIDDEN)

    def test_a_forwarded_for_header_is_ignored_by_default(self):
        """
        Otherwise anyone claims to be on the office network by setting one
        header. `TRUSTED_PROXY_COUNT` defaults to zero for exactly this reason.
        """
        row = SecuritySetting.load()
        row.enforce_network_policy = True
        row.save()
        NetworkPolicy.objects.create(name="Office", cidr="10.20.0.0/24")

        response = self.client.post(
            reverse("login"),
            {"email": "alice@oxp.com", "password": "demo1234pw"},
            format="json", REMOTE_ADDR="203.0.113.9",
            HTTP_X_FORWARDED_FOR="10.20.0.55")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_every_sign_in_is_recorded(self):
        self.client.post(reverse("login"),
                         {"email": "alice@oxp.com", "password": "demo1234pw"},
                         format="json")
        self.client.post(reverse("login"),
                         {"email": "alice@oxp.com", "password": "nope"},
                         format="json")
        self.assertEqual(LoginAttempt.objects.filter(succeeded=True).count(), 1)
        self.assertEqual(LoginAttempt.objects.filter(succeeded=False).count(), 1)


# ==========================================================================
# Privilege escalation
# ==========================================================================

class EscalationTests(SecurityFixture):

    def test_an_admin_cannot_deactivate_themselves(self):
        self.client.force_authenticate(user=self.admin)
        self.make_user("admin2@oxp.com", Role.ADMIN)   # so it is not the last one
        response = self.client.patch(reverse("user-detail", args=[self.admin.pk]),
                                     {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_the_last_administrator_cannot_be_demoted(self):
        """A system with no administrator cannot be repaired from inside it."""
        other_admin = self.make_user("admin2@oxp.com", Role.ADMIN)
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("user-detail", args=[other_admin.pk]),
            {"role_ids": [self.make_role(Role.EMPLOYEE).pk]}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # self.admin is now the only one left; removing their role must fail,
        # and it has to be another admin trying, since self-edits are barred.
        restored = self.make_user("admin3@oxp.com", Role.ADMIN)
        self.client.force_authenticate(user=restored)
        self.client.patch(reverse("user-detail", args=[self.admin.pk]),
                          {"role_ids": [self.make_role(Role.EMPLOYEE).pk]},
                          format="json")
        self.client.force_authenticate(user=self.admin)
        last = self.client.patch(
            reverse("user-detail", args=[restored.pk]),
            {"role_ids": [self.make_role(Role.EMPLOYEE).pk]}, format="json")
        self.assertEqual(last.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("only active administrator", str(last.data))

    def test_deactivating_a_user_ends_their_live_session(self):
        """
        Without this the account keeps working until its token happens to
        expire — which is exactly the window somebody being walked out uses.
        """
        token = Token.objects.create(user=self.employee)
        SessionActivity.objects.create(token_key=token.key, user=self.employee)

        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse("user-detail", args=[self.employee.pk]),
                                     {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.employee).exists())

    def test_a_role_change_is_written_to_the_audit_log(self):
        self.client.force_authenticate(user=self.admin)
        self.client.patch(
            reverse("user-detail", args=[self.employee.pk]),
            {"role_ids": [self.make_role(Role.HR_MANAGER).pk]}, format="json")
        entry = AuditLog.objects.filter(action=AuditLog.ROLES_CHANGED).first()
        self.assertIsNotNone(entry)
        self.assertIn("HR_MANAGER", entry.summary)

    def test_only_an_admin_reads_the_audit_log(self):
        for user, expected in ((self.employee, status.HTTP_403_FORBIDDEN),
                               (self.hr, status.HTTP_403_FORBIDDEN),
                               (self.admin, status.HTTP_200_OK)):
            with self.subTest(user=user.email):
                self.client.force_authenticate(user=user)
                self.assertEqual(
                    self.client.get(reverse("auditlog-list")).status_code,
                    expected)

    def test_turning_on_network_enforcement_from_an_uncovered_address_is_refused(self):
        """
        The classic self-inflicted outage: switch the allowlist on from an
        address the allowlist does not contain.
        """
        NetworkPolicy.objects.create(name="Office", cidr="10.20.0.0/24")
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(reverse("security-settings"),
                                     {"enforce_network_policy": True},
                                     format="json", REMOTE_ADDR="203.0.113.9")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("locked out", response.data["detail"])
        self.assertFalse(SecuritySetting.load().enforce_network_policy)


# ==========================================================================
# Session lifetime
# ==========================================================================

class SessionLifetimeTests(SecurityFixture):

    def _sign_in(self):
        response = self.client.post(
            reverse("login"),
            {"email": "alice@oxp.com", "password": "demo1234pw"}, format="json")
        return response.data["token"]

    def test_a_token_older_than_its_absolute_lifetime_is_rejected(self):
        key = self._sign_in()
        token = Token.objects.get(key=key)
        token.created = timezone.now() - timedelta(hours=48)
        token.save(update_fields=["created"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(Token.objects.filter(key=key).exists())

    def test_an_idle_token_is_signed_out(self):
        key = self._sign_in()
        SessionActivity.objects.filter(token_key=key).update(
            last_used=timezone.now() - timedelta(hours=20))

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        self.assertEqual(self.client.get(reverse("me")).status_code,
                         status.HTTP_401_UNAUTHORIZED)

    def test_leaving_the_permitted_network_ends_the_session_mid_flight(self):
        """
        Checking the network only at sign-in would make the control a
        formality: authenticate at the office, then use the token anywhere.
        """
        key = self._sign_in()
        row = SecuritySetting.load()
        row.enforce_network_policy = True
        row.save()
        NetworkPolicy.objects.create(name="Office", cidr="10.20.0.0/24")

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {key}")
        self.assertEqual(
            self.client.get(reverse("me"), REMOTE_ADDR="203.0.113.9").status_code,
            status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            self.client.get(reverse("me"), REMOTE_ADDR="10.20.0.7").status_code,
            status.HTTP_200_OK)
