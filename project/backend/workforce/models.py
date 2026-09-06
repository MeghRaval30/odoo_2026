"""
Working on many people at once.

Everything in the rest of this product acts on one record: one employee, one
contract, one leave request. That is correct for the daily work and useless for
the events that actually reshape a company -- an acquisition, a restructure, an
annual increment cycle, a site closure. Those are single decisions with
hundreds of consequences, and doing them one record at a time is both slow and
where the mistakes come from.

Four things live here.

  Segment          a saved question about the workforce ("engineers who joined
                   before 2022 earning under 60,000"). Stored as criteria, not
                   as a list of people, so it stays true as the roster changes.
  BulkOperation    a change applied to a segment, which is always previewed
                   before it is executed and always records what it did.
  Bond             a service agreement with a lock-in period and a recovery
                   amount, and the pro-rata liability that falls out of it.
  Playbook         a standing rule that watches for a condition and raises an
                   event when it is met, so "remind me about increments six
                   months after someone joins" is a thing the system does
                   rather than a thing somebody remembers.
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel
from employees.models import Employee


class Segment(TimeStampedModel):
    """
    A saved question, not a saved answer.

    Storing criteria rather than a list of employee ids is the whole point: a
    segment called "interns past six months" must mean the same thing in March
    that it meant in January, which it cannot if it is a frozen list.
    """

    MANUAL = "manual"
    AI = "ai"
    SOURCES = [(MANUAL, "Built by hand"), (AI, "Interpreted from a sentence")]

    name = models.CharField(max_length=140)
    description = models.CharField(max_length=300, blank=True)
    criteria = models.JSONField(default=dict)
    source = models.CharField(max_length=8, choices=SOURCES, default=MANUAL)
    #: The sentence somebody typed, kept beside the rule it compiled to. When
    #: the two disagree six months later, the sentence is the intent.
    nl_prompt = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="segments")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def resolve(self):
        from .segments import resolve
        return resolve(self.criteria)


class BondTemplate(TimeStampedModel):
    name = models.CharField(max_length=140)
    description = models.CharField(max_length=300, blank=True)
    duration_months = models.PositiveSmallIntegerField(default=24)
    recovery_amount = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=Decimal("0.00"))
    notice_days = models.PositiveSmallIntegerField(default=30)
    #: Placeholders: {{employee_name}} {{duration_months}} {{recovery_amount}}
    #: {{start_date}} {{end_date}} {{notice_days}} {{company}}
    body = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Bond(TimeStampedModel):
    DRAFT = "DRAFT"
    SENT = "SENT"
    SIGNED = "SIGNED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    BREACHED = "BREACHED"
    CANCELLED = "CANCELLED"
    STATES = [
        (DRAFT, "Draft"), (SENT, "Sent"), (SIGNED, "Signed"), (ACTIVE, "Active"),
        (COMPLETED, "Completed"), (BREACHED, "Breached"), (CANCELLED, "Cancelled"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                 related_name="bonds")
    template = models.ForeignKey(BondTemplate, null=True, blank=True,
                                 on_delete=models.SET_NULL, related_name="bonds")
    state = models.CharField(max_length=10, choices=STATES, default=DRAFT)

    start_date = models.DateField()
    end_date = models.DateField()
    duration_months = models.PositiveSmallIntegerField(default=24)
    recovery_amount = models.DecimalField(max_digits=12, decimal_places=2,
                                          default=Decimal("0.00"))
    notice_days = models.PositiveSmallIntegerField(default=30)

    signed_at = models.DateTimeField(null=True, blank=True)
    signed_name = models.CharField(max_length=160, blank=True)
    breach_date = models.DateField(null=True, blank=True)
    breach_note = models.CharField(max_length=300, blank=True)

    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL,
                                  related_name="bonds_issued")

    class Meta:
        ordering = ["-start_date"]
        indexes = [models.Index(fields=["state", "end_date"])]

    def __str__(self):
        return "%s until %s" % (self.employee.full_name, self.end_date)

    # -- the arithmetic that makes a mass exit meaningful -----------------

    def months_served(self, on=None):
        on = on or date.today()
        if on <= self.start_date:
            return 0
        months = ((on.year - self.start_date.year) * 12
                  + on.month - self.start_date.month)
        if on.day < self.start_date.day:
            months -= 1
        return max(0, min(months, self.duration_months))

    def months_remaining(self, on=None):
        return max(0, self.duration_months - self.months_served(on))

    def remaining_liability(self, on=None):
        """
        What the employee would owe if they left on `on`.

        Pro-rata by months served, because that is how a service bond is
        actually enforceable -- charging the full amount to somebody who served
        twenty-three of twenty-four months is the kind of term that gets a bond
        thrown out, and the whole reason to compute it here is so the figure in
        a mass-exit preview is the one that would really be recovered.
        """
        if self.duration_months <= 0 or self.state in (
                self.COMPLETED, self.CANCELLED):
            return Decimal("0.00")
        remaining = Decimal(self.months_remaining(on))
        share = remaining / Decimal(self.duration_months)
        return (self.recovery_amount * share).quantize(Decimal("0.01"))

    @property
    def is_active(self):
        return self.state in (self.SIGNED, self.ACTIVE)

    def days_to_expiry(self, on=None):
        return (self.end_date - (on or date.today())).days

    @property
    def is_expiring_soon(self):
        return self.is_active and 0 <= self.days_to_expiry() <= 60

    def render_body(self):
        template = self.template
        text = (template.body if template else "") or ""
        for key, value in {
            "employee_name": self.employee.full_name,
            "duration_months": self.duration_months,
            "recovery_amount": "INR {:,.2f}".format(self.recovery_amount),
            "start_date": self.start_date.strftime("%d %b %Y"),
            "end_date": self.end_date.strftime("%d %b %Y"),
            "notice_days": self.notice_days,
            "company": getattr(self.employee.company, "name", ""),
        }.items():
            text = text.replace("{{%s}}" % key, str(value))
        return text


class BulkOperation(TimeStampedModel):
    INCREMENT = "INCREMENT"
    EXIT = "EXIT"
    TRANSFER = "TRANSFER"
    BOND_ISSUE = "BOND_ISSUE"
    KINDS = [
        (INCREMENT, "Increment"), (EXIT, "Offboarding"),
        (TRANSFER, "Transfer"), (BOND_ISSUE, "Issue bonds"),
    ]

    DRAFT = "DRAFT"
    PREVIEWED = "PREVIEWED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    STATES = [(DRAFT, "Draft"), (PREVIEWED, "Previewed"),
              (EXECUTED, "Executed"), (FAILED, "Failed")]

    name = models.CharField(max_length=160, blank=True)
    kind = models.CharField(max_length=12, choices=KINDS)
    state = models.CharField(max_length=10, choices=STATES, default=DRAFT)
    segment = models.ForeignKey(Segment, null=True, blank=True,
                                on_delete=models.SET_NULL,
                                related_name="operations")
    criteria = models.JSONField(default=dict, blank=True)
    params = models.JSONField(default=dict, blank=True)
    #: The preview, stored. An operation that was executed should be able to
    #: show what it said it would do next to what it did.
    preview = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="bulk_operations")
    executed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or "%s (%s)" % (self.get_kind_display(), self.state)

    def effective_criteria(self):
        return self.segment.criteria if self.segment else (self.criteria or {})


class Playbook(TimeStampedModel):
    TENURE_REACHED = "TENURE_REACHED"
    CONTRACT_ENDING = "CONTRACT_ENDING"
    BOND_EXPIRING = "BOND_EXPIRING"
    PROBATION_ENDING = "PROBATION_ENDING"
    NO_BANK_ACCOUNT = "NO_BANK_ACCOUNT"
    TRIGGERS = [
        (TENURE_REACHED, "Tenure reached"),
        (CONTRACT_ENDING, "Contract ending"),
        (BOND_EXPIRING, "Bond expiring"),
        (PROBATION_ENDING, "Probation ending"),
        (NO_BANK_ACCOUNT, "No bank account"),
    ]

    NOTIFY = "NOTIFY"
    PROPOSE_INCREMENT = "PROPOSE_INCREMENT"
    FLAG_REVIEW = "FLAG_REVIEW"
    ACTIONS = [(NOTIFY, "Raise a reminder"),
               (PROPOSE_INCREMENT, "Propose an increment"),
               (FLAG_REVIEW, "Flag for review")]

    name = models.CharField(max_length=160)
    trigger = models.CharField(max_length=20, choices=TRIGGERS)
    trigger_params = models.JSONField(default=dict, blank=True)
    criteria = models.JSONField(default=dict, blank=True)
    action = models.CharField(max_length=20, choices=ACTIONS, default=NOTIFY)
    action_params = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)
    nl_prompt = models.TextField(blank=True)
    last_run = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="playbooks")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PlaybookEvent(models.Model):
    playbook = models.ForeignKey(Playbook, on_delete=models.CASCADE,
                                 related_name="events")
    employee = models.ForeignKey(Employee, null=True, blank=True,
                                 on_delete=models.CASCADE,
                                 related_name="playbook_events")
    fired_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=200)
    detail = models.CharField(max_length=400, blank=True)
    acknowledged = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fired_at"]
        #: One event per playbook per employee. A rule that fires every night
        #: until somebody acts is a rule people learn to ignore.
        constraints = [
            models.UniqueConstraint(fields=["playbook", "employee"],
                                    name="one_open_event_per_person"),
        ]

    def __str__(self):
        return self.title
