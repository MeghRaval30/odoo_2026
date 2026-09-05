"""
Attendance capture.

Worked hours are derived from check in/out, never stored as input.
Feeds worked days, LOP and overtime into payroll (PRD-4.6).
"""

from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import TimeStampedModel
from employees.models import Employee

ZERO = Decimal("0.00")


class Attendance(TimeStampedModel):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    OVERTIME = "OVERTIME"
    HALF_DAY = "HALF_DAY"
    STATUSES = [(PRESENT, "Present"), (ABSENT, "Absent"),
                (OVERTIME, "Overtime"), (HALF_DAY, "Half Day")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                 related_name="attendances")
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default=PRESENT)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=ZERO)

    is_manually_edited = models.BooleanField(default=False)
    edited_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                                  null=True, blank=True,
                                  related_name="edited_attendances")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-check_in"]
        verbose_name_plural = "attendances"
        indexes = [models.Index(fields=["employee", "check_in"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(check_out__isnull=True) | Q(check_out__gt=models.F("check_in")),
                name="attendance_checkout_after_checkin"),
            # At most one open session per employee
            models.UniqueConstraint(
                fields=["employee"], condition=Q(check_out__isnull=True),
                name="one_open_attendance_session_per_employee"),
        ]

    def __str__(self):
        return f"{self.employee.full_name} — {self.check_in:%d-%b-%Y}"

    # -- derived ------------------------------------------------------------

    @property
    def worked_hours(self) -> Decimal:
        if not self.check_out:
            return ZERO
        seconds = Decimal((self.check_out - self.check_in).total_seconds())
        return round(seconds / Decimal(3600), 2)

    @property
    def elapsed_hours(self) -> Decimal:
        """Live elapsed time for an open session — drives the widget."""
        end = self.check_out or timezone.now()
        seconds = Decimal((end - self.check_in).total_seconds())
        return round(seconds / Decimal(3600), 2)

    @property
    def is_open(self):
        return self.check_out is None

    @property
    def date(self):
        return timezone.localtime(self.check_in).date()

    @classmethod
    def open_session_for(cls, employee):
        return cls.objects.filter(employee=employee, check_out__isnull=True).first()

    @classmethod
    def check_in_employee(cls, employee):
        existing = cls.open_session_for(employee)
        if existing:
            return existing, False
        return cls.objects.create(employee=employee, check_in=timezone.now()), True

    @classmethod
    def check_out_employee(cls, employee):
        session = cls.open_session_for(employee)
        if not session:
            return None
        session.check_out = timezone.now()
        session.save(update_fields=["check_out", "updated_at"])
        return session
