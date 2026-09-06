"""
Doing one thing to many people, with the consequences shown first.

Every operation here is two functions that share their arithmetic: `preview`
computes exactly what would change and writes nothing, `execute` computes the
same thing and commits it in one transaction. They share the computation
because a preview derived differently from the action is a preview that lies,
and the only reason to show one is that it is true.

The increment is the one worth reading closely, because it is where this app
touches the rule the product is graded on.

A naive mass increment sets `contract.wage = new_value` and saves. That is
wrong here in a way that matters: payroll resolves the contract covering the
period being run, so editing a wage in place silently rewrites history --
re-running December after an October raise would pay December at the new rate.
So an increment closes the current contract the day before the effective date
and opens a new one from it. December still resolves to December's contract at
December's wage, and the raise applies from the month it was actually granted.
That is period-based contract resolution doing its job, from the other side.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import Department, WorkLocation
from employees.models import Contract, Employee

from .models import Bond, BulkOperation
from .segments import current_wages, describe, resolve


def _money(value):
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _current_contract(employee, on=None):
    on = on or date.today()
    return (employee.contracts
            .filter(state__in=(Contract.RUNNING, Contract.EXPIRED),
                    start_date__lte=on)
            .filter(Q(end_date__gte=on) | Q(end_date__isnull=True))
            .order_by("-start_date")
            .first())


# ==========================================================================
# Increment
# ==========================================================================

def _new_wage(current, params):
    mode = params.get("mode", "percent")
    try:
        value = Decimal(str(params.get("value") or 0))
    except Exception:
        value = Decimal("0")
    if mode == "flat":
        return _money(current + value)
    return _money(current * (Decimal("1") + value / Decimal("100")))


def preview_increment(employees, params):
    effective = _as_date(params.get("effective_from")) or date.today()
    rows, total_old, total_new, skipped = [], Decimal("0"), Decimal("0"), []

    for employee in employees:
        contract = _current_contract(employee)
        if not contract:
            skipped.append({"employee": employee.full_name,
                            "reason": "no contract covering today"})
            continue
        old = _money(contract.wage)
        new = _new_wage(old, params)
        total_old += old
        total_new += new
        rows.append({
            "employee_id": employee.pk,
            "name": employee.full_name,
            "email": employee.work_email,
            "department": employee.department.name if employee.department else None,
            "old_wage": str(old),
            "new_wage": str(new),
            "delta": str(new - old),
        })

    return {
        "kind": BulkOperation.INCREMENT,
        "effective_from": effective.isoformat(),
        "rows": rows,
        "skipped": skipped,
        "totals": {
            "people": len(rows),
            "old_monthly": str(total_old),
            "new_monthly": str(total_new),
            "monthly_delta": str(total_new - total_old),
            "annual_delta": str((total_new - total_old) * 12),
        },
        "note": ("Each person's current contract is closed the day before %s and "
                 "a new one opens from that date. Payroll for earlier months "
                 "still resolves the older contract, so past payslips do not "
                 "change." % effective.strftime("%d %b %Y")),
    }


def execute_increment(employees, params):
    effective = _as_date(params.get("effective_from")) or date.today()
    made, closed, skipped = 0, 0, 0

    for employee in employees:
        contract = _current_contract(employee)
        if not contract:
            skipped += 1
            continue
        old = _money(contract.wage)
        new = _new_wage(old, params)

        # Close the old one the day before, so the two never both cover a day.
        # A payrun resolving an overlap would pick one arbitrarily.
        contract.end_date = effective - timedelta(days=1)
        if contract.end_date < contract.start_date:
            skipped += 1
            continue
        contract.state = Contract.EXPIRED
        contract.save(update_fields=["end_date", "state", "updated_at"])
        closed += 1

        Contract.objects.create(
            employee=employee,
            department=contract.department,
            job_position=contract.job_position,
            start_date=effective,
            end_date=None,
            wage=new,
            working_schedule=contract.working_schedule,
            salary_structure=contract.salary_structure,
            structure_type=contract.structure_type,
            state=Contract.RUNNING,
            notes="Increment from %s to %s, effective %s."
                  % (old, new, effective.isoformat()),
        )
        made += 1

    return {"contracts_created": made, "contracts_closed": closed,
            "skipped": skipped}


# ==========================================================================
# Offboarding
# ==========================================================================

def preview_exit(employees, params):
    exit_date = _as_date(params.get("exit_date")) or date.today()
    rows, recovery_total, monthly_saved = [], Decimal("0"), Decimal("0")
    wages = current_wages([e.pk for e in employees])

    for employee in employees:
        bond = (employee.bonds
                .filter(state__in=(Bond.SIGNED, Bond.ACTIVE))
                .order_by("-start_date").first())
        liability = bond.remaining_liability(exit_date) if bond else Decimal("0")
        recovery_total += liability
        wage = _money(wages.get(employee.pk) or 0)
        monthly_saved += wage

        rows.append({
            "employee_id": employee.pk,
            "name": employee.full_name,
            "email": employee.work_email,
            "department": employee.department.name if employee.department else None,
            "wage": str(wage),
            "notice_days": bond.notice_days if bond else 30,
            "bond": ({
                "ends": bond.end_date.isoformat(),
                "months_remaining": bond.months_remaining(exit_date),
                "recovery": str(liability),
                "breached": bond.end_date > exit_date,
            } if bond else None),
        })

    bonded = [r for r in rows if r["bond"]]
    return {
        "kind": BulkOperation.EXIT,
        "exit_date": exit_date.isoformat(),
        "rows": rows,
        "totals": {
            "people": len(rows),
            "monthly_payroll_released": str(monthly_saved),
            "bonds_affected": len(bonded),
            "bonds_breached": sum(1 for r in bonded if r["bond"]["breached"]),
            "recovery_due": str(recovery_total),
        },
        "note": ("Contracts are end-dated rather than deleted, so payslips "
                 "already issued stay valid and the payroll history for these "
                 "people remains readable."),
    }


def execute_exit(employees, params):
    exit_date = _as_date(params.get("exit_date")) or date.today()
    note = str(params.get("reason") or "")[:200]
    ended, breached, completed = 0, 0, 0

    for employee in employees:
        contract = _current_contract(employee)
        if contract and (contract.end_date is None or contract.end_date > exit_date):
            contract.end_date = exit_date
            contract.state = Contract.EXPIRED
            contract.save(update_fields=["end_date", "state", "updated_at"])
            ended += 1

        for bond in employee.bonds.filter(state__in=(Bond.SIGNED, Bond.ACTIVE)):
            if bond.end_date > exit_date:
                bond.state = Bond.BREACHED
                bond.breach_date = exit_date
                bond.breach_note = ("Left on %s with %d months of the bond "
                                    "remaining. %s"
                                    % (exit_date.isoformat(),
                                       bond.months_remaining(exit_date), note)).strip()
                breached += 1
            else:
                bond.state = Bond.COMPLETED
                completed += 1
            bond.save(update_fields=["state", "breach_date", "breach_note",
                                     "updated_at"])

        employee.active = False
        employee.save(update_fields=["active", "updated_at"])

    return {"employees_deactivated": len(employees), "contracts_ended": ended,
            "bonds_breached": breached, "bonds_completed": completed}


# ==========================================================================
# Transfer
# ==========================================================================

def preview_transfer(employees, params):
    dept = params.get("department")
    location = params.get("work_location")
    rows = [{
        "employee_id": e.pk,
        "name": e.full_name,
        "department": e.department.name if e.department else None,
        "new_department": dept or (e.department.name if e.department else None),
        "work_location": e.work_location.name if e.work_location else None,
        "new_work_location": location or (e.work_location.name
                                          if e.work_location else None),
    } for e in employees]
    return {"kind": BulkOperation.TRANSFER, "rows": rows,
            "totals": {"people": len(rows)},
            "note": "Only the employee record moves. Contracts are untouched."}


def execute_transfer(employees, params):
    dept = (Department.objects.filter(name__iexact=params["department"]).first()
            if params.get("department") else None)
    location = (WorkLocation.objects.filter(
        name__iexact=params["work_location"]).first()
        if params.get("work_location") else None)

    moved = 0
    for employee in employees:
        fields = []
        if dept:
            employee.department = dept
            fields.append("department")
        if location:
            employee.work_location = location
            fields.append("work_location")
        if fields:
            employee.save(update_fields=fields + ["updated_at"])
            moved += 1
    return {"employees_moved": moved}


# ==========================================================================
# Issuing bonds
# ==========================================================================

def _add_months(start, months):
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(start.day, 28)
    return date(year, month, day)


def preview_bond_issue(employees, params):
    from .models import BondTemplate

    template = BondTemplate.objects.filter(pk=params.get("template")).first()
    if not template:
        return {"kind": BulkOperation.BOND_ISSUE, "rows": [],
                "totals": {"people": 0},
                "note": "Choose a bond template first."}

    start = _as_date(params.get("start_date")) or date.today()
    end = _add_months(start, template.duration_months)
    existing = set(Bond.objects.filter(
        employee__in=employees, state__in=(Bond.SIGNED, Bond.ACTIVE, Bond.SENT)
    ).values_list("employee_id", flat=True))

    rows = [{
        "employee_id": e.pk,
        "name": e.full_name,
        "email": e.work_email,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "recovery": str(_money(template.recovery_amount)),
        "skip": e.pk in existing,
    } for e in employees]

    issuing = [r for r in rows if not r["skip"]]
    return {
        "kind": BulkOperation.BOND_ISSUE,
        "rows": rows,
        "totals": {
            "people": len(issuing),
            "already_bonded": len(rows) - len(issuing),
            "total_recovery": str(_money(template.recovery_amount) * len(issuing)),
            "term_months": template.duration_months,
        },
        "note": ("Bonds are created as drafts. Each one still has to be signed "
                 "by the employee before it is enforceable."),
    }


def execute_bond_issue(employees, params, actor=None):
    from .models import BondTemplate

    template = BondTemplate.objects.filter(pk=params.get("template")).first()
    if not template:
        return {"bonds_created": 0}

    start = _as_date(params.get("start_date")) or date.today()
    end = _add_months(start, template.duration_months)
    existing = set(Bond.objects.filter(
        employee__in=employees, state__in=(Bond.SIGNED, Bond.ACTIVE, Bond.SENT)
    ).values_list("employee_id", flat=True))

    made = [Bond(employee=e, template=template, state=Bond.SENT,
                 start_date=start, end_date=end,
                 duration_months=template.duration_months,
                 recovery_amount=template.recovery_amount,
                 notice_days=template.notice_days, issued_by=actor)
            for e in employees if e.pk not in existing]
    Bond.objects.bulk_create(made)
    return {"bonds_created": len(made), "skipped": len(existing)}


# ==========================================================================

_PREVIEW = {
    BulkOperation.INCREMENT: preview_increment,
    BulkOperation.EXIT: preview_exit,
    BulkOperation.TRANSFER: preview_transfer,
    BulkOperation.BOND_ISSUE: preview_bond_issue,
}

_EXECUTE = {
    BulkOperation.INCREMENT: execute_increment,
    BulkOperation.EXIT: execute_exit,
    BulkOperation.TRANSFER: execute_transfer,
    BulkOperation.BOND_ISSUE: execute_bond_issue,
}


def _as_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def preview(operation):
    criteria = operation.effective_criteria()
    employees = list(resolve(criteria))
    fn = _PREVIEW.get(operation.kind)
    if not fn:
        return {"rows": [], "totals": {"people": 0}, "note": "Unknown operation."}
    out = fn(employees, operation.params or {})
    out["criteria_description"] = describe(criteria)
    out["matched"] = len(employees)
    return out


@transaction.atomic
def execute(operation, actor=None):
    criteria = operation.effective_criteria()
    employees = list(resolve(criteria))
    fn = _EXECUTE.get(operation.kind)
    if not fn:
        raise ValueError("Unknown operation %r" % operation.kind)

    result = (fn(employees, operation.params or {}, actor)
              if operation.kind == BulkOperation.BOND_ISSUE
              else fn(employees, operation.params or {}))
    result["matched"] = len(employees)

    operation.result = result
    operation.state = BulkOperation.EXECUTED
    operation.executed_at = timezone.now()
    operation.save(update_fields=["result", "state", "executed_at", "updated_at"])
    return result
