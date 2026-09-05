"""
Employee master data, working schedules and contracts.

Contains graded rules #1 (period-based contract resolution) and #2 (derived
weekly hours). See claude/context/prd.md §4.1 and §4.2.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.models import Company, Department, JobPosition, TimeStampedModel, WorkLocation

ZERO = Decimal("0.00")


# ==========================================================================
# Working schedules — graded rule #2
# ==========================================================================

class WorkingSchedule(TimeStampedModel):
    FIXED = "FIXED"
    VARIABLE = "VARIABLE"
    CALENDAR_TYPES = [(FIXED, "Fixed"), (VARIABLE, "Variable")]

    name = models.CharField(max_length=120)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="working_schedules")
    calendar_type = models.CharField(max_length=10, choices=CALENDAR_TYPES,
                                     default=FIXED)
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    # -- derived, never stored (PRD-4.2.2) ---------------------------------

    @property
    def hours_per_week(self) -> Decimal:
        return sum((line.hours for line in self.lines.all()), ZERO)

    @property
    def days_per_week(self) -> int:
        """Distinct days — a day may carry several lines (split shifts)."""
        return self.lines.values("day_of_week").distinct().count()

    def expected_working_days(self, start, end, holidays=None):
        """Working days in [start, end] per this schedule, minus holidays."""
        holidays = set(holidays or [])
        working_days = set(self.lines.values_list("day_of_week", flat=True))
        count, cursor = 0, start
        while cursor <= end:
            if cursor.weekday() in working_days and cursor not in holidays:
                count += 1
            cursor += timedelta(days=1)
        return count


class ScheduleLine(models.Model):
    DAYS = [(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
            (4, "Friday"), (5, "Saturday"), (6, "Sunday")]

    schedule = models.ForeignKey(WorkingSchedule, on_delete=models.CASCADE,
                                 related_name="lines")
    day_of_week = models.SmallIntegerField(choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    break_minutes = models.SmallIntegerField(default=0)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=models.F("start_time")),
                                   name="schedule_line_end_after_start"),
        ]

    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

    @property
    def hours(self) -> Decimal:
        base = datetime(2000, 1, 1)
        delta = (datetime.combine(base, self.end_time)
                 - datetime.combine(base, self.start_time))
        net = delta - timedelta(minutes=self.break_minutes)
        return round(Decimal(net.total_seconds()) / Decimal(3600), 2)


# ==========================================================================
# Employee
# ==========================================================================

class Employee(TimeStampedModel):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    INTERN = "INTERN"
    CONTRACTOR = "CONTRACTOR"
    EMPLOYEE_TYPES = [
        (FULL_TIME, "Full Time"), (PART_TIME, "Part Time"),
        (INTERN, "Intern"), (CONTRACTOR, "Contractor"),
    ]

    GENDERS = [("M", "Male"), ("F", "Female"), ("O", "Other")]

    employee_code = models.CharField(max_length=20, unique=True, blank=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    work_email = models.EmailField(unique=True)
    work_phone = models.CharField(max_length=20, blank=True)

    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="employees")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="employees")
    job_position = models.ForeignKey(JobPosition, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="employees")
    manager = models.ForeignKey("self", on_delete=models.SET_NULL,
                                null=True, blank=True, related_name="reports")
    work_location = models.ForeignKey(WorkLocation, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name="employees")
    working_schedule = models.ForeignKey(WorkingSchedule, on_delete=models.SET_NULL,
                                         null=True, blank=True, related_name="employees")

    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPES,
                                     default=FULL_TIME)
    date_of_joining = models.DateField()

    # Payroll-critical — a null account raises the A/C missing warning
    bank_account_number = models.CharField(max_length=34, blank=True, null=True)
    bank_ifsc = models.CharField(max_length=11, blank=True, null=True)
    pan_number = models.CharField(max_length=10, blank=True, null=True)

    # Private Information tab
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDERS, blank=True)
    personal_email = models.EmailField(blank=True)
    personal_phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)

    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["first_name", "last_name"]
        indexes = [
            models.Index(fields=["department"]),
            models.Index(fields=["active"]),
            models.Index(fields=["employee_type"]),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def has_bank_details(self):
        return bool(self.bank_account_number and self.bank_ifsc)

    def save(self, *args, **kwargs):
        if not self.employee_code:
            year = (self.date_of_joining or datetime.now().date()).year
            last = (Employee.objects
                    .filter(employee_code__startswith=f"EMP/{year}/")
                    .order_by("-employee_code").first())
            seq = int(last.employee_code.split("/")[-1]) + 1 if last else 1
            self.employee_code = f"EMP/{year}/{seq:04d}"
        super().save(*args, **kwargs)

    def clean(self):
        # Guard against a manager cycle (data-model.md §5)
        seen, node = set(), self.manager
        while node is not None:
            if node.pk == self.pk or node.pk in seen:
                raise ValidationError({"manager": "Circular management chain."})
            seen.add(node.pk)
            node = node.manager

    # -- contract resolution ------------------------------------------------

    def contract_for_period(self, period_start, period_end):
        """Graded rule #1 — resolve by period, never by recency (PRD-4.1.2)."""
        return (self.contracts
                .filter(state=Contract.RUNNING, start_date__lte=period_end)
                .filter(Q(end_date__gte=period_start) | Q(end_date__isnull=True))
                .order_by("-start_date")
                .first())

    @property
    def current_contract(self):
        today = datetime.now().date()
        return self.contract_for_period(today, today)


