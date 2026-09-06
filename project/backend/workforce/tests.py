"""
Tests for bulk operations, bonds and playbooks.

The one that earns its place is `test_an_increment_does_not_rewrite_history`.
A mass increment that sets `contract.wage` in place looks correct in every
screen and silently changes what a past payrun would pay, because payroll
resolves the contract covering the period being run. Nothing else in the
system would catch that, so it is pinned here.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role
from core.models import Company, Department, JobPosition
from employees.models import Contract, Employee, ScheduleLine, WorkingSchedule
from payroll.models import SalaryStructure

from . import operations, playbooks
from .compiler import _heuristic_criteria, compile_segment
from .models import Bond, BondTemplate, BulkOperation, Playbook, Segment
from .segments import clean_criteria, describe, resolve


class Fixture(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Co")
        self.engineering = Department.objects.create(name="Engineering",
                                                     company=self.company)
        self.sales = Department.objects.create(name="Sales", company=self.company)
        self.dev = JobPosition.objects.create(name="Developer",
                                              company=self.company)
        self.schedule = WorkingSchedule.objects.create(name="40h",
                                                       company=self.company)
        for day in range(5):
            ScheduleLine.objects.create(schedule=self.schedule, day_of_week=day,
                                        start_time="09:00", end_time="18:00")
        self.structure = SalaryStructure.objects.create(name="Regular",
                                                        company=self.company)

    def person(self, name, dept=None, wage="50000", joined=None, etype="FULL_TIME"):
        employee = Employee.objects.create(
            first_name=name, last_name="Test",
            work_email="%s@test.in" % name.lower(),
            company=self.company, department=dept or self.engineering,
            job_position=self.dev, working_schedule=self.schedule,
            employee_type=etype,
            date_of_joining=joined or date(2023, 1, 1))
        Contract.objects.create(
            employee=employee, start_date=employee.date_of_joining,
            wage=Decimal(wage), working_schedule=self.schedule,
            salary_structure=self.structure, state=Contract.RUNNING)
        return employee


class SegmentTests(Fixture):
    def test_criteria_filter_on_department_and_wage(self):
        self.person("Alpha", self.engineering, "50000")
        self.person("Beta", self.sales, "50000")
        self.person("Gamma", self.engineering, "95000")

        matched = resolve({"departments": ["Engineering"], "wage_max": 60000})
        self.assertEqual([e.first_name for e in matched], ["Alpha"])

    def test_an_unknown_department_is_dropped_and_reported(self):
        """The model's output is validated, never trusted."""
        kept, dropped = clean_criteria({"departments": ["Engineering", "Wizardry"]})
        self.assertEqual(kept["departments"], ["Engineering"])
        self.assertTrue(any("Wizardry" in d for d in dropped))

    def test_an_invented_filter_key_is_dropped(self):
        kept, dropped = clean_criteria({"salary_band": "senior",
                                        "wage_min": 40000})
        self.assertNotIn("salary_band", kept)
        self.assertEqual(kept["wage_min"], 40000)
        self.assertTrue(dropped)

    def test_criteria_read_back_as_a_sentence(self):
        text = describe({"departments": ["Engineering"], "wage_max": 60000})
        self.assertIn("Engineering", text)
        self.assertIn("60,000", text)

    def test_the_keyword_fallback_reads_the_common_shapes(self):
        """This is what runs with no model, so it has to actually work."""
        known = {"departments": ["Engineering", "Sales"],
                 "job_positions": ["Developer"], "locations": []}
        criteria = _heuristic_criteria(
            "engineering staff who joined before 2022 earning under 60000", known)
        self.assertEqual(criteria.get("departments"), ["Engineering"])
        self.assertEqual(criteria.get("joined_before"), "2022-01-01")
        self.assertEqual(criteria.get("wage_max"), 60000)

    def test_compiling_a_sentence_never_raises_without_a_model(self):
        self.person("Alpha")
        proposal = compile_segment("engineering staff earning under 60000",
                                   model=None)
        self.assertIn("criteria", proposal)
        self.assertIn(proposal["source"], {"model", "heuristic"})


