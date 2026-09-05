"""
Seed representative demo data (T-028, PRD-7.1).

Targets deliberately chosen so the demo script works:
  - 22 employees across 5 departments
  - 2 employees with multiple contracts, proving period-based resolution
  - 2 employees with no bank account, so A/C missing fires on cue
  - 3 months of payroll history for the trend chart
  - mixed leave, both allocation-required and not

Usage:  python manage.py seed [--flush]
"""

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
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
        self._users(employees, roles)
        self._timeoff(employees)
        self._attendance(employees)
        self._payroll_history(company, structures["regular"], employees)

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
            ]
            formulas = {
                # Overtime paid at 1.5x the derived hourly rate
                "OT": "(wage / Decimal('173.33')) * overtime_hours * Decimal('1.5')",
                "GROSS": "categories['BASIC'] + categories['ALLOWANCE']",
                # One unpaid leave day costs one day of gross
                "LOP": "(rules['GROSS'] / expected_days) * lop_days if expected_days > 0 else Decimal('0')",
                "ESIC": "rules['GROSS'] * Decimal('0.0075') if rules['GROSS'] <= 21000 else Decimal('0')",
                "NET": "categories['GROSS'] - categories['DEDUCTION']",
            }
            for seq, name, code, cat, comp, amt, pct, base in rules:
                SalaryRule.objects.create(
                    structure=regular, sequence=seq, name=name, code=code,
                    category=cat, computation=comp, amount=amt, percentage=pct,
                    percentage_base=base, formula=formulas.get(code, ""))

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

        for emp in employees:
            Allocation.objects.get_or_create(
                employee=emp, time_off_type=types["PTO"],
                valid_from=date(2026, 1, 1),
                defaults={
                    "name": "Paid Time Off 2026", "allocated": D("20"),
                    "valid_to": date(2026, 12, 31),
                    "state": Allocation.APPROVED,
                    "description": "Annual leave balance granted at start of policy year.",
                })

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

    def _attendance(self, employees):
        made = 0
        for emp in employees:
            for offset in range(0, 60):
                day = date(2026, 2, 1) + timedelta(days=offset)
                if day > date(2026, 3, 31) or day.weekday() >= 5:
                    continue
                if random.random() < 0.07:      # absence
                    continue
                start_h, start_m = 9, random.randint(0, 40)
                worked = random.uniform(8.0, 9.5)
                ci = timezone.make_aware(datetime.combine(day, time(start_h, start_m)))
                co = ci + timedelta(hours=worked)
                overtime = D(str(round(max(0.0, worked - 8.5), 2)))
                Attendance.objects.create(
                    employee=emp, check_in=ci, check_out=co,
                    status=Attendance.OVERTIME if overtime > 0 else Attendance.PRESENT,
                    overtime_hours=overtime)
                made += 1
        self.stdout.write(f"  attendance: {made} records across Feb-Mar 2026")

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
            eligible = [e for e in employees if e.employee_type != "INTERN"]
            engine.create_payrun_payslips(payrun, eligible)
            engine.compute_payrun(payrun)
            if payrun.can_validate:
                engine.validate_payrun(payrun)
                engine.mark_payrun_paid(payrun)
            self.stdout.write(
                f"  payrun {name}: {payrun.payslip_count} payslips, "
                f"net INR {payrun.total_net:,.2f}, "
                f"{payrun.warning_count} warnings, state={payrun.state}")

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