# ==========================================================================
# Contract — graded rule #1
# ==========================================================================

class Contract(TimeStampedModel):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    STATES = [(DRAFT, "Draft"), (RUNNING, "Running"),
              (EXPIRED, "Expired"), (CANCELLED, "Cancelled")]

    reference = models.CharField(max_length=24, unique=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                 related_name="contracts")
    department = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="contracts")
    job_position = models.ForeignKey(JobPosition, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name="contracts")

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    wage = models.DecimalField(max_digits=12, decimal_places=2)

    working_schedule = models.ForeignKey(WorkingSchedule, on_delete=models.PROTECT,
                                         related_name="contracts")
    salary_structure = models.ForeignKey(
        "payroll.SalaryStructure", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="contracts")
    structure_type = models.CharField(max_length=60, default="Employee Salary")

    state = models.CharField(max_length=12, choices=STATES, default=DRAFT)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["employee", "state", "start_date", "end_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__isnull=True) | Q(end_date__gte=models.F("start_date")),
                name="contract_end_after_start"),
        ]

    def __str__(self):
        return f"{self.reference} — {self.employee.full_name}"

    def save(self, *args, **kwargs):
        if not self.reference:
            year = self.start_date.year
            last = (Contract.objects
                    .filter(reference__startswith=f"CON/{year}/")
                    .order_by("-reference").first())
            seq = int(last.reference.split("/")[-1]) + 1 if last else 1
            self.reference = f"CON/{year}/{seq:04d}"
        super().save(*args, **kwargs)

    def clean(self):
        """
        No overlapping RUNNING contracts (PRD-4.1.1).

        On PostgreSQL a gist EXCLUDE constraint also enforces this at the
        database level; on SQLite this validation is the only guard, so it
        must run on every save path.
        """
        if self.state != self.RUNNING:
            return
        clash = (Contract.objects
                 .filter(employee=self.employee, state=self.RUNNING)
                 .exclude(pk=self.pk)
                 .filter(start_date__lte=self.end_date or "9999-12-31")
                 .filter(Q(end_date__gte=self.start_date) | Q(end_date__isnull=True))
                 .first())
        if clash:
            raise ValidationError(
                f"Overlaps running contract {clash.reference} "
                f"({clash.start_date} – {clash.end_date or 'open'}).")

    @property
    def is_running(self):
        return self.state == self.RUNNING

    def covers(self, period_start, period_end):
        return (self.start_date <= period_end
                and (self.end_date is None or self.end_date >= period_start))
