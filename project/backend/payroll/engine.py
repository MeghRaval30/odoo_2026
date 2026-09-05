"""
The salary rule computation engine — graded rule #4.

Rules execute in ascending `sequence`, and each result becomes available to
every later rule through the evaluation context. This is what lets Gross be
defined as BASIC + ALLOWANCE and Net as GROSS - DEDUCTION without either
being hardcoded.

Recompute is idempotent (PRD-6.1): lines are deleted and rewritten, never
appended, so computing three times yields identical totals.
"""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from attendance.models import Attendance
from core.models import Holiday
from employees.models import Contract
from timeoff.models import TimeOffRequest

from .models import Payslip, PayslipLine, PayslipWarning, SalaryRule

ZERO = Decimal("0.00")


def money(value) -> Decimal:
    """Quantise to 2dp with half-up rounding — never float (PRD-7.6)."""
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ==========================================================================
# Sandboxed expression evaluation (PRD-4.4.6)
# ==========================================================================

_FORBIDDEN = ("__", "import", "open(", "exec", "eval", "compile",
              "globals", "locals", "getattr", "setattr", "delattr",
              "subprocess", "os.", "sys.")

_SAFE_BUILTINS = {
    "abs": abs, "min": min, "max": max, "round": round, "sum": sum,
    "len": len, "int": int, "float": float, "bool": bool,
    "Decimal": Decimal,
}


class RuleEvaluationError(Exception):
    pass


def safe_eval(expression: str, context: dict):
    """
    Evaluate a rule expression with builtins stripped and a source allowlist.

    Deliberately conservative: anything that smells like introspection or IO
    is rejected before evaluation rather than sandboxed at runtime.
    """
    source = (expression or "").strip()
    if not source:
        raise RuleEvaluationError("Empty expression")

    lowered = source.lower()
    for token in _FORBIDDEN:
        if token in lowered:
            raise RuleEvaluationError(f"Forbidden token in expression: {token!r}")

    scope = {"__builtins__": _SAFE_BUILTINS, **context}
    try:
        return eval(source, scope, {})  # noqa: S307 — guarded above
    except RuleEvaluationError:
        raise
    except Exception as exc:
        raise RuleEvaluationError(f"{type(exc).__name__}: {exc}") from exc


# ==========================================================================
# Period facts drawn from attendance and leave (PRD-4.6)
# ==========================================================================

def gather_period_facts(employee, contract, period_start, period_end):
    """
    Worked days, expected days, LOP days and overtime for the period.

    This is the integration the problem statement hints at but does not
    require (D-002): attendance and leave genuinely reach the payslip.

    The day window is clamped to the contract's own dates, so an employee who
    joins or leaves mid-period is measured against the days they were actually
    employed. Without that clamp a 20 February joiner was billed a full
    February — the most common real-world payroll case, and one no payroll
    manager would sign off.
    """
    holidays = set(Holiday.objects.filter(
        company=employee.company,
        date__range=(period_start, period_end),
    ).values_list("date", flat=True))

    # The stretch of this period the contract actually covers.
    paid_start = max(period_start, contract.start_date) if contract else period_start
    paid_end = period_end
    if contract and contract.end_date:
        paid_end = min(period_end, contract.end_date)

    schedule = contract.working_schedule if contract else employee.working_schedule
    if schedule:
        full = Decimal(schedule.expected_working_days(
            period_start, period_end, holidays))
        expected = Decimal(schedule.expected_working_days(
            paid_start, paid_end, holidays)) if paid_start <= paid_end else ZERO
    else:
        full = Decimal(_weekdays_between(period_start, period_end, holidays))
        expected = (Decimal(_weekdays_between(paid_start, paid_end, holidays))
                    if paid_start <= paid_end else ZERO)

    sessions = Attendance.objects.filter(
        employee=employee,
        check_in__date__range=(period_start, period_end),
        check_out__isnull=False,
    )
    worked_days = Decimal(
        len({s.check_in.date() for s in sessions
             if s.status != Attendance.ABSENT}))
    overtime = sum((s.overtime_hours for s in sessions), ZERO)

    # Unpaid approved leave becomes Loss of Pay
    lop = ZERO
    unpaid = TimeOffRequest.objects.filter(
        employee=employee,
        state=TimeOffRequest.APPROVED,
        time_off_type__is_paid=False,
        date_from__lte=period_end,
        date_to__gte=period_start,
    ).select_related("time_off_type")
    for req in unpaid:
        lop += _overlap_days(req.date_from, req.date_to,
                             period_start, period_end, req.duration)

    # Fraction of the period the contract covers. 1 for anyone employed
    # throughout, less for a joiner or leaver. Wage-derived rules scale by it.
    proration = (expected / full) if full else Decimal("1")

    return {
        "expected_days": expected,
        "full_period_days": full,
        "worked_days": worked_days,
        "lop_days": money(lop),
        "overtime_hours": money(overtime),
        "proration": proration,
        "paid_from": paid_start,
        "paid_to": paid_end,
        "is_prorated": proration != Decimal("1"),
    }


