"""
Time off: types, allocations and requests.

Graded rule #3 — allocation-gated leave. If a type requires allocation, a
request cannot be submitted without an approved allocation covering the dates
with sufficient balance. Balance is derived, never stored (PRD-4.3).
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from core.models import Holiday, TimeStampedModel
from employees.models import Employee

ZERO = Decimal("0.00")


class TimeOffType(TimeStampedModel):
    DAYS = "DAYS"
    HOURS = "HOURS"
    UNITS = [(DAYS, "Days"), (HOURS, "Hours")]

    NONE = "NONE"
    MANAGER = "MANAGER"
    OFFICER = "OFFICER"
    APPROVALS = [(NONE, "No Validation"), (MANAGER, "By Manager"),
                 (OFFICER, "By Time Off Officer")]

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    unit = models.CharField(max_length=6, choices=UNITS, default=DAYS)

    #: The gate for graded rule #3
    requires_allocation = models.BooleanField(default=True)
    approval = models.CharField(max_length=10, choices=APPROVALS, default=MANAGER)

    #: Unpaid leave contributes Loss of Pay to the payslip (PRD-4.6.2)
    is_paid = models.BooleanField(default=True)
    work_entry_code = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=20, default="blue")
    active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Allocation(TimeStampedModel):
    DRAFT = "DRAFT"
    TO_APPROVE = "TO_APPROVE"
    APPROVED = "APPROVED"
    REFUSED = "REFUSED"
    STATES = [(DRAFT, "Draft"), (TO_APPROVE, "To Approve"),
              (APPROVED, "Approved"), (REFUSED, "Refused")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                 related_name="allocations")
    time_off_type = models.ForeignKey(TimeOffType, on_delete=models.PROTECT,
                                      related_name="allocations")
    name = models.CharField(max_length=120)
    allocated = models.DecimalField(max_digits=6, decimal_places=2)
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=12, choices=STATES, default=DRAFT)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-valid_from"]
        indexes = [models.Index(fields=["employee", "time_off_type", "state"])]
        constraints = [
            models.CheckConstraint(condition=Q(allocated__gt=0),
                                   name="allocation_positive"),
        ]

    def __str__(self):
        return f"{self.name} — {self.employee.full_name}"

    # -- derived, never stored (PRD-4.3.3) ---------------------------------

    @property
    def taken(self) -> Decimal:
        return self.consuming_requests.filter(
            state=TimeOffRequest.APPROVED
        ).aggregate(t=Coalesce(Sum("duration"), ZERO))["t"]

    @property
    def remaining(self) -> Decimal:
        return self.allocated - self.taken

    @property
    def is_active_balance(self):
        return self.state == self.APPROVED

    def covers(self, date_from, date_to):
        return (self.valid_from <= date_from
                and (self.valid_to is None or self.valid_to >= date_to))


class TimeOffRequest(TimeStampedModel):
    DRAFT = "DRAFT"
    TO_APPROVE = "TO_APPROVE"
    APPROVED = "APPROVED"
    REFUSED = "REFUSED"
    CANCELLED = "CANCELLED"
    STATES = [(DRAFT, "Draft"), (TO_APPROVE, "To Approve"),
              (APPROVED, "Approved"), (REFUSED, "Refused"),
              (CANCELLED, "Cancelled")]

    HALF_DAY_CHOICES = [("FIRST", "First Half"), ("SECOND", "Second Half")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                 related_name="timeoff_requests")
    time_off_type = models.ForeignKey(TimeOffType, on_delete=models.PROTECT,
                                      related_name="requests")
    allocation_used = models.ForeignKey(
        Allocation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="consuming_requests")

    date_from = models.DateField()
    date_to = models.DateField()
    duration = models.DecimalField(max_digits=6, decimal_places=2, default=ZERO)
    half_day = models.CharField(max_length=6, choices=HALF_DAY_CHOICES, blank=True)

    state = models.CharField(max_length=12, choices=STATES, default=DRAFT)
    reason = models.TextField(blank=True)
    approver = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                                 null=True, blank=True,
                                 related_name="approved_timeoff")
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_from"]
        indexes = [models.Index(fields=["employee", "state", "date_from"])]
        constraints = [
            models.CheckConstraint(condition=Q(date_to__gte=models.F("date_from")),
                                   name="timeoff_dates_ordered"),
        ]

    def __str__(self):
        return f"{self.employee.full_name} — {self.time_off_type.name}"

    # -- duration -----------------------------------------------------------

    def compute_duration(self) -> Decimal:
        """Working days in range, excluding weekends and company holidays."""
        if self.half_day and self.date_from == self.date_to:
            return Decimal("0.5")

        holidays = set(Holiday.objects.filter(
            company=self.employee.company,
            date__range=(self.date_from, self.date_to),
        ).values_list("date", flat=True))

        schedule = self.employee.working_schedule
        working_days = (set(schedule.lines.values_list("day_of_week", flat=True))
                        if schedule else {0, 1, 2, 3, 4})

        count, cursor = 0, self.date_from
        while cursor <= self.date_to:
            if cursor.weekday() in working_days and cursor not in holidays:
                count += 1
            cursor += timedelta(days=1)
        return Decimal(count)

    # -- the allocation gate — graded rule #3 -------------------------------

    def find_valid_allocation(self):
        """Approved allocation of this type covering these dates."""
        candidates = Allocation.objects.filter(
            employee=self.employee,
            time_off_type=self.time_off_type,
            state=Allocation.APPROVED,
            valid_from__lte=self.date_from,
        ).filter(Q(valid_to__gte=self.date_to) | Q(valid_to__isnull=True))
        # Prefer the allocation that can actually absorb the request
        for alloc in candidates.order_by("valid_from"):
            if alloc.remaining >= self.duration:
                return alloc
        return candidates.order_by("valid_from").first()

    def clean(self):
        if not self.duration or self.duration <= 0:
            self.duration = self.compute_duration()
        if self.duration <= 0:
            raise ValidationError(
                "Request covers no working days — check the dates, weekends "
                "and holidays.")

        if not self.time_off_type.requires_allocation:
            return

        alloc = self.find_valid_allocation()
        if alloc is None:
            raise ValidationError(
                f"No approved {self.time_off_type.name} allocation covering "
                f"{self.date_from} – {self.date_to}. An allocation must be "
                f"created and approved before this request can be submitted.")

        available = alloc.remaining
        # An edit to an already-approved request must not count itself twice
        if self.pk and self.state == self.APPROVED and self.allocation_used_id == alloc.pk:
            available += Decimal(
                TimeOffRequest.objects.get(pk=self.pk).duration)

        if available < self.duration:
            raise ValidationError(
                f"Insufficient balance: {available} {self.time_off_type.get_unit_display().lower()} "
                f"remaining, {self.duration} requested.")

        self.allocation_used = alloc

    def save(self, *args, **kwargs):
        if not self.duration or self.duration <= 0:
            self.duration = self.compute_duration()
        super().save(*args, **kwargs)

    # -- workflow -----------------------------------------------------------

    def approve(self, user=None):
        from django.utils import timezone
        self.full_clean(exclude=["approver"])
        self.state = self.APPROVED
        self.approver = user
        self.approved_at = timezone.now()
        self.save()
        return self

    def refuse(self, user=None):
        self.state = self.REFUSED
        self.approver = user
        self.save(update_fields=["state", "approver", "updated_at"])
        return self

    @property
    def is_unpaid(self):
        """Drives Loss of Pay on the payslip (PRD-4.6.2)."""
        return not self.time_off_type.is_paid
