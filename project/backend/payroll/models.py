"""
Payroll: salary structures, rules, payruns and payslips.

Graded rule #4 — rules execute in sequence order, each result visible to
later rules. Graded rule #5 — warnings surface before validation.
Gross and Net are read from payslip lines, never stored independently.
"""

from decimal import Decimal

from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce

from core.models import Company, TimeStampedModel
from employees.models import Contract, Employee

ZERO = Decimal("0.00")


# ==========================================================================
# Configuration — graded rule #4
# ==========================================================================

class SalaryStructure(TimeStampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="salary_structures")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def rule_count(self):
        return self.rules.filter(active=True).count()

    @property
    def employee_count(self):
        return Employee.objects.filter(
            contracts__salary_structure=self,
            contracts__state=Contract.RUNNING,
        ).distinct().count()

    def ordered_rules(self):
        return self.rules.filter(active=True).order_by("sequence", "id")


class SalaryRule(TimeStampedModel):
    BASIC = "BASIC"
    ALLOWANCE = "ALLOWANCE"
    GROSS = "GROSS"
    DEDUCTION = "DEDUCTION"
    NET = "NET"
    CATEGORIES = [(BASIC, "Basic"), (ALLOWANCE, "Allowance"), (GROSS, "Gross"),
                  (DEDUCTION, "Deduction"), (NET, "Net")]

    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"
    FORMULA = "FORMULA"
    COMPUTATIONS = [(FIXED, "Fixed Amount"),
                    (PERCENTAGE, "Percentage of Wage"),
                    (FORMULA, "Formula / Python Code")]

    structure = models.ForeignKey(SalaryStructure, on_delete=models.CASCADE,
                                  related_name="rules")
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20)
    category = models.CharField(max_length=12, choices=CATEGORIES)
    sequence = models.IntegerField(default=10)

    computation = models.CharField(max_length=12, choices=COMPUTATIONS, default=FIXED)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    percentage = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    percentage_base = models.CharField(
        max_length=20, blank=True,
        help_text="Rule code the percentage applies to. Blank = contract wage.")
    formula = models.TextField(blank=True)
    condition = models.TextField(
        blank=True, help_text="Optional expression; blank means always applies.")

    quantity = models.DecimalField(max_digits=6, decimal_places=2,
                                   default=Decimal("1.00"))
    appears_on_payslip = models.BooleanField(default=True)
    is_employer_cost = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(fields=["structure", "code"],
                                    name="uniq_rule_code_per_structure"),
        ]

    def __str__(self):
        return f"{self.sequence}. {self.name} [{self.code}]"


# ==========================================================================
# Processing
# ==========================================================================

class Payrun(TimeStampedModel):
    DRAFT = "DRAFT"
    COMPUTED = "COMPUTED"
    VALIDATED = "VALIDATED"
    PAID = "PAID"
    STATES = [(DRAFT, "Draft"), (COMPUTED, "Computed"),
              (VALIDATED, "Validated"), (PAID, "Paid")]

    name = models.CharField(max_length=120)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="payruns")
    salary_structure = models.ForeignKey(SalaryStructure, on_delete=models.PROTECT,
                                         related_name="payruns")
    period_start = models.DateField()
    period_end = models.DateField()
    employee_type = models.CharField(max_length=20, blank=True)

    state = models.CharField(max_length=12, choices=STATES, default=DRAFT)
    computed_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="payruns")

    class Meta:
        ordering = ["-period_start"]
        constraints = [
            models.CheckConstraint(condition=Q(period_end__gte=models.F("period_start")),
                                   name="payrun_period_ordered"),
        ]

    def __str__(self):
        return self.name

    # -- aggregates ---------------------------------------------------------

    @property
    def payslip_count(self):
        return self.payslips.count()

    @property
    def warning_count(self):
        return self.warnings.filter(severity=PayslipWarning.WARNING).count()

    @property
    def error_count(self):
        return self.warnings.filter(severity=PayslipWarning.ERROR).count()

    @property
    def total_net(self):
        return sum((p.net for p in self.payslips.all()), ZERO)

    @property
    def total_gross(self):
        return sum((p.gross for p in self.payslips.all()), ZERO)

    # -- state machine (PRD §6) ---------------------------------------------

    @property
    def is_locked(self):
        return self.state == self.PAID

    @property
    def can_compute(self):
        return self.state in (self.DRAFT, self.COMPUTED)

    @property
    def can_validate(self):
        return self.state == self.COMPUTED and self.error_count == 0

    @property
    def can_mark_paid(self):
        return self.state == self.VALIDATED