def _weekdays_between(start, end, holidays):
    count, cursor = 0, start
    while cursor <= end:
        if cursor.weekday() < 5 and cursor not in holidays:
            count += 1
        cursor += timedelta(days=1)
    return count


def _overlap_days(req_from, req_to, period_start, period_end, duration):
    """Portion of a leave request's duration that falls inside the period."""
    lo, hi = max(req_from, period_start), min(req_to, period_end)
    if lo > hi:
        return ZERO
    total_span = (req_to - req_from).days + 1
    overlap_span = (hi - lo).days + 1
    if total_span == overlap_span:
        return Decimal(duration)
    return money(Decimal(duration) * Decimal(overlap_span) / Decimal(total_span))


# ==========================================================================
# Rule evaluation
# ==========================================================================

def evaluate_rule(rule, ctx) -> Decimal:
    if rule.computation == SalaryRule.FIXED:
        return money(rule.amount or ZERO)

    if rule.computation == SalaryRule.PERCENTAGE:
        pct = Decimal(rule.percentage or 0)
        if rule.percentage_base:
            # Already prorated: it derives from an earlier rule's result.
            base = Decimal(ctx["rules"].get(rule.percentage_base, ZERO))
            return money(base * pct / Decimal(100))
        # A percentage of the contract wage is a monthly figure, so it is
        # scaled to the part of the period the contract actually covers.
        base = Decimal(ctx["wage"]) * ctx["proration"]
        return money(base * pct / Decimal(100))

    if rule.computation == SalaryRule.FORMULA:
        result = safe_eval(rule.formula, ctx)
        return money(result)

    raise RuleEvaluationError(f"Unknown computation {rule.computation!r}")


def build_context(payslip, contract, facts):
    categories = defaultdict(lambda: ZERO)
    employer_categories = defaultdict(lambda: ZERO)
    rules_by_code = {}
    return {
        "contract": contract,
        "employee": payslip.employee,
        "payslip": payslip,
        "wage": Decimal(contract.wage) if contract else ZERO,
        "worked_days": facts["worked_days"],
        "expected_days": facts["expected_days"],
        "full_period_days": facts["full_period_days"],
        "lop_days": facts["lop_days"],
        "overtime_hours": facts["overtime_hours"],
        # Fraction of the period the contract covers — 1 for a full month.
        # Exposed so a formula rule can prorate a fixed amount too:
        #   amount * proration
        "proration": facts["proration"],
        "categories": categories,
        # Employer contributions accumulate separately so they never move the
        # employee's gross or net. Exposed to formulas so a rule can reference
        # the employer side if it needs to.
        "employer_categories": employer_categories,
        "rules": rules_by_code,
        "Decimal": Decimal,
    }


@transaction.atomic
def compute_payslip(payslip) -> Payslip:
    """Compute one payslip. Idempotent — safe to call repeatedly."""
    payslip.lines.all().delete()
    payslip.warnings.all().delete()

    contract = payslip.contract
    if contract is None:
        contract = payslip.employee.contract_for_period(
            payslip.period_start, payslip.period_end)
        payslip.contract = contract

    if contract is None:
        _warn(payslip, PayslipWarning.NO_CONTRACT,
              f"{payslip.employee.full_name} has no running contract covering "
              f"{payslip.period_start} – {payslip.period_end}.",
              PayslipWarning.ERROR)
        payslip.save()
        return payslip

    facts = gather_period_facts(payslip.employee, contract,
                                payslip.period_start, payslip.period_end)
    payslip.worked_days = facts["worked_days"]
    payslip.expected_days = facts["expected_days"]
    payslip.lop_days = facts["lop_days"]
    payslip.overtime_hours = facts["overtime_hours"]

    structure = payslip.salary_structure or contract.salary_structure
    if structure is None:
        _warn(payslip, PayslipWarning.NO_STRUCTURE,
              f"Contract {contract.reference} has no salary structure.",
              PayslipWarning.ERROR)
        payslip.save()
        return payslip

    ctx = build_context(payslip, contract, facts)
    lines = []

    for rule in structure.ordered_rules():
        if rule.condition:
            try:
                if not safe_eval(rule.condition, ctx):
                    continue
            except RuleEvaluationError as exc:
                _warn(payslip, PayslipWarning.RULE_ERROR,
                      f"Condition failed on {rule.code}: {exc}")
                continue

        try:
            rate = evaluate_rule(rule, ctx)
        except RuleEvaluationError as exc:
            # A failing rule must not abort the whole run (PRD-4.4.7)
            _warn(payslip, PayslipWarning.RULE_ERROR,
                  f"Rule {rule.code} failed: {exc}")
            continue

        # rate is the per-unit figure and amount is rate x quantity, so the
        # payslip's Quantity/Rate/Amount columns reconcile. Storing the
        # multiplied value in rate made the line read as quantity x (rate x
        # quantity) for any rule with a quantity other than 1.
        quantity = Decimal(rule.quantity or 1)
        amount = money(rate * quantity)

        lines.append(PayslipLine(
            payslip=payslip, rule=rule, name=rule.name, code=rule.code,
            category=rule.category, sequence=rule.sequence,
            quantity=rule.quantity, rate=rate, amount=amount,
            is_employer_cost=rule.is_employer_cost,
            appears_on_payslip=rule.appears_on_payslip,
        ))

        # Every rule's result is visible to later rules by code, employer cost
        # included — an employer PF rule may well want to reference the
        # employee's PF figure.
        ctx["rules"][rule.code] = amount

        if rule.is_employer_cost:
            # Employer contributions are a cost to the company, not money the
            # employee receives or forfeits. Accumulating them into
            # `categories` made an employer-side PF rule categorised DEDUCTION
            # reduce the employee's net pay, which is simply wrong: the flag
            # was stored, serialized and editable in the UI, and nothing read
            # it. They go into a parallel bucket that feeds CTC instead.
            ctx["employer_categories"][rule.category] += amount
        else:
            ctx["categories"][rule.category] += amount

    PayslipLine.objects.bulk_create(lines)
    payslip.save()

    validate_payslip(payslip)
    return payslip


