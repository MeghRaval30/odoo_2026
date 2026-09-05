"""
Seed representative demo data (T-028, PRD-7.1).

Targets deliberately chosen so the demo script works:
  - 22 employees across 5 departments
  - 2 employees with multiple contracts, proving period-based resolution
  - 2 employees with no bank account, so A/C missing fires on cue
  - 3 months of payroll history for the trend chart
  - mixed leave, both allocation-required and not

A larger roster can be generated on top of that with `--employees N`. The 22
demo people are always seeded first and are never touched, so the demo script
stays true at any headcount; everything above 22 is generated and written with
`bulk_create`.

Usage:  python manage.py seed [--flush] [--employees N]
"""

import random
import time as time_module
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from accounts.security import NetworkPolicy, SecuritySetting
from attendance.models import Attendance
from core.models import Company, Department, Holiday, JobPosition, WorkLocation
from employees.models import Contract, Employee, ScheduleLine, WorkingSchedule
from payroll.models import Payrun, SalaryRule, SalaryStructure
from payroll import engine
from timeoff.models import Allocation, TimeOffRequest, TimeOffType

D = Decimal


class Command(BaseCommand):
    help = "Seed PeoplePay360 with representative demo data"

    def add_arguments(self, parser):
        parser.add_argument("--flush", action="store_true",
                            help="Delete existing data first")
        parser.add_argument("--employees", type=int, default=None, metavar="N",
                            help="Total headcount to seed. The 22-person demo "
                                 "roster is always created first and kept "
                                 "intact; anything above 22 is generated. "
                                 "Default: 22.")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["flush"]:
            self.stdout.write("Flushing existing data...")
            # Payruns first — Payslip.employee is PROTECT, so payslips must be
            # gone (cascaded from Payrun) before employees can be deleted.
            for model in (Payrun, Attendance, TimeOffRequest, Allocation,
                          TimeOffType, Contract, Employee, ScheduleLine,
                          WorkingSchedule, SalaryRule, SalaryStructure,
                          JobPosition, Department, WorkLocation, Holiday,
                          Company):
                model.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

            # Security settings are a single row that nothing above touches,
            # so they survived every reseed. probe_forms.py and smoke_api.py
            # exercise the security screen by flipping them, which left the
            # demo opening on "Sign-in is restricted to 0 permitted networks"
            # and IP-bound sessions -- alarming to read, and the second one
            # signs everybody out the moment the laptop changes network.
            #
            # This command is what "a known demo state" means, so the row and
            # its policies are reset here with it.
            NetworkPolicy.objects.all().delete()
            SecuritySetting.objects.all().delete()
            SecuritySetting.load()          # recreated at model defaults

        random.seed(360)  # reproducible demos

        company = self._company()
        roles = self._roles()
        departments = self._departments(company)
        positions = self._positions(company, departments)
        locations = self._locations(company)
        schedules = self._schedules(company)
        self._holidays(company)
        structures = self._salary_structures(company)
        employees = self._employees(company, departments, positions,
                                    locations, schedules)
        self._contracts(employees, schedules, structures)
        employees += self._generated_roster(
            company, departments, positions, locations, schedules, structures,
            target=opts.get("employees") or len(self.ROSTER))
        self._users(employees, roles)
        self._timeoff(employees)
        self._attendance(employees)
        self._payroll_history(company, structures["regular"], employees)
        self._off_cycle_correction(company, structures["regular"], employees)

        self._summary()

    # ------------------------------------------------------------------ org

    def _company(self):
        c, _ = Company.objects.get_or_create(
            name="OXP Pvt Ltd",
            defaults={"currency": "INR", "timezone": "Asia/Kolkata"})
        self.stdout.write(f"  company: {c.name}")
        return c

    def _roles(self):
        roles = {}
        for code, name in Role.CHOICES:
            roles[code], _ = Role.objects.get_or_create(
                code=code, defaults={"name": name})
        return roles

    def _departments(self, company):
        names = ["Finance", "HR", "Engineering", "Sales", "IT"]
        return {n: Department.objects.get_or_create(
            name=n, company=company)[0] for n in names}

    def _positions(self, company, departments):
        spec = {
            "Payroll Specialist": "Finance", "Accountant": "Finance",
            "HR Officer": "HR", "Recruiter": "HR",
            "Developer": "Engineering", "QA Engineer": "Engineering",
            "Sales Executive": "Sales", "Account Manager": "Sales",
            "System Admin": "IT", "Support Engineer": "IT",
        }
        return {name: JobPosition.objects.get_or_create(
            name=name, company=company,
            defaults={"department": departments[dept]})[0]
            for name, dept in spec.items()}

    def _locations(self, company):
        return [WorkLocation.objects.get_or_create(name=n, company=company)[0]
                for n in ("Mumbai", "Bengaluru", "Remote")]

    # ------------------------------------------------------------- schedules

    def _schedules(self, company):
        specs = {
            "40 Hours / Week": (range(0, 5), time(9, 0), time(18, 0), 60, "FIXED"),
            "Night Shift": (range(0, 5), time(22, 0), time(23, 59), 30, "FIXED"),
            "Retail Weekend": ([4, 5, 6], time(10, 0), time(19, 0), 60, "FIXED"),
            "Flexible Hybrid": (range(0, 5), time(10, 0), time(18, 0), 30, "VARIABLE"),
            "Part-time 20h": (range(0, 4), time(9, 0), time(14, 0), 0, "FIXED"),
        }
        out = {}
        for name, (days, start, end, brk, cal) in specs.items():
            sched, created = WorkingSchedule.objects.get_or_create(
                name=name, company=company, defaults={"calendar_type": cal})
            if created:
                for day in days:
                    ScheduleLine.objects.create(
                        schedule=sched, day_of_week=day, start_time=start,
                        end_time=end, break_minutes=brk)
            out[name] = sched
            self.stdout.write(
                f"  schedule: {name} -> {sched.hours_per_week}h / "
                f"{sched.days_per_week} days (derived)")
        return out

    def _holidays(self, company):
        for name, d in [("Republic Day", date(2026, 1, 26)),
                        ("Holi", date(2026, 3, 4)),
                        ("Independence Day", date(2026, 8, 15)),
                        ("Diwali", date(2026, 11, 8))]:
            Holiday.objects.get_or_create(company=company, date=d,
                                          defaults={"name": name})

    # ---------------------------------------------------------------- salary

    def _salary_structures(self, company):
        regular, created = SalaryStructure.objects.get_or_create(
            code="REGULAR", company=company,
            defaults={"name": "Regular Salary"})
        if created:
            rules = [
                (1, "Basic Salary", "BASIC", "BASIC", "PERCENTAGE", None, D("50"), ""),
                (10, "House Rent Allowance", "HRA", "ALLOWANCE", "PERCENTAGE", None, D("40"), "BASIC"),
                (20, "Standard Allowance", "STD", "ALLOWANCE", "FIXED", D("10000"), None, ""),
                (30, "Performance Bonus", "BONUS", "ALLOWANCE", "FIXED", D("5000"), None, ""),
                (40, "Leave Travel Allowance", "LTA", "ALLOWANCE", "FIXED", D("3000"), None, ""),
                (50, "Fixed Allowance", "FIX", "ALLOWANCE", "FIXED", D("2000"), None, ""),
                # Overtime earned from attendance (D-002)
                (55, "Overtime", "OT", "ALLOWANCE", "FORMULA", None, None, ""),
                (60, "Gross Salary", "GROSS", "GROSS", "FORMULA", None, None, ""),
                # Loss of Pay driven by unpaid approved leave (D-002)
                (65, "Loss of Pay", "LOP", "DEDUCTION", "FORMULA", None, None, ""),
                (70, "Labour Welfare Fund", "LWF", "DEDUCTION", "FIXED", D("20"), None, ""),
                (80, "Provident Fund", "PF", "DEDUCTION", "PERCENTAGE", None, D("12"), "BASIC"),
                (90, "ESIC", "ESIC", "DEDUCTION", "FORMULA", None, None, ""),
                (100, "Professional Tax", "PT", "DEDUCTION", "FIXED", D("200"), None, ""),
                (110, "Net Salary", "NET", "NET", "FORMULA", None, None, ""),
                # Employer contributions — a cost to the company, never a
                # deduction from the employee. Flagged is_employer_cost so the
                # engine keeps them out of gross and net and rolls them into
                # CTC instead.
                (120, "Provident Fund (Employer)", "PF_ER", "DEDUCTION", "PERCENTAGE", None, D("12"), "BASIC"),
                (130, "ESIC (Employer)", "ESIC_ER", "DEDUCTION", "FORMULA", None, None, ""),
            ]
            employer_cost_codes = {"PF_ER", "ESIC_ER"}
            formulas = {
                # Overtime paid at 1.5x the derived hourly rate
                "OT": "(wage / Decimal('173.33')) * overtime_hours * Decimal('1.5')",
                "GROSS": "categories['BASIC'] + categories['ALLOWANCE']",
                # One unpaid leave day costs one day of gross
                "LOP": "(rules['GROSS'] / expected_days) * lop_days if expected_days > 0 else Decimal('0')",
                "ESIC": "rules['GROSS'] * Decimal('0.0075') if rules['GROSS'] <= 21000 else Decimal('0')",
                "NET": "categories['GROSS'] - categories['DEDUCTION']",
                # Employer ESIC is 3.25% on the same ceiling as the employee's
                "ESIC_ER": "rules['GROSS'] * Decimal('0.0325') if rules['GROSS'] <= 21000 else Decimal('0')",
            }
            for seq, name, code, cat, comp, amt, pct, base in rules:
                SalaryRule.objects.create(
                    structure=regular, sequence=seq, name=name, code=code,
                    category=cat, computation=comp, amount=amt, percentage=pct,
                    percentage_base=base, formula=formulas.get(code, ""),
                    is_employer_cost=code in employer_cost_codes)

        intern, created = SalaryStructure.objects.get_or_create(
            code="INTERN", company=company, defaults={"name": "Intern Salary"})
        if created:
            for seq, name, code, cat, comp, amt, pct, base, formula in [
                (1, "Stipend", "BASIC", "BASIC", "PERCENTAGE", None, D("100"), "", ""),
                (60, "Gross Salary", "GROSS", "GROSS", "FORMULA", None, None, "",
                 "categories['BASIC'] + categories['ALLOWANCE']"),
                (100, "Professional Tax", "PT", "DEDUCTION", "FIXED", D("200"), None, "", ""),
                (110, "Net Salary", "NET", "NET", "FORMULA", None, None, "",
                 "categories['GROSS'] - categories['DEDUCTION']"),
            ]:
                SalaryRule.objects.create(
                    structure=intern, sequence=seq, name=name, code=code,
                    category=cat, computation=comp, amount=amt, percentage=pct,
                    percentage_base=base, formula=formula)

        self.stdout.write(f"  structures: Regular ({regular.rule_count} rules), "
                          f"Intern ({intern.rule_count} rules)")
        return {"regular": regular, "intern": intern}

    # ------------------------------------------------------------- employees

    ROSTER = [
        ("Aarav", "Mehta", "Finance", "Payroll Specialist", "FULL_TIME", 85000),
        ("Sara", "Khan", "HR", "HR Officer", "FULL_TIME", 95000),
        ("John", "Dsouza", "Engineering", "Developer", "FULL_TIME", 110000),
        ("Neha", "Patel", "HR", "Recruiter", "FULL_TIME", 72000),
        ("Anita", "Oliver", "Sales", "Sales Executive", "FULL_TIME", 78000),
        ("Audrey", "Peterson", "Sales", "Account Manager", "FULL_TIME", 88000),
        ("Billy", "Kyle", "Engineering", "Developer", "FULL_TIME", 105000),
        ("Eli", "Lambert", "IT", "System Admin", "FULL_TIME", 92000),
        ("Paul", "Williams", "Finance", "Accountant", "FULL_TIME", 76000),
        ("Priya", "Sharma", "Engineering", "QA Engineer", "FULL_TIME", 82000),
        ("Rohan", "Verma", "IT", "Support Engineer", "FULL_TIME", 68000),
        ("Meera", "Iyer", "Finance", "Accountant", "FULL_TIME", 74000),
        ("Karan", "Singh", "Sales", "Sales Executive", "FULL_TIME", 71000),
        ("Divya", "Nair", "HR", "HR Officer", "FULL_TIME", 79000),
        ("Arjun", "Reddy", "Engineering", "Developer", "FULL_TIME", 118000),
        ("Sneha", "Joshi", "Engineering", "QA Engineer", "FULL_TIME", 84000),
        ("Vikram", "Rao", "IT", "System Admin", "FULL_TIME", 96000),
        ("Ananya", "Gupta", "Sales", "Account Manager", "FULL_TIME", 89000),
        ("Rahul", "Kapoor", "Finance", "Payroll Specialist", "FULL_TIME", 81000),
        ("Ishita", "Bose", "Engineering", "Developer", "PART_TIME", 55000),
        ("Dev", "Malhotra", "Engineering", "Developer", "INTERN", 25000),
        ("Tanya", "Shah", "Sales", "Sales Executive", "INTERN", 22000),
    ]

    def _employees(self, company, departments, positions, locations, schedules):
        employees = []
        for i, (first, last, dept, pos, etype, _wage) in enumerate(self.ROSTER):
            schedule = schedules["40 Hours / Week"]
            if etype == "PART_TIME":
                schedule = schedules["Part-time 20h"]
            elif etype == "INTERN":
                schedule = schedules["Flexible Hybrid"]

            # Two employees deliberately have no bank account (PRD-7.1)
            has_bank = i not in (4, 11)

            emp, _ = Employee.objects.get_or_create(
                work_email=f"{first.lower()}@oxp.com",
                defaults={
                    "first_name": first, "last_name": last, "company": company,
                    "department": departments[dept],
                    "job_position": positions[pos],
                    "work_location": random.choice(locations),
                    "working_schedule": schedule,
                    "employee_type": etype,
                    "date_of_joining": date(2025, 1, 1) + timedelta(days=i * 17),
                    "work_phone": f"+91 98{random.randint(10000000, 99999999)}",
                    "bank_account_number": f"5011{random.randint(10**9, 10**10 - 1)}" if has_bank else None,
                    "bank_ifsc": "HDFC0001234" if has_bank else None,
                    "pan_number": f"ABCDE{random.randint(1000, 9999)}F",
                })
            employees.append(emp)

        # Managers
        sara, aarav = employees[1], employees[0]
        for emp in employees:
            if emp.pk != sara.pk:
                emp.manager = sara
                emp.save(update_fields=["manager"])
        departments["Finance"].manager = aarav
        departments["Finance"].save(update_fields=["manager"])

        missing = [e.full_name for e in employees if not e.has_bank_details]
        self.stdout.write(f"  employees: {len(employees)} "
                          f"(no bank account: {', '.join(missing)})")
        return employees

    def _contracts(self, employees, schedules, structures):
        created = 0
        for i, emp in enumerate(employees):
            wage = D(self.ROSTER[i][5])
            structure = (structures["intern"]
                         if emp.employee_type == "INTERN"
                         else structures["regular"])

            schedule = emp.working_schedule or schedules["40 Hours / Week"]
            common = {
                "working_schedule": schedule,
                "salary_structure": structure,
                "department": emp.department,
                "job_position": emp.job_position,
            }

            if i in (0, 2):
                # Two employees carry contract history at a lower wage. The
                # December payrun must resolve the OLD contract and the
                # February payrun the NEW one — this is the demo evidence for
                # graded rule #1.
                Contract.objects.get_or_create(
                    employee=emp, start_date=date(2025, 7, 1),
                    defaults={"end_date": date(2025, 12, 31),
                              "wage": wage - D("7000"),
                              "state": Contract.EXPIRED, **common})
                Contract.objects.get_or_create(
                    employee=emp, start_date=date(2026, 1, 1),
                    defaults={"end_date": None, "wage": wage,
                              "state": Contract.RUNNING, **common})
                created += 2
            else:
                _, made = Contract.objects.get_or_create(
                    employee=emp, start_date=date(2025, 1, 1),
                    defaults={"end_date": None, "wage": wage,
                              "state": Contract.RUNNING, **common})
                created += int(made)
        self.stdout.write(f"  contracts: {created} "
                          f"(2 employees have contract history)")

    # ------------------------------------------------- generated roster (T-089)

    #: Names for the generated roster. Paired with a running index in the work
    #: email, so a collision between two generated people is impossible however
    #: large N gets.
    GEN_FIRST = [
        "Aditya", "Akash", "Ameya", "Ananya", "Anjali", "Ansh", "Arnav",
        "Aryan", "Bhavna", "Chirag", "Deepa", "Dhruv", "Farhan", "Gaurav",
        "Harsha", "Imran", "Ira", "Jatin", "Kavya", "Kabir", "Lakshmi",
        "Manish", "Mitali", "Naveen", "Nikita", "Omkar", "Pallavi", "Pranav",
        "Rachana", "Raghav", "Ritika", "Sahil", "Sanya", "Shreya", "Siddharth",
        "Tarun", "Trisha", "Uday", "Varun", "Yash", "Zoya", "Nandini",
    ]
    GEN_LAST = [
        "Agarwal", "Banerjee", "Chandra", "Chauhan", "Desai", "Dutta", "Ghosh",
        "Hegde", "Jain", "Kulkarni", "Menon", "Mishra", "Naidu", "Pillai",
        "Prasad", "Ranganathan", "Sethi", "Shetty", "Sinha", "Sridhar",
        "Thakur", "Trivedi", "Vaidya", "Venkatesan", "Yadav", "Chopra",
    ]

    #: Position -> (department, base monthly wage). Generated wages jitter
    #: around the base so department totals on the dashboard stay plausible.
    GEN_POSITIONS = [
        ("Developer", "Engineering", 105000),
        ("QA Engineer", "Engineering", 84000),
        ("System Admin", "IT", 94000),
        ("Support Engineer", "IT", 68000),
        ("Sales Executive", "Sales", 73000),
        ("Account Manager", "Sales", 88000),
        ("Accountant", "Finance", 76000),
        ("Payroll Specialist", "Finance", 82000),
        ("HR Officer", "HR", 79000),
        ("Recruiter", "HR", 72000),
    ]

    #: A leaver's contract closes here — the last day of the newest seeded
    #: payrun period. Every historical payrun still resolves a contract for
    #: them, so the seeded history validates; a payrun for March or later
    #: raises NO_CONTRACT, which is what makes the check demonstrable.
    LEAVER_END = date(2026, 2, 28)

    #: Dealt to the first generated people, in order, so that every roster above
    #: 22 contains at least one of each interesting shape however small N is.
    GUARANTEED_SHAPES = ["JOINER", "LEAVER", "RAISE"]

    #: A guaranteed joiner starts here — inside March, so a March payrun shows
    #: proration. Random joiners still land anywhere in the Feb–Mar window.
    GUARANTEED_JOIN_DATE = date(2026, 3, 11)

    def _sequencer(self, model, field, prefix):
        """
        Hand back a `next(year) -> 'PREFIX/YYYY/NNNN'` callable.

        `Employee.save` and `Contract.save` mint these references themselves,
        but `bulk_create` does not call `save`, so the generated rows have to
        carry their own. Counters start above whatever is already in the table
        so the fixed roster's codes — which the demo script quotes — are never
        reused or shifted.
        """
        highest = {}
        for value in model.objects.values_list(field, flat=True):
            try:
                _, year, seq = value.split("/")
                highest[year] = max(highest.get(year, 0), int(seq))
            except (ValueError, AttributeError):
                continue

        def mint(year):
            key = str(year)
            highest[key] = highest.get(key, 0) + 1
            return f"{prefix}/{key}/{highest[key]:04d}"

        return mint

    def _generated_roster(self, company, departments, positions, locations,
                          schedules, structures, target):
        """
        Grow the roster to `target` people (T-089).

        The 22 fixed demo employees are already in the database and are left
        exactly as they are. Everything here is appended after them, so the
        random stream the fixed roster drew from is untouched and a default
        seed is byte-for-byte what it always was.
        """
        extra = target - len(self.ROSTER)
        if extra <= 0:
            return []

        emp_code = self._sequencer(Employee, "employee_code", "EMP")
        con_ref = self._sequencer(Contract, "reference", "CON")

        rows, plans = [], []
        for i in range(extra):
            first = random.choice(self.GEN_FIRST)
            last = random.choice(self.GEN_LAST)
            title, dept, base = random.choice(self.GEN_POSITIONS)

            roll = random.random()
            if roll < 0.05:
                etype, schedule = "INTERN", schedules["Flexible Hybrid"]
            elif roll < 0.12:
                etype, schedule = "PART_TIME", schedules["Part-time 20h"]
            else:
                etype, schedule = "FULL_TIME", schedules["40 Hours / Week"]

            # Four contract shapes, in the proportions a real roster has —
            # except that the first three are dealt out deterministically. At a
            # small N the random draw can produce none of a shape at all, and a
            # generated roster whose interesting cases may simply be absent
            # demonstrates nothing and makes its tests probabilistic.
            if i < len(self.GUARANTEED_SHAPES):
                profile = self.GUARANTEED_SHAPES[i]
            else:
                shape = random.random()
                if shape < 0.04:
                    profile = "JOINER"      # starts mid-period — proration
                elif shape < 0.07:
                    profile = "LEAVER"      # contract closes 28 Feb 2026
                elif shape < 0.18:
                    profile = "RAISE"       # expired + running pair
                else:
                    profile = "STANDARD"

            if profile == "JOINER":
                joined = (self.GUARANTEED_JOIN_DATE
                          if i < len(self.GUARANTEED_SHAPES)
                          else date(2026, 2, 1) + timedelta(days=random.randint(8, 45)))
            else:
                joined = date(2023, 1, 2) + timedelta(days=random.randint(0, 1060))

            wage = D(base if etype == "FULL_TIME"
                     else int(base * 0.55) if etype == "PART_TIME"
                     else 25000)
            wage += D(random.randrange(-6, 9) * 1000)

            has_bank = random.random() >= 0.05

            rows.append(Employee(
                employee_code=emp_code(joined.year),
                first_name=first, last_name=last, company=company,
                department=departments[dept], job_position=positions[title],
                work_location=random.choice(locations),
                working_schedule=schedule, employee_type=etype,
                date_of_joining=joined,
                work_email=f"{first}.{last}.{i + 1}@oxp.com".lower(),
                work_phone=f"+91 98{random.randint(10000000, 99999999)}",
                bank_account_number=(f"5011{random.randint(10**9, 10**10 - 1)}"
                                     if has_bank else None),
                bank_ifsc="HDFC0001234" if has_bank else None,
                pan_number=f"ABCDE{random.randint(1000, 9999)}F",
            ))
            plans.append((profile, joined, wage, etype, schedule, dept, title))

        Employee.objects.bulk_create(rows, batch_size=500)

        structure_for = {"INTERN": structures["intern"]}
        contracts, counts = [], {"JOINER": 0, "LEAVER": 0,
                                 "RAISE": 0, "STANDARD": 0}

        for emp, (profile, joined, wage, etype, schedule, dept, title) in zip(rows, plans):
            counts[profile] += 1
            common = {
                "working_schedule": schedule,
                "salary_structure": structure_for.get(etype, structures["regular"]),
                "department": departments[dept],
                "job_position": positions[title],
            }
            # Attendance is only meaningful while somebody is actually employed.
            emp._attend_from = joined
            emp._attend_to = None

            if profile == "RAISE":
                # The raise lands on 01 Jan 2026, so December resolves the old
                # contract and January the new one — graded rule #1 at scale.
                contracts.append(Contract(
                    employee=emp, reference=con_ref(joined.year),
                    start_date=joined, end_date=date(2025, 12, 31),
                    wage=wage - D("7000"), state=Contract.EXPIRED, **common))
                contracts.append(Contract(
                    employee=emp, reference=con_ref(2026),
                    start_date=date(2026, 1, 1), end_date=None,
                    wage=wage, state=Contract.RUNNING, **common))
            elif profile == "LEAVER":
                emp._attend_to = self.LEAVER_END
                contracts.append(Contract(
                    employee=emp, reference=con_ref(joined.year),
                    start_date=joined, end_date=self.LEAVER_END,
                    wage=wage, state=Contract.EXPIRED, **common))
            else:
                contracts.append(Contract(
                    employee=emp, reference=con_ref(joined.year),
                    start_date=joined, end_date=None,
                    wage=wage, state=Contract.RUNNING, **common))

        Contract.objects.bulk_create(contracts, batch_size=500)

        # Everyone reports to the HR manager, matching the fixed roster.
        Employee.objects.filter(pk__in=[e.pk for e in rows]).update(
            manager=Employee.objects.get(work_email="sara@oxp.com"))

        no_bank = sum(1 for e in rows if not e.has_bank_details)
        self.stdout.write(
            f"  generated: {len(rows)} employees, {len(contracts)} contracts "
            f"({counts['RAISE']} with a raise, {counts['JOINER']} mid-period "
            f"joiners, {counts['LEAVER']} leavers, {no_bank} without a bank "
            f"account)")
        return rows

    def _users(self, employees, roles):
        accounts = [
            ("admin@oxp.com", None, [Role.ADMIN]),
            ("aarav@oxp.com", employees[0], [Role.PAYROLL_MANAGER]),
            ("sara@oxp.com", employees[1], [Role.HR_MANAGER]),
            ("rahul@oxp.com", employees[18], [Role.PAYROLL_USER]),
            ("john@oxp.com", employees[2], [Role.EMPLOYEE]),
        ]
        for email, emp, codes in accounts:
            user, created = User.objects.get_or_create(
                email=email, defaults={"employee": emp, "is_staff": email.startswith("admin")})
            if created:
                user.set_password("demo1234")
                user.is_superuser = email.startswith("admin")
                user.save()
            user.roles.set([roles[c] for c in codes])
        self.stdout.write("  users: 5 accounts, password 'demo1234'")

    # ---------------------------------------------------------------- timeoff

    def _timeoff(self, employees):
        types = {}
        for name, code, unit, req_alloc, paid, approval in [
            ("Paid Time Off", "PTO", "DAYS", True, True, "MANAGER"),
            ("Sick Leave", "SICK", "DAYS", False, True, "MANAGER"),
            ("Comp Off", "COMP", "HOURS", True, True, "OFFICER"),
            ("Unpaid Leave", "UNPAID", "DAYS", False, False, "MANAGER"),
        ]:
            types[code], _ = TimeOffType.objects.get_or_create(
                code=code, defaults={
                    "name": name, "unit": unit, "requires_allocation": req_alloc,
                    "is_paid": paid, "approval": approval,
                    "work_entry_code": "Leave Work Entry",
                    "description": f"{name}. "
                                   f"{'Balance comes from approved allocations.' if req_alloc else 'No allocation required.'}",
                })

        # One allocation each, written in bulk — at 250 employees the
        # row-at-a-time get_or_create this replaced was 250 round trips.
        already = set(Allocation.objects
                      .filter(time_off_type=types["PTO"],
                              valid_from=date(2026, 1, 1))
                      .values_list("employee_id", flat=True))
        Allocation.objects.bulk_create([
            Allocation(
                employee=emp, time_off_type=types["PTO"],
                valid_from=date(2026, 1, 1), name="Paid Time Off 2026",
                allocated=D("20"), valid_to=date(2026, 12, 31),
                state=Allocation.APPROVED,
                description="Annual leave balance granted at start of policy year.")
            for emp in employees if emp.pk not in already
        ], batch_size=500)

        # A spread of requests, approved and pending
        for i, emp in enumerate(employees[:10]):
            req = TimeOffRequest(
                employee=emp, time_off_type=types["PTO"],
                date_from=date(2026, 2, 9) + timedelta(days=i * 3),
                date_to=date(2026, 2, 11) + timedelta(days=i * 3),
                reason="Family vacation",
            )
            req.duration = req.compute_duration()
            try:
                req.full_clean()
                req.state = (TimeOffRequest.APPROVED if i % 3 else TimeOffRequest.TO_APPROVE)
                if req.state == TimeOffRequest.APPROVED:
                    req.approved_at = timezone.now()
                req.save()
            except Exception as exc:  # pragma: no cover — seed resilience
                self.stderr.write(f"    skipped leave for {emp.full_name}: {exc}")

        # Unpaid leave so LOP genuinely reaches a payslip (PRD-4.6.2)
        emp = employees[3]
        lop = TimeOffRequest(
            employee=emp, time_off_type=types["UNPAID"],
            date_from=date(2026, 2, 17), date_to=date(2026, 2, 18),
            reason="Personal, unpaid", state=TimeOffRequest.APPROVED,
            approved_at=timezone.now())
        lop.duration = lop.compute_duration()
        lop.save()

        alloc = Allocation.objects.filter(time_off_type=types["PTO"]).first()
        self.stdout.write(
            f"  time off: 4 types, {Allocation.objects.count()} allocations, "
            f"{TimeOffRequest.objects.count()} requests "
            f"(sample balance {alloc.allocated}/{alloc.taken}/{alloc.remaining})")

    # ------------------------------------------------------------- attendance

    #: Attendance spans every payroll period we seed. It used to start in
    #: February, which left the December and January payslips reading
    #: "Worked Days 0.00 / 23.00" — the payruns were correct but looked broken.
    ATTENDANCE_FROM = date(2025, 12, 1)
    ATTENDANCE_TO = date(2026, 3, 31)

    #: Overtime is confined to February onward. December and January are clean
    #: eight-hour months, which keeps the demo's headline evidence intact: the
    #: December-under-January gap is caused purely by two employees resolving
    #: to older, cheaper contracts, and February's rise is purely overtime.
    #: Sprinkling overtime everywhere would swamp both signals with noise.
    OVERTIME_FROM = date(2026, 2, 1)

    #: A person's working pattern is their schedule's, not Monday-to-Friday
    #: nine-to-five. Reading it from the contract keeps three things honest at
    #: once: worked days never exceed expected days, the attendance screen
    #: agrees with the working-schedules screen, and the derived weekly hours
    #: of graded rule #2 describe something the data actually shows.
    #:
    #: Without this the part-time employee was seeded five days a week at
    #: eight hours — 44 hours against a 20-hour contract, and 23 worked days
    #: against 19 expected. The holiday case immediately below was the same
    #: bug found from the other end and fixed for holidays alone.
    def _schedule_pattern(self, emp):
        """{weekday: hours} for this employee, falling back to Mon-Fri 8h."""
        contract = (Contract.objects
                    .filter(employee=emp)
                    .select_related("working_schedule")
                    .order_by("-start_date")
                    .first())
        schedule = contract.working_schedule if contract else None
        lines = list(schedule.lines.all()) if schedule else []
        if not lines:
            return {d: 8.0 for d in range(5)}
        return {line.day_of_week: float(line.hours) for line in lines}

    def _attendance(self, employees):
        made = 0
        rows = []
        span = (self.ATTENDANCE_TO - self.ATTENDANCE_FROM).days + 1
        # Nobody is at their desk on a company holiday. Generating attendance
        # on them made worked days exceed expected days — January read 22 of 21.
        holidays = set(Holiday.objects.values_list("date", flat=True))
        for emp in employees:
            pattern = self._schedule_pattern(emp)
            # Generated joiners and leavers are only at work while employed.
            # The fixed roster carries neither attribute, so it is unaffected.
            attend_from = getattr(emp, "_attend_from", None)
            attend_to = getattr(emp, "_attend_to", None)
            for offset in range(span):
                day = self.ATTENDANCE_FROM + timedelta(days=offset)
                if day.weekday() not in pattern or day in holidays:
                    continue
                if attend_from and day < attend_from:
                    continue
                if attend_to and day > attend_to:
                    continue
                if random.random() < 0.07:      # absence
                    continue

                scheduled = pattern[day.weekday()]
                start_m = random.randint(0, 40)
                # Overtime is measured against the person's own day, so a
                # part-timer earns it after five hours rather than after eight.
                if day >= self.OVERTIME_FROM:
                    worked = random.uniform(scheduled, scheduled + 1.5)
                else:
                    worked = random.uniform(scheduled, scheduled + 0.5)

                ci = timezone.make_aware(datetime.combine(day, time(9, start_m)))
                co = ci + timedelta(hours=worked)
                overtime = D(str(round(
                    max(0.0, worked - (scheduled + 0.5)), 2)))
                rows.append(Attendance(
                    employee=emp, check_in=ci, check_out=co,
                    status=Attendance.OVERTIME if overtime > 0 else Attendance.PRESENT,
                    overtime_hours=overtime))
                made += 1

        # ~87 working days per person: at 250 employees this is over 20,000
        # rows, which is unusable one INSERT at a time.
        Attendance.objects.bulk_create(rows, batch_size=2000)
        self.stdout.write(
            f"  attendance: {made} records, "
            f"{self.ATTENDANCE_FROM:%b %Y} - {self.ATTENDANCE_TO:%b %Y} "
            f"(overtime from {self.OVERTIME_FROM:%b %Y})")

    # ---------------------------------------------------------------- payroll

    def _payroll_history(self, company, structure, employees):
        periods = [
            ("December 2025", date(2025, 12, 1), date(2025, 12, 31)),
            ("January 2026", date(2026, 1, 1), date(2026, 1, 31)),
            ("February 2026", date(2026, 2, 1), date(2026, 2, 28)),
        ]
        for name, start, end in periods:
            payrun, created = Payrun.objects.get_or_create(
                name=name, company=company,
                defaults={"salary_structure": structure,
                          "period_start": start, "period_end": end})
            if not created:
                continue
            # Somebody who had not joined yet, or had already left, has no
            # contract for the period. Including them would raise a NO_CONTRACT
            # error, and an errored payrun cannot be validated — the seeded
            # history would then sit at Computed instead of Paid. A payrun the
            # operator creates for March still meets them, which is the point.
            eligible = [e for e in employees
                        if e.employee_type != "INTERN"
                        and e.contract_for_period(start, end) is not None]
            began = time_module.perf_counter()
            engine.create_payrun_payslips(payrun, eligible)
            engine.compute_payrun(payrun)
            elapsed = time_module.perf_counter() - began
            if payrun.can_validate:
                engine.validate_payrun(payrun)
                engine.mark_payrun_paid(payrun)
            self.stdout.write(
                f"  payrun {name}: {payrun.payslip_count} payslips, "
                f"net INR {payrun.total_net:,.2f}, "
                f"{payrun.warning_count} warnings, state={payrun.state}, "
                f"computed in {elapsed:.2f}s")

    #: One person paid off-cycle in March, before the operator runs March
    #: properly. This is the seed's reason for existing beyond history.
    #:
    #: PRD success criterion 4 asks for at least two distinct warning codes
    #: before validation. `AC_MISSING` fires twice on the demo roster and
    #: nothing else does — every other code needs a shape the fixed 22 do not
    #: have, and the three that would fit are ERROR severity, which blocks
    #: Validate and would break the demo two steps later.
    #:
    #: `DUPLICATE` is the exception, and it is the problem statement's own named
    #: example: warning severity, so Validate still proceeds, and it needs
    #: nothing but a payslip that already covers the period. So the seed leaves
    #: one — a correction run for a single employee, computed but deliberately
    #: not paid, exactly as a real one would sit mid-month. When the operator
    #: then runs March for everybody, that employee is skipped with a reason.
    #:
    #: Vikram Rao is chosen because he appears nowhere in the demo script: not
    #: the protagonist, not one of the two without bank details, and not in the
    #: leave scenario. The warnings therefore name three different people.
    OFF_CYCLE_EMPLOYEE = ("Vikram", "Rao")
    OFF_CYCLE_PERIOD = (date(2026, 3, 1), date(2026, 3, 31))

    def _off_cycle_correction(self, company, structure, employees):
        first, last = self.OFF_CYCLE_EMPLOYEE
        subject = next((e for e in employees
                        if e.first_name == first and e.last_name == last), None)
        start, end = self.OFF_CYCLE_PERIOD
        if subject is None or subject.contract_for_period(start, end) is None:
            return

        payrun, created = Payrun.objects.get_or_create(
            name="March 2026 (off-cycle correction)", company=company,
            defaults={"salary_structure": structure,
                      "period_start": start, "period_end": end})
        if not created:
            return

        engine.create_payrun_payslips(payrun, [subject])
        engine.compute_payrun(payrun)
        # Left at Computed on purpose. Paying it would make it the newest paid
        # payrun, and the dashboard opens on that.
        self.stdout.write(
            f"  payrun {payrun.name}: {payrun.payslip_count} payslip for "
            f"{subject.full_name}, state={payrun.state} "
            f"(leaves a DUPLICATE for the March run to find)")

    # ----------------------------------------------------------------- report

    def _summary(self):
        from payroll.models import Payslip, PayslipLine, PayslipWarning
        self.stdout.write(self.style.SUCCESS("\nSeed complete."))
        self.stdout.write(
            f"  {Employee.objects.count()} employees | "
            f"{Contract.objects.count()} contracts | "
            f"{Attendance.objects.count()} attendance | "
            f"{TimeOffRequest.objects.count()} leave requests")
        self.stdout.write(
            f"  {Payrun.objects.count()} payruns | "
            f"{Payslip.objects.count()} payslips | "
            f"{PayslipLine.objects.count()} lines | "
            f"{PayslipWarning.objects.count()} warnings")
        self.stdout.write("\n  Login: admin@oxp.com / demo1234")