class Payslip(TimeStampedModel):
    payrun = models.ForeignKey(Payrun, on_delete=models.CASCADE,
                               related_name="payslips")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT,
                                 related_name="payslips")
    contract = models.ForeignKey(Contract, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name="payslips")
    salary_structure = models.ForeignKey(SalaryStructure, on_delete=models.PROTECT,
                                         related_name="payslips")

    period_start = models.DateField()
    period_end = models.DateField()

    worked_days = models.DecimalField(max_digits=6, decimal_places=2, default=ZERO)
    expected_days = models.DecimalField(max_digits=6, decimal_places=2, default=ZERO)
    lop_days = models.DecimalField(max_digits=6, decimal_places=2, default=ZERO)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, default=ZERO)

    state = models.CharField(max_length=12, choices=Payrun.STATES,
                             default=Payrun.DRAFT)
    number = models.CharField(max_length=30, unique=True, blank=True)

    class Meta:
        ordering = ["employee__first_name"]
        constraints = [
            # The duplicate-payslip guard (PRD-4.5.2)
            models.UniqueConstraint(
                fields=["employee", "period_start", "period_end"],
                name="uniq_payslip_per_employee_period"),
        ]

    def __str__(self):
        return f"{self.employee.full_name} — {self.period_start:%b %Y}"

    def save(self, *args, **kwargs):
        if not self.number:
            prefix = f"PAY/{self.period_start:%Y/%m}"
            last = (Payslip.objects.filter(number__startswith=prefix)
                    .order_by("-number").first())
            seq = int(last.number.split("/")[-1]) + 1 if last else 1
            self.number = f"{prefix}/{seq:04d}"
        super().save(*args, **kwargs)

    # -- derived from lines (PRD-4.4.8) -------------------------------------

    def _category_total(self, category):
        """
        Employee-side total for a category.

        Employer contributions are excluded: they are a cost to the company,
        not money the employee receives or forfeits, so they must never move
        gross or net.
        """
        return self.lines.filter(
            category=category, is_employer_cost=False
        ).aggregate(t=Coalesce(Sum("amount"), ZERO))["t"]

    @property
    def basic(self):
        return self._category_total(SalaryRule.BASIC)

    @property
    def allowances(self):
        return self._category_total(SalaryRule.ALLOWANCE)

    @property
    def deductions(self):
        return self._category_total(SalaryRule.DEDUCTION)

    @property
    def gross(self):
        total = self._category_total(SalaryRule.GROSS)
        return total if total else self.basic + self.allowances

    @property
    def net(self):
        total = self._category_total(SalaryRule.NET)
        return total if total else self.gross - self.deductions

    @property
    def employer_cost(self):
        """Total employer contributions — the company-side half of CTC."""
        return self.lines.filter(is_employer_cost=True).aggregate(
            t=Coalesce(Sum("amount"), ZERO))["t"]

    @property
    def ctc(self):
        """Cost to company: what the employee earns plus what we pay on top."""
        return self.gross + self.employer_cost

    @property
    def visible_lines(self):
        """Lines to print. A rule may compute without appearing on the slip."""
        return self.lines.filter(appears_on_payslip=True)

    @property
    def has_warnings(self):
        return self.warnings.exists()


class PayslipLine(models.Model):
    """
    One executed rule. Name/code/category are snapshotted so the payslip stays
    readable if the rule is later edited.
    """

    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE,
                                related_name="lines")
    rule = models.ForeignKey(SalaryRule, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="payslip_lines")

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=20)
    category = models.CharField(max_length=12, choices=SalaryRule.CATEGORIES)
    sequence = models.IntegerField(default=10)

    quantity = models.DecimalField(max_digits=6, decimal_places=2,
                                   default=Decimal("1.00"))
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=ZERO)

    # Snapshotted from the rule alongside name/code/category, so a payslip
    # keeps reading correctly if the rule's flags are changed afterwards.
    is_employer_cost = models.BooleanField(default=False)
    appears_on_payslip = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequence", "id"]
        constraints = [
            # What makes recompute idempotent (PRD-6.1)
            models.UniqueConstraint(fields=["payslip", "code"],
                                    name="uniq_line_code_per_payslip"),
        ]

    def __str__(self):
        return f"{self.code}: {self.amount}"


class PayslipWarning(models.Model):
    """Graded rule #5 — surfaced before validation, regenerated every compute."""

    AC_MISSING = "AC_MISSING"
    DUPLICATE = "DUPLICATE"
    NO_CONTRACT = "NO_CONTRACT"
    NEGATIVE_NET = "NEGATIVE_NET"
    NO_STRUCTURE = "NO_STRUCTURE"
    RULE_ERROR = "RULE_ERROR"
    CODES = [
        (AC_MISSING, "Bank account missing"),
        (DUPLICATE, "Duplicate payslip"),
        (NO_CONTRACT, "No contract for period"),
        (NEGATIVE_NET, "Negative net salary"),
        (NO_STRUCTURE, "No salary structure"),
        (RULE_ERROR, "Salary rule error"),
    ]

    WARNING = "WARNING"
    ERROR = "ERROR"
    SEVERITIES = [(WARNING, "Warning"), (ERROR, "Error")]

    payrun = models.ForeignKey(Payrun, on_delete=models.CASCADE,
                               related_name="warnings")
    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE,
                                null=True, blank=True, related_name="warnings")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE,
                                 null=True, blank=True,
                                 related_name="payroll_warnings")

    code = models.CharField(max_length=20, choices=CODES)
    message = models.CharField(max_length=255)
    severity = models.CharField(max_length=8, choices=SEVERITIES, default=WARNING)

    class Meta:
        ordering = ["severity", "code"]

    def __str__(self):
        return f"[{self.severity}] {self.message}"
