"""
Self-service — what a person may change about themselves, and what needs a
second pair of eyes.

The split is not arbitrary. A phone number is the employee's own business: if
they get it wrong, they miss a call. A **bank account number** is the single
most attacked field in any payroll system — change it quietly the day before a
payrun and the salary lands somewhere else. So the rule is:

* fields that only affect the employee → edited directly, logged;
* fields that affect **pay, identity or entitlement** → raised as a request,
  reviewed by HR, and only then written.

Everything else about a person — department, manager, job position, contract,
wage — is not self-service in either form. Those are HR's records, and they
appear here nowhere.
"""

from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


#: Editable by the employee, applied immediately.
DIRECT_FIELDS = {
    "work_phone": "Work phone",
    "personal_phone": "Personal phone",
    "personal_email": "Personal email",
    "address": "Address",
}

#: Editable by the employee only through an approved request.
APPROVAL_FIELDS = {
    "first_name": "First name",
    "last_name": "Last name",
    "date_of_birth": "Date of birth",
    "gender": "Gender",
    "bank_account_number": "Bank account number",
    "bank_ifsc": "Bank IFSC",
    "pan_number": "PAN number",
}

#: Shown on the profile screen but never editable there, in either mode.
READ_ONLY_FIELDS = {
    "employee_code": "Employee code",
    "work_email": "Work email",
    "department": "Department",
    "job_position": "Job position",
    "manager": "Manager",
    "working_schedule": "Working schedule",
    "employee_type": "Employment type",
    "date_of_joining": "Date of joining",
}

#: The subset whose change should make a reviewer look twice. Surfaced with a
#: warning on the review screen and always written to the audit log.
SENSITIVE_FIELDS = {"bank_account_number", "bank_ifsc", "pan_number"}


class ProfileChangeRequest(TimeStampedModel):
    """
    One employee-initiated change to one field, awaiting an HR decision.

    Kept as one row per field rather than one per form submission so that a
    reviewer can approve a corrected spelling and refuse a bank account in the
    same sitting, and so the audit trail names exactly what moved.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REFUSED = "REFUSED"
    CANCELLED = "CANCELLED"
    STATES = [(PENDING, "Pending"), (APPROVED, "Approved"),
              (REFUSED, "Refused"), (CANCELLED, "Cancelled")]

    employee = models.ForeignKey("employees.Employee", on_delete=models.CASCADE,
                                 related_name="profile_change_requests")
    requested_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name="profile_changes_raised")
    field = models.CharField(max_length=40)
    old_value = models.CharField(max_length=200, blank=True)
    new_value = models.CharField(max_length=200, blank=True)
    reason = models.TextField(blank=True)

    state = models.CharField(max_length=10, choices=STATES, default=PENDING,
                             db_index=True)
    reviewed_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name="profile_changes_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["employee", "state"])]

    def __str__(self):
        return f"{self.employee.full_name}: {self.field_label} → {self.new_value}"

    @property
    def field_label(self):
        return APPROVAL_FIELDS.get(self.field, self.field)

    @property
    def is_sensitive(self):
        return self.field in SENSITIVE_FIELDS

    @property
    def is_open(self):
        return self.state == self.PENDING

    # -- decisions ----------------------------------------------------------

    def approve(self, reviewer, note=""):
        """
        Write the value through and close the request.

        The employee is deliberately not allowed to be their own reviewer, even
        when they hold HR rights — an HR Manager who could approve their own
        bank-account change would make the whole control decorative. The check
        lives here, at the write, rather than in the view.
        """
        if not self.is_open:
            raise ValueError(f"This request is already {self.get_state_display().lower()}.")
        if reviewer is not None and getattr(reviewer, "employee_id", None) == self.employee_id:
            raise ValueError("You cannot approve a change to your own record.")

        setattr(self.employee, self.field, self.new_value or None)
        self.employee.save(update_fields=[self.field, "updated_at"])

        self.state = self.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note[:200]
        self.save(update_fields=["state", "reviewed_by", "reviewed_at",
                                 "review_note", "updated_at"])
        return self

    def refuse(self, reviewer, note=""):
        if not self.is_open:
            raise ValueError(f"This request is already {self.get_state_display().lower()}.")
        if reviewer is not None and getattr(reviewer, "employee_id", None) == self.employee_id:
            raise ValueError("You cannot decide a change to your own record.")
        self.state = self.REFUSED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note[:200]
        self.save(update_fields=["state", "reviewed_by", "reviewed_at",
                                 "review_note", "updated_at"])
        return self

    def cancel(self):
        """Withdrawn by the person who raised it, while still pending."""
        if not self.is_open:
            raise ValueError("Only a pending request can be withdrawn.")
        self.state = self.CANCELLED
        self.save(update_fields=["state", "updated_at"])
        return self