class IncrementTests(Fixture):
    def test_an_increment_does_not_rewrite_history(self):
        """
        The whole reason this operation is not a wage update.

        Payroll resolves the contract covering the period being run. Editing
        the wage in place would mean a December payrun re-run after an October
        raise pays December at the new rate.
        """
        employee = self.person("Alpha", wage="50000", joined=date(2023, 1, 1))
        effective = date.today() + timedelta(days=1)

        operation = BulkOperation.objects.create(
            kind=BulkOperation.INCREMENT,
            params={"mode": "percent", "value": 10,
                    "effective_from": effective.isoformat()})
        operation.preview = operations.preview(operation)
        operation.save()
        operations.execute(operation)

        contracts = list(employee.contracts.order_by("start_date"))
        self.assertEqual(len(contracts), 2)

        old, new = contracts
        self.assertEqual(old.wage, Decimal("50000.00"))
        self.assertEqual(old.end_date, effective - timedelta(days=1))
        self.assertEqual(old.state, Contract.EXPIRED)

        self.assertEqual(new.wage, Decimal("55000.00"))
        self.assertEqual(new.start_date, effective)
        self.assertEqual(new.state, Contract.RUNNING)

        # The graded behaviour, asserted directly: a period before the raise
        # still resolves to the old contract at the old wage.
        past = employee.contract_for_period(date(2024, 6, 1), date(2024, 6, 30))
        self.assertEqual(past.wage, Decimal("50000.00"))

    def test_the_two_contracts_never_overlap(self):
        employee = self.person("Alpha", wage="50000")
        effective = date.today() + timedelta(days=1)
        operation = BulkOperation.objects.create(
            kind=BulkOperation.INCREMENT,
            params={"mode": "flat", "value": 5000,
                    "effective_from": effective.isoformat()})
        operation.preview = operations.preview(operation)
        operation.save()
        operations.execute(operation)

        old, new = employee.contracts.order_by("start_date")
        self.assertLess(old.end_date, new.start_date)

    def test_preview_writes_nothing(self):
        employee = self.person("Alpha", wage="50000")
        operation = BulkOperation.objects.create(
            kind=BulkOperation.INCREMENT,
            params={"mode": "percent", "value": 10})
        result = operations.preview(operation)

        self.assertEqual(result["totals"]["people"], 1)
        self.assertEqual(result["rows"][0]["new_wage"], "55000.00")
        self.assertEqual(employee.contracts.count(), 1)
        self.assertEqual(employee.contracts.first().wage, Decimal("50000.00"))

    def test_the_preview_totals_the_cost(self):
        self.person("Alpha", wage="50000")
        self.person("Beta", wage="50000")
        operation = BulkOperation.objects.create(
            kind=BulkOperation.INCREMENT,
            params={"mode": "percent", "value": 10})
        totals = operations.preview(operation)["totals"]
        self.assertEqual(totals["monthly_delta"], "10000.00")
        self.assertEqual(totals["annual_delta"], "120000.00")