# ==========================================================================
# Validation warnings — graded rule #5
# ==========================================================================

def _warn(payslip, code, message, severity=PayslipWarning.WARNING):
    PayslipWarning.objects.create(
        payrun=payslip.payrun, payslip=payslip, employee=payslip.employee,
        code=code, message=message, severity=severity)


def validate_payslip(payslip):
    """Surface problems before Validate becomes available (PRD-4.5)."""
    employee = payslip.employee

    if not employee.has_bank_details:
        _warn(payslip, PayslipWarning.AC_MISSING,
              f"{employee.full_name} has no bank account on file.")

    duplicate = (Payslip.objects
                 .filter(employee=employee,
                         period_start=payslip.period_start,
                         period_end=payslip.period_end)
                 .exclude(pk=payslip.pk)
                 .exists())
    if duplicate:
        _warn(payslip, PayslipWarning.DUPLICATE,
              f"Another payslip already exists for {employee.full_name} "
              f"covering this period.")

    if payslip.net < ZERO:
        _warn(payslip, PayslipWarning.NEGATIVE_NET,
              f"Net salary is negative ({payslip.net}).",
              PayslipWarning.ERROR)


# ==========================================================================
# Payrun orchestration
# ==========================================================================

@transaction.atomic
def compute_payrun(payrun):
    """Compute every payslip in the run. Idempotent."""
    if payrun.is_locked:
        raise ValueError("A paid payrun is read-only and cannot be recomputed.")

    # Clear only warnings that compute itself regenerates. Warnings raised at
    # payrun creation — an employee skipped because they already had a payslip
    # for the period — record a fact about the run and must survive recompute,
    # otherwise the operator silently loses the record that someone was skipped.
    payrun.warnings.filter(payslip__isnull=True, employee__isnull=True).delete()

    for payslip in payrun.payslips.select_related("employee", "contract"):
        payslip.salary_structure = payrun.salary_structure
        compute_payslip(payslip)

    payrun.state = payrun.COMPUTED
    payrun.computed_at = timezone.now()
    payrun.save(update_fields=["state", "computed_at", "updated_at"])
    return payrun


@transaction.atomic
def create_payrun_payslips(payrun, employees):
    """Create payslip shells for the selected employees (wizard step 2)."""
    created = []
    for employee in employees:
        contract = employee.contract_for_period(
            payrun.period_start, payrun.period_end)

        if Payslip.objects.filter(employee=employee,
                                  period_start=payrun.period_start,
                                  period_end=payrun.period_end).exists():
            PayslipWarning.objects.create(
                payrun=payrun, employee=employee,
                code=PayslipWarning.DUPLICATE,
                message=f"{employee.full_name} already has a payslip for this "
                        f"period and was skipped.")
            continue

        created.append(Payslip.objects.create(
            payrun=payrun, employee=employee, contract=contract,
            salary_structure=payrun.salary_structure,
            period_start=payrun.period_start, period_end=payrun.period_end,
        ))
    return created


def validate_payrun(payrun):
    if not payrun.can_validate:
        raise ValueError(
            f"Cannot validate: state is {payrun.state} with "
            f"{payrun.error_count} blocking error(s).")
    payrun.state = payrun.VALIDATED
    payrun.validated_at = timezone.now()
    payrun.payslips.update(state=payrun.VALIDATED)
    payrun.save(update_fields=["state", "validated_at", "updated_at"])
    return payrun


def mark_payrun_paid(payrun):
    if not payrun.can_mark_paid:
        raise ValueError(f"Cannot mark paid: state is {payrun.state}.")
    payrun.state = payrun.PAID
    payrun.paid_at = timezone.now()
    payrun.payslips.update(state=payrun.PAID)
    payrun.save(update_fields=["state", "paid_at", "updated_at"])
    return payrun
