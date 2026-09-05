"""
Tests for the import pipeline.

Weighted towards the two things that fail silently rather than loudly: header
detection, where taking the wrong row puts somebody's salary in the PAN field
and nothing complains; and the reconciler's overrule path, which is the only
thing standing between a confident wrong answer from a 7B model and a corrupted
roster.

Nothing here needs the local model. The ensemble is tested with the model voter
absent and with a stubbed one, because a test that only passes when a GPU is
present is a test that stops running.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import Role
from core.models import Company, Department, JobPosition, WorkLocation
from employees.models import Contract, Employee, ScheduleLine, WorkingSchedule
from payroll.models import SalaryStructure

from .mapper import build_plan, reconcile_column
from .profiler import profile_column, profile_table, strip_money
from .readers import ParsedTable, detect_header, read_table, sniff_delimiter
from .schema import match_header, normalise
from .transforms import apply_chain, suggest_transforms
from .validators import validate_rows

MESSY = b"""Brightloom Textiles Pvt Ltd - Employee Master,,,,
Updated till 31 Aug 2026,,,,
,,,,
Emp Naam,Dept.,DOJ,Sal (pm),Email ID
rajesh kumar,Engg,15-03-2021,"Rs 45,000",rajesh@b.in
PRIYA NAIR,Engg,02/07/2019,"72,000",priya@b.in
Anil Deshpande,Sls,2020-11-30,38500/-,anil@b.in
TOTAL,,,155500,
"""


class ReaderTests(TestCase):
    def test_header_is_found_below_junk_rows(self):
        """The failure this prevents is silent: row 0 is a company name."""
        table = read_table(MESSY, "roster.csv")
        self.assertEqual(table.header_row_index, 3)
        self.assertEqual(table.junk_rows_above, 3)
        self.assertEqual(table.headers[0], "Emp Naam")
        self.assertEqual(table.headers[3], "Sal (pm)")

    def test_trailing_total_row_is_dropped(self):
        table = read_table(MESSY, "roster.csv")
        self.assertEqual(len(table.rows), 3)
        self.assertNotIn("TOTAL", [r[0] for r in table.rows])
        self.assertTrue(any("total" in n.lower() for n in table.notes))

    def test_what_was_skipped_is_reported(self):
        table = read_table(MESSY, "roster.csv")
        self.assertTrue(any("line 4" in n for n in table.notes))

    def test_a_header_on_the_first_row_is_left_alone(self):
        clean = b"Name,Email\nA B,a@b.in\nC D,c@d.in\n"
        table = read_table(clean, "clean.csv")
        self.assertEqual(table.header_row_index, 0)
        self.assertEqual(table.junk_rows_above, 0)

    def test_delimiter_is_chosen_by_consistency(self):
        self.assertEqual(sniff_delimiter("a;b;c\n1;2;3\n4;5;6"), ";")
        self.assertEqual(sniff_delimiter("a,b,c\n1,2,3"), ",")

    def test_a_data_row_never_wins_header_scoring(self):
        rows = [["Name", "Email", "Joined"],
                ["Rajesh Kumar", "r@b.in", "15-03-2021"],
                ["Priya Nair", "p@b.in", "02/07/2019"]]
        index, _ = detect_header(rows)
        self.assertEqual(index, 0)

    def test_encoding_falls_back_without_raising(self):
        table = read_table("Name,City\nJose,Curacao\n".encode("cp1252"), "x.csv")
        self.assertEqual(table.headers, ["Name", "City"])


class ProfilerTests(TestCase):
    def test_currency_is_stripped_three_ways(self):
        self.assertEqual(strip_money("Rs 45,000"), "45000")
        self.assertEqual(strip_money("38500/-"), "38500")
        self.assertEqual(strip_money("1,04,000"), "104000")
        self.assertIsNone(strip_money("not a number"))

    def test_an_annual_salary_column_is_flagged(self):
        """The whole reason the profiler exists: 12x too large is invisible."""
        profile = profile_column(0, "ANNUAL_CTC",
                                 ["1080000", "1560000", "912000", "2160000"])
        self.assertEqual(profile["best_kind"], "money")
        self.assertIn("looks_annual", profile["flags"])

    def test_a_monthly_salary_column_is_not_flagged(self):
        profile = profile_column(0, "Sal (pm)",
                                 ["Rs 45,000", "72,000", "38500/-", "65,000"])
        self.assertEqual(profile["best_kind"], "money")
        self.assertNotIn("looks_annual", profile["flags"])

    def test_underscored_header_still_reads_as_money(self):
        """ANNUAL_CTC lowercases to annual_ctc and \\b finds no boundary."""
        profile = profile_column(0, "ANNUAL_CTC", ["1080000", "912000"])
        self.assertEqual(profile["best_kind"], "money")

    def test_mixed_date_formats_are_detected_and_flagged(self):
        profile = profile_column(0, "DOJ",
                                 ["15-03-2021", "02/07/2019", "2020-11-30"])
        self.assertEqual(profile["best_kind"], "date")
        self.assertIn("mixed_date_formats", profile["flags"])

    def test_a_mostly_empty_column_is_text_not_a_name(self):
        """Four filled cells that look like names do not make a name column."""
        values = ["Good one", "On notice"] + [""] * 20
        profile = profile_column(0, "Remarks", values)
        self.assertEqual(profile["best_kind"], "text")

    def test_a_bare_integer_salary_is_not_read_as_a_date(self):
        """
        45000 is a plausible monthly wage and also the Excel serial for a date
        in 2023. Counting serials as confidently as a parsed date made every
        such salary column read as a date, and since a date may be a contract
        end, the column then mapped to one.

        Known limit, deliberately not fixed: a column of raw Excel serials
        under a date header still reads as integer. It only arises in a CSV
        exported from Excel without formatting, since openpyxl hands us real
        dates as ISO strings, and the operator can remap the column in one
        click. Reading a salary as a date is the damaging direction.
        """
        profile = profile_column(0, "Salary", ["45000", "52000", "38000"])
        self.assertEqual(profile["best_kind"], "money")

    def test_a_long_account_number_stays_an_integer(self):
        profile = profile_column(0, "A/C No",
                                 ["367604506824", "949453045647", "401297682956"])
        self.assertEqual(profile["best_kind"], "integer")

    def test_identifier_formats_are_recognised(self):
        self.assertEqual(
            profile_column(0, "IFSC", ["HDFC0000234", "ICIC0001177"])["best_kind"],
            "ifsc")
        self.assertEqual(
            profile_column(0, "PAN", ["ABCDE1234F", "GVERF2288H"])["best_kind"],
            "pan")
        self.assertEqual(
            profile_column(0, "Mob", ["9940951293", "+91 7225967148"])["best_kind"],
            "phone")

    def test_evidence_is_short_and_ascii(self):
        profile = profile_column(0, "Sal (pm)", ["Rs 45,000", "72,000"])
        self.assertLessEqual(len(profile["evidence"]), 150)
        self.assertTrue(all(ord(c) < 128 for c in profile["evidence"]))


class MatcherTests(TestCase):
    def test_indian_hr_abbreviations_resolve(self):
        for header, expected in [("DOJ", "date_of_joining"),
                                 ("Emp Naam", "full_name"),
                                 ("A/C No", "bank_account_number"),
                                 ("Sal (pm)", "wage"),
                                 ("Mob No", "work_phone"),
                                 ("Dept.", "department"),
                                 ("Designation", "job_position")]:
            with self.subTest(header=header):
                self.assertEqual(match_header(header)[0]["field"], expected)

    def test_normalise_expands_and_splits(self):
        self.assertEqual(normalise("ANNUAL_CTC"), "annual ctc")
        self.assertEqual(normalise("Sal (pm)"), "salary")
        self.assertEqual(normalise("empName"), "employee name")
        # "A/C" splits into two tokens rather than expanding to "account", and
        # that is fine because the synonym list is normalised through the same
        # function -- both sides become "a c number" and match. The property
        # worth pinning is the match, not the intermediate string.
        self.assertEqual(normalise("A/C No."), normalise("a/c no"))

    def test_a_label_match_is_demoted_when_the_data_contradicts_it(self):
        email = profile_column(0, "Joining", ["a@b.in", "c@d.in", "e@f.in"])
        top = match_header("Joining", email)[0]
        self.assertLess(top["confidence"], 0.5)


class _StubModel:
    """Stands in for the local model so the ensemble is testable without a GPU."""

    def __init__(self, mappings):
        self.model = "stub"
        self._mappings = mappings

    def generate_json(self, prompt, **kwargs):
        return {"mappings": self._mappings}, 10


class EnsembleTests(TestCase):
    def _table(self):
        table = read_table(MESSY, "roster.csv")
        return table, profile_table(table)

    def test_a_plan_is_usable_with_no_model_at_all(self):
        table, profiles = self._table()
        plan = build_plan(table, profiles, model=None)
        self.assertFalse(plan["llm"]["used"])
        self.assertTrue(plan["llm"]["fallback_reason"])
        mapped = {c["field"] for c in plan["columns"] if c["field"]}
        self.assertIn("wage", mapped)
        self.assertIn("date_of_joining", mapped)
        self.assertIn("work_email", mapped)
        self.assertEqual(plan["missing_required"], [])

    def test_hard_evidence_overrules_the_model(self):
        """A column of emails is not a joining date, however confident it is."""
        emails = profile_column(0, "Contact", ["a@b.in", "c@d.in", "e@f.in"])
        entry = reconcile_column(emails, {
            "voter": "model", "field": "date_of_joining",
            "confidence": 0.99, "reason": "looks like a date"})
        model_vote = next(v for v in entry["votes"] if v["voter"] == "model")
        self.assertEqual(model_vote["status"], "overruled")
        self.assertNotEqual(entry["field"], "date_of_joining")

    def test_the_losing_votes_are_kept(self):
        table, profiles = self._table()
        plan = build_plan(table, profiles, model=None)
        self.assertTrue(any(c["votes"] for c in plan["columns"]))
        for column in plan["columns"]:
            for vote in column["votes"]:
                self.assertIn(vote["status"],
                              {"agreed", "outvoted", "overruled", "considered"})

    def test_agreement_between_voters_raises_confidence(self):
        """A header no dictionary knows: the model is the only voter until
        a second one agrees with it."""
        # "Particulars" is in no synonym list, so only the shape voter has an
        # opinion until the model arrives and agrees with it.
        opaque = profile_column(0, "Particulars",
                                ["Rs 45,000", "72,000", "38500/-"])
        alone = reconcile_column(opaque, None)
        together = reconcile_column(opaque, {
            "voter": "model", "field": "wage", "confidence": 0.8,
            "reason": "monthly salary"})
        self.assertEqual(together["field"], "wage")
        self.assertEqual(together["verdict"], "consensus")
        self.assertGreater(together["confidence"], alone["confidence"])

    def test_two_columns_cannot_claim_the_same_field(self):
        table = ParsedTable(
            headers=["Salary", "Wage"],
            rows=[["45000", "50000"], ["52000", "61000"], ["38000", "44000"]])
        plan = build_plan(table, profile_table(table), model=None)
        claimed = [c["field"] for c in plan["columns"] if c["field"]]
        self.assertEqual(len(claimed), len(set(claimed)))
        self.assertTrue(any(c["verdict"] == "conflict" for c in plan["columns"]))

    def test_an_invented_field_from_the_model_is_discarded(self):
        table, profiles = self._table()
        stub = _StubModel([{"column": 1, "field": "salary_band",
                            "confidence": 0.99, "reason": "invented"}])
        plan = build_plan(table, profiles, model=stub)
        self.assertNotIn("salary_band",
                         {c["field"] for c in plan["columns"]})

    def test_full_name_satisfies_the_first_name_requirement(self):
        table, profiles = self._table()
        plan = build_plan(table, profiles, model=None)
        mapped = {c["field"] for c in plan["columns"] if c["field"]}
        self.assertIn("full_name", mapped)
        self.assertNotIn("first_name", plan["missing_required"])


class TransformTests(TestCase):
    def test_an_annual_column_is_proposed_for_scaling(self):
        profile = profile_column(0, "ANNUAL_CTC", ["1080000", "1560000", "912000"])
        chain = suggest_transforms("wage", profile)
        self.assertIn("scale", [t["id"] for t in chain])
        value, ok, _ = apply_chain("1080000", chain)
        self.assertTrue(ok)
        self.assertEqual(value, Decimal("90000.00"))

    def test_a_monthly_column_is_not_scaled(self):
        profile = profile_column(0, "Sal (pm)", ["Rs 45,000", "72,000", "38500/-"])
        chain = suggest_transforms("wage", profile)
        self.assertNotIn("scale", [t["id"] for t in chain])
        value, ok, _ = apply_chain("Rs 45,000", chain)
        self.assertTrue(ok)
        self.assertEqual(value, Decimal("45000"))

    def test_mixed_date_formats_all_parse(self):
        profile = profile_column(0, "DOJ",
                                 ["15-03-2021", "02/07/2019", "2020-11-30"])
        chain = suggest_transforms("date_of_joining", profile)
        for raw, expected in [("15-03-2021", date(2021, 3, 15)),
                              ("02/07/2019", date(2019, 7, 2)),
                              ("2020-11-30", date(2020, 11, 30))]:
            value, ok, _ = apply_chain(raw, chain)
            self.assertTrue(ok, raw)
            self.assertEqual(value, expected)

    def test_a_name_is_split_and_recased(self):
        profile = profile_column(0, "Emp Naam",
                                 ["rajesh kumar", "PRIYA NAIR", "Anil Deshpande"])
        chain = suggest_transforms("full_name", profile)
        value, ok, _ = apply_chain("  rajesh kumar", chain)
        self.assertTrue(ok)
        self.assertEqual(value, {"first_name": "Rajesh", "last_name": "Kumar"})

    def test_a_phone_loses_its_country_code(self):
        profile = profile_column(0, "Mob", ["+91 9940951293", "7225967148"])
        chain = suggest_transforms("work_phone", profile)
        self.assertEqual(apply_chain("+91 9940951293", chain)[0], "9940951293")

    def test_a_step_that_cannot_run_stops_the_chain_and_says_why(self):
        profile = profile_column(0, "Sal", ["45000", "52000"])
        chain = suggest_transforms("wage", profile)
        value, ok, notes = apply_chain("not a number", chain)
        self.assertFalse(ok)
        self.assertTrue(notes)


class ValidatorTests(TestCase):
    def test_a_row_with_no_email_is_blocked(self):
        issues = validate_rows([{"first_name": "A", "wage": 5000,
                                 "date_of_joining": date(2020, 1, 1)}])
        codes = {(i["code"], i["severity"]) for i in issues}
        self.assertIn(("MISSING_REQUIRED", "error"), codes)

    def test_a_duplicate_inside_the_file_is_found(self):
        row = {"first_name": "A", "work_email": "a@b.in", "wage": 5000,
               "date_of_joining": date(2020, 1, 1)}
        issues = validate_rows([dict(row), dict(row)])
        self.assertIn("DUPLICATE_IN_FILE", {i["code"] for i in issues})

    def test_an_email_already_on_the_roster_is_found(self):
        issues = validate_rows(
            [{"first_name": "A", "work_email": "a@b.in", "wage": 5000,
              "date_of_joining": date(2020, 1, 1)}],
            existing_emails={"a@b.in"})
        self.assertIn("DUPLICATE_EMAIL", {i["code"] for i in issues})

    def test_a_missing_bank_account_warns_but_does_not_block(self):
        issues = validate_rows([{"first_name": "A", "work_email": "a@b.in",
                                 "wage": 5000,
                                 "date_of_joining": date(2020, 1, 1)}])
        bank = [i for i in issues if i["code"] == "NO_BANK_ACCOUNT"]
        self.assertEqual(len(bank), 1)
        self.assertEqual(bank[0]["severity"], "warning")

    def test_an_unscaled_annual_wage_is_questioned(self):
        issues = validate_rows([{"first_name": "A", "work_email": "a@b.in",
                                 "wage": 1080000,
                                 "date_of_joining": date(2020, 1, 1)}])
        self.assertIn("IMPLAUSIBLE_WAGE", {i["code"] for i in issues})


class ImportApiTests(TestCase):
    """The pipeline through HTTP, and who is allowed to run it."""

    def setUp(self):
        User = get_user_model()
        self.company = Company.objects.create(name="Test Co")
        schedule = WorkingSchedule.objects.create(name="40h", company=self.company)
        for day in range(5):
            ScheduleLine.objects.create(schedule=schedule, day_of_week=day,
                                        start_time="09:00", end_time="18:00",
                                        break_minutes=60)
        SalaryStructure.objects.create(name="Regular", company=self.company)

        for code, name in Role.CHOICES:
            Role.objects.get_or_create(code=code, defaults={"name": name})

        self.admin = User.objects.create_user(email="a@test.in", password="x")
        self.admin.roles.add(Role.objects.get(code=Role.ADMIN))
        self.hr = User.objects.create_user(email="h@test.in", password="x")
        self.hr.roles.add(Role.objects.get(code=Role.HR_MANAGER))

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_only_the_admin_may_reach_the_import(self):
        for path in ["/api/intel/health/", "/api/intel/sources/",
                     "/api/intel/runs/"]:
            with self.subTest(path=path):
                self.assertEqual(self._client(self.admin).get(path).status_code, 200)
                self.assertEqual(self._client(self.hr).get(path).status_code, 403)

    def test_a_roster_imports_end_to_end(self):
        import base64

        client = self._client(self.admin)
        source = client.post("/api/intel/sources/", {
            "filename": "roster.csv",
            "content_b64": base64.b64encode(MESSY).decode(),
        }, format="json")
        self.assertEqual(source.status_code, 201)
        self.assertEqual(source.data["junk_rows_above"], 3)

        run = client.post("/api/intel/runs/", {"source": source.data["id"]},
                          format="json")
        self.assertEqual(run.status_code, 201)
        run_id = run.data["id"]

        # Consume the stream so the plan is stored, then import from it.
        list(client.get("/api/intel/runs/%d/analyze/" % run_id).streaming_content)

        preview = client.post("/api/intel/runs/%d/preview/" % run_id, {},
                              format="json")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["counts"]["rows"], 3)

        before = Employee.objects.count()
        result = client.post("/api/intel/runs/%d/commit/" % run_id, {},
                             format="json")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Employee.objects.count(), before + 3)

        rajesh = Employee.objects.get(work_email="rajesh@b.in")
        self.assertEqual(rajesh.first_name, "Rajesh")
        self.assertEqual(rajesh.last_name, "Kumar")
        self.assertEqual(rajesh.date_of_joining, date(2021, 3, 15))
        self.assertEqual(rajesh.department.name, "Engineering")

        contract = rajesh.contracts.first()
        self.assertIsNotNone(contract)
        self.assertEqual(contract.wage, Decimal("45000.00"))
        self.assertEqual(contract.state, Contract.RUNNING)

    def test_a_preview_writes_nothing(self):
        import base64

        client = self._client(self.admin)
        source = client.post("/api/intel/sources/", {
            "filename": "roster.csv",
            "content_b64": base64.b64encode(MESSY).decode(),
        }, format="json")
        run = client.post("/api/intel/runs/", {"source": source.data["id"]},
                          format="json")
        list(client.get("/api/intel/runs/%d/analyze/" % run.data["id"])
             .streaming_content)

        before = (Employee.objects.count(), Department.objects.count())
        client.post("/api/intel/runs/%d/preview/" % run.data["id"], {},
                    format="json")
        self.assertEqual(
            (Employee.objects.count(), Department.objects.count()), before)