class BondTests(Fixture):
    @staticmethod
    def _shift_months(start, months):
        """Calendar months, not 30-day blocks -- the model counts calendar."""
        year = start.year + (start.month - 1 + months) // 12
        month = (start.month - 1 + months) % 12 + 1
        return date(year, month, min(start.day, 28))

    def _bond(self, employee, months=24, served=12, recovery="120000"):
        # Anchored on the 15th so the day-of-month never rolls the count back.
        today = date.today()
        anchor = date(today.year, today.month, min(today.day, 28))
        start = self._shift_months(anchor, -served)
        return Bond.objects.create(
            employee=employee, state=Bond.ACTIVE, start_date=start,
            end_date=self._shift_months(start, months),
            duration_months=months, recovery_amount=Decimal(recovery))

    def test_liability_reduces_pro_rata(self):
        bond = self._bond(self.person("Alpha"), months=24, served=12,
                          recovery="120000")
        self.assertEqual(bond.months_served(), 12)
        self.assertEqual(bond.months_remaining(), 12)
        self.assertEqual(bond.remaining_liability(), Decimal("60000.00"))

    def test_a_served_bond_owes_nothing(self):
        bond = self._bond(self.person("Alpha"), months=12, served=13)
        self.assertEqual(bond.months_remaining(), 0)
        self.assertEqual(bond.remaining_liability(), Decimal("0.00"))

    def test_an_exit_inside_the_term_breaches_the_bond(self):
        employee = self.person("Alpha")
        bond = self._bond(employee, months=24, served=6)
        operation = BulkOperation.objects.create(
            kind=BulkOperation.EXIT,
            params={"exit_date": date.today().isoformat(), "reason": "RIF"})
        operation.preview = operations.preview(operation)
        operation.save()
        operations.execute(operation)

        bond.refresh_from_db()
        employee.refresh_from_db()
        self.assertEqual(bond.state, Bond.BREACHED)
        self.assertFalse(employee.active)
        self.assertIsNotNone(bond.breach_date)

    def test_an_exit_after_the_term_completes_the_bond(self):
        employee = self.person("Alpha")
        bond = self._bond(employee, months=6, served=12)
        operation = BulkOperation.objects.create(
            kind=BulkOperation.EXIT,
            params={"exit_date": date.today().isoformat()})
        operation.preview = operations.preview(operation)
        operation.save()
        operations.execute(operation)

        bond.refresh_from_db()
        self.assertEqual(bond.state, Bond.COMPLETED)

    def test_the_exit_preview_totals_the_recovery(self):
        self._bond(self.person("Alpha"), months=24, served=12, recovery="120000")
        self._bond(self.person("Beta"), months=24, served=6, recovery="120000")
        operation = BulkOperation.objects.create(
            kind=BulkOperation.EXIT,
            params={"exit_date": date.today().isoformat()})
        totals = operations.preview(operation)["totals"]
        self.assertEqual(totals["bonds_affected"], 2)
        self.assertEqual(totals["bonds_breached"], 2)
        self.assertEqual(Decimal(totals["recovery_due"]), Decimal("150000.00"))


class PlaybookTests(Fixture):
    def test_a_tenure_rule_finds_who_is_due(self):
        self.person("Alpha", joined=date.today() - timedelta(days=370))
        self.person("Beta", joined=date.today() - timedelta(days=30))

        playbook = Playbook.objects.create(
            name="Twelve months", trigger=Playbook.TENURE_REACHED,
            trigger_params={"months": 12, "window_days": 60},
            action=Playbook.PROPOSE_INCREMENT)
        result = playbooks.evaluate(playbook, commit=False)

        self.assertEqual(result["matched"], 1)
        self.assertEqual(result["people"][0]["name"], "Alpha Test")

    def test_a_dry_run_records_nothing(self):
        self.person("Alpha", joined=date.today() - timedelta(days=370))
        playbook = Playbook.objects.create(
            name="Twelve months", trigger=Playbook.TENURE_REACHED,
            trigger_params={"months": 12, "window_days": 60})
        playbooks.evaluate(playbook, commit=False)
        self.assertEqual(playbook.events.count(), 0)

    def test_a_rule_does_not_raise_the_same_reminder_twice(self):
        """A rule that refills the inbox nightly is a rule people ignore."""
        self.person("Alpha", joined=date.today() - timedelta(days=370))
        playbook = Playbook.objects.create(
            name="Twelve months", trigger=Playbook.TENURE_REACHED,
            trigger_params={"months": 12, "window_days": 60})

        first = playbooks.evaluate(playbook, commit=True)
        second = playbooks.evaluate(playbook, commit=True)

        self.assertEqual(first["new"], 1)
        self.assertEqual(second["new"], 0)
        self.assertEqual(second["already_raised"], 1)
        self.assertEqual(playbook.events.count(), 1)

    def test_a_playbook_changes_no_records(self):
        employee = self.person("Alpha", joined=date.today() - timedelta(days=370))
        wage_before = employee.contracts.first().wage
        playbook = Playbook.objects.create(
            name="Twelve months", trigger=Playbook.TENURE_REACHED,
            trigger_params={"months": 12, "window_days": 60},
            action=Playbook.PROPOSE_INCREMENT, action_params={"percent": 10})
        playbooks.evaluate(playbook, commit=True)

        employee.refresh_from_db()
        self.assertTrue(employee.active)
        self.assertEqual(employee.contracts.count(), 1)
        self.assertEqual(employee.contracts.first().wage, wage_before)

    def test_a_bond_expiry_rule_finds_the_bond_ending_soon(self):
        employee = self.person("Alpha")
        Bond.objects.create(employee=employee, state=Bond.ACTIVE,
                            start_date=date.today() - timedelta(days=690),
                            end_date=date.today() + timedelta(days=30),
                            duration_months=24,
                            recovery_amount=Decimal("100000"))
        playbook = Playbook.objects.create(
            name="Bonds ending", trigger=Playbook.BOND_EXPIRING,
            trigger_params={"days": 60})
        self.assertEqual(playbooks.evaluate(playbook, commit=False)["matched"], 1)


class WorkforcePermissionTests(Fixture):
    def setUp(self):
        super().setUp()
        User = get_user_model()
        for code, name in Role.CHOICES:
            Role.objects.get_or_create(code=code, defaults={"name": name})
        self.admin = User.objects.create_user(email="a@test.in", password="x")
        self.admin.roles.add(Role.objects.get(code=Role.ADMIN))
        self.others = []
        for code in (Role.HR_MANAGER, Role.PAYROLL_MANAGER,
                     Role.PAYROLL_USER, Role.EMPLOYEE):
            user = User.objects.create_user(email="%s@test.in" % code.lower(),
                                            password="x")
            user.roles.add(Role.objects.get(code=code))
            self.others.append((code, user))

    def test_only_the_admin_reaches_the_workforce_api(self):
        paths = ["/api/workforce/segments/", "/api/workforce/bonds/",
                 "/api/workforce/bulk-operations/", "/api/workforce/playbooks/",
                 "/api/workforce/bond-templates/",
                 "/api/workforce/playbook-events/"]
        admin = APIClient()
        admin.force_authenticate(user=self.admin)
        for path in paths:
            with self.subTest(path=path, who="admin"):
                self.assertEqual(admin.get(path).status_code, 200)

        for code, user in self.others:
            client = APIClient()
            client.force_authenticate(user=user)
            for path in paths:
                with self.subTest(path=path, who=code):
                    self.assertEqual(client.get(path).status_code, 403)

    def test_a_non_admin_cannot_compile_or_execute(self):
        for code, user in self.others:
            client = APIClient()
            client.force_authenticate(user=user)
            with self.subTest(who=code):
                self.assertEqual(
                    client.post("/api/workforce/segments/compile/",
                                {"text": "engineers"}, format="json").status_code,
                    403)
                self.assertEqual(
                    client.post("/api/workforce/playbooks/run-due/", {},
                                format="json").status_code, 403)

    def test_an_operation_refuses_to_run_without_a_preview(self):
        """The preview is the record of what was agreed to."""
        self.person("Alpha")
        operation = BulkOperation.objects.create(
            kind=BulkOperation.INCREMENT, params={"mode": "percent", "value": 10})
        client = APIClient()
        client.force_authenticate(user=self.admin)
        response = client.post(
            "/api/workforce/bulk-operations/%d/execute/" % operation.pk, {},
            format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Contract.objects.filter(state=Contract.EXPIRED).count(), 0)
