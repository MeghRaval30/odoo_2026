"""
Importing pay that already happened.

The employee importer answers "who works here". This answers "what did we pay
them before we bought this system", and it is a different problem in three ways
that shape everything below.

**A payslip has to find its person.** An employee row creates a record; a
payslip row must attach to one that already exists. So the first thing this
does is *resolve*, on three keys in descending order of trust -- employee code,
work email, then name -- and a row that cannot find its person does not import.
That is not a failure to be smoothed over. Attaching December's pay to the
wrong Sharma is worse than not importing it.

**A payslip has to find its month.** Payroll sheets write the period in the
header, in a column called "Month", as a pair of dates, or not at all. Whatever
form it takes it has to become a start and an end, because a payslip that is
not filed against a period cannot be found by the register, the dashboard or
the employee themselves.

**A payslip is arithmetic, and the arithmetic can be checked.** This is the
part worth the trouble. Every legacy payroll sheet states a gross and a net
alongside the components that produce them. Those three numbers are related by
a law -- earnings sum to gross, gross less deductions is net -- so the sheet
carries its own proof. `reconcile` below checks it row by row.

That check earns its place. A migration that silently drops one allowance
column still produces a plausible-looking import: every payslip has numbers on
it and nobody notices for a year. Here the sum stops matching the stated net
and the row is flagged before it is written, naming the rupee difference. It is
the same instinct as the payrun's pre-finalisation warnings, applied to data
arriving from outside rather than data computed inside.

## What a commit writes

Rows are grouped by period, and each period becomes one `Payrun` in state
`PAID` -- historical pay is, by definition, already paid -- carrying one
`Payslip` per employee and one `PayslipLine` per component the sheet had a
value for. Nothing is recomputed. The engine is deliberately not run: these
figures are what the previous system actually paid, and the point of keeping
them is that they are the record, not our opinion of what the record should
have been.

Because the lines carry a `category`, an imported payslip's totals derive
exactly the way a computed one's do. It appears in the register, on the
dashboard and under the employee's own "My Payslips" with no special-casing
anywhere -- which is the test of whether this was imported properly.
"""

import calendar
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction

from employees.models import Employee
from payroll.models import Payrun, Payslip, PayslipLine, SalaryStructure

from . import payslip_schema as ps
from .profiler import is_blank, parse_date_value, strip_money

ZERO = Decimal("0.00")

#: How far a stated total may sit from the computed one before it is worth
#: saying out loud. One rupee absorbs the rounding every legacy system does
#: differently; anything above it is a real disagreement about the money.
TOLERANCE = Decimal("1.00")


# ==========================================================================
# Reading one cell
# ==========================================================================

def money(value):
    """A cell as rupees, or None. Accepts '1,08,000.00', 'Rs. 45000', '(500)'."""
    if is_blank(value):
        return None
    raw = str(value).strip()
    # Accounting parentheses. `strip_money` does not know them, and a recovery
    # written "(500)" is a real negative rather than an unreadable cell.
    negative = raw.startswith("(") and raw.endswith(")")
    if negative:
        raw = raw[1:-1].strip()
    cleaned = strip_money(raw)
    if cleaned is None:
        return None
    try:
        amount = Decimal(str(cleaned)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None
    return -amount if negative else amount


def number(value):
    """A cell as a plain quantity -- days, hours. None when it is not one."""
    amount = money(value)
    return None if amount is None else amount


_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})

#: 'Dec-2025', 'December 2025', '12/2025', '2025-12', 'Dec 25'.
_MONTH_YEAR = re.compile(
    r"^\s*(?P<a>[A-Za-z]+|\d{1,4})\s*[-/\s,]+\s*(?P<b>\d{2,4})\s*$")


def parse_month(value):
    """
    A pay-month cell as (year, month), or None.

    Written out rather than handed to a date parser because the ambiguous case
    here has a right answer a general parser cannot know: '12/2025' is December
    2025, never the twelfth of some day in 2025. A pay month has no day, and
    inventing one is how a period ends up off by a month at a year boundary.
    """
    if is_blank(value):
        return None
    raw = str(value).strip()

    # A real date in the cell -- take its month and drop the day.
    parsed = parse_date_value(raw)
    if parsed:
        return parsed.year, parsed.month

    match = _MONTH_YEAR.match(raw)
    if not match:
        return None
    a, b = match.group("a"), match.group("b")

    year = int(b)
    if year < 100:                       # 'Dec 25'
        year += 2000 if year < 70 else 1900

    if a.isdigit():
        month = int(a)
        # '2025-12' arrives with the parts the other way round.
        if month > 12 and 1 <= year <= 12:
            month, year = year, month
        elif len(a) == 4 and 1 <= int(b) <= 12:
            year, month = int(a), int(b)
    else:
        month = _MONTHS.get(a.lower()[:9]) or _MONTHS.get(a.lower()[:3])

    if not month or not 1 <= month <= 12 or not 1900 <= year <= 2200:
        return None
    return year, month


def month_bounds(year, month):
    return (date(year, month, 1),
            date(year, month, calendar.monthrange(year, month)[1]))


# ==========================================================================
# The plan
# ==========================================================================

def build_plan(table, profiles):
    """
    Decide what each column is, and say why.

    Rules only. Unlike the employee importer this never asks the language
    model, and that is a deliberate limit rather than an omission: payroll
    column headers are a small, standardised, heavily abbreviated vocabulary --
    'PF', 'PT', 'HRA', 'LOP' -- which is exactly the case a dictionary settles
    outright and a 7B model gets confidently wrong. The synonym table in
    `payslip_schema` reads real sheets on its own, so there is nothing left for
    a model to add and no latency worth paying.
    """
    columns = []
    for profile in profiles:
        candidates = ps.match_header(profile["header"], profile)
        top = candidates[0] if candidates else None
        chosen = top["field"] if top and top["confidence"] >= 0.5 else None
        columns.append({
            "index": profile["index"],
            "header": profile["header"],
            "field": chosen,
            "confidence": top["confidence"] if top else 0.0,
            "reason": top["reason"] if top else "no field matched this header",
            "candidates": candidates,
            "evidence": profile.get("evidence", ""),
            "best_kind": profile.get("best_kind", "text"),
        })

    _enforce_uniqueness(columns)
    return {
        "columns": columns,
        "gaps": ps.missing_required(columns),
        "period_override": None,
    }


def _enforce_uniqueness(columns):
    """
    One field, one column.

    Payroll sheets repeat themselves constantly -- 'Total Deductions' sitting
    beside 'Other Deductions', two columns both reading 'Amount'. Whichever
    match is weaker loses its field and says so, because summing the same
    component twice is a silent doubling of somebody's deduction.
    """
    best = {}
    for column in columns:
        field = column["field"]
        if not field:
            continue
        held = best.get(field)
        if held is None or column["confidence"] > held["confidence"]:
            if held is not None:
                held["field"] = None
                held["reason"] = ("column %d matched %s more strongly"
                                  % (column["index"] + 1,
                                     ps.FIELDS_BY_KEY[field]["label"]))
            best[field] = column
        else:
            column["field"] = None
            column["reason"] = ("column %d matched %s more strongly"
                                % (held["index"] + 1,
                                   ps.FIELDS_BY_KEY[field]["label"]))


# ==========================================================================
# Rows
# ==========================================================================

def build_records(table, plan):
    """Each sheet row as a dict of target field -> raw cell."""
    mapping = {c["index"]: c["field"] for c in plan.get("columns", [])
               if c.get("field")}
    records = []
    for row_index, row in enumerate(table.rows):
        record = {"_row": row_index}
        for column_index, field in mapping.items():
            if column_index < len(row):
                value = row[column_index]
                if not is_blank(value):
                    record[field] = str(value).strip()
        records.append(record)
    return records


def _employee_index(company):
    """
    Every employee, indexed the three ways a payroll sheet might name them.

    Built once per run rather than queried per row: a 500-row sheet against a
    240-person roster is 500 queries otherwise, and the whole index is a few
    thousand short strings.
    """
    by_code, by_email, by_name = {}, {}, {}
    query = Employee.objects.all()
    if company is not None:
        query = query.filter(company=company)
    for employee in query.only("id", "employee_code", "work_email",
                               "first_name", "last_name"):
        if employee.employee_code:
            by_code[employee.employee_code.strip().lower()] = employee
        if employee.work_email:
            by_email[employee.work_email.strip().lower()] = employee
        name = employee.full_name.strip().lower()
        # A name that is not unique is not an identifier. Both rows are kept
        # out of the index rather than the second overwriting the first.
        by_name[name] = None if name in by_name else employee
    return by_code, by_email, by_name


def resolve_employee(record, index):
    """
    Which person this row is about, and how sure we are.

    Returns (employee, how, note). `how` is one of code / email / name / None
    and is shown in the preview, because "matched by name" is a materially
    weaker claim than "matched by employee code" and the operator should be
    able to see which rows rest on it.
    """
    by_code, by_email, by_name = index

    code = (record.get("employee_code") or "").strip().lower()
    if code and code in by_code:
        return by_code[code], "code", "employee code %s" % record["employee_code"]

    email = (record.get("work_email") or "").strip().lower()
    if email and email in by_email:
        return by_email[email], "email", "work email %s" % record["work_email"]

    name = (record.get("full_name") or "").strip().lower()
    if name:
        found = by_name.get(name)
        if found:
            return found, "name", "name %s" % record["full_name"]
        if name in by_name:
            return None, None, ("more than one employee is called %s"
                                % record["full_name"])

    return None, None, "no employee matches this row"


def resolve_period(record, override=None):
    """
    The month this row covers, as (start, end), or (None, None) with a reason.

    `override` is the operator's answer for a sheet that names its month only
    in a filename or a title row -- 'Salary Statement December 2025' -- which
    is common enough that refusing those files outright would be unhelpful.
    """
    start = parse_date_value(record.get("period_start")) if record.get("period_start") else None
    end = parse_date_value(record.get("period_end")) if record.get("period_end") else None
    if start and end:
        return start, end, ""
    if start and not end:
        return month_bounds(start.year, start.month) + ("",)

    parsed = parse_month(record.get("period_month"))
    if parsed:
        return month_bounds(*parsed) + ("",)

    if override:
        parsed = parse_month(override)
        if parsed:
            return month_bounds(*parsed) + ("",)

    return None, None, "this row does not say which month it covers"


# ==========================================================================
# The arithmetic
# ==========================================================================

def components(record):
    """The money components present on this row, as {field_key: Decimal}."""
    out = {}
    for key in ps.COMPONENT_KEYS:
        amount = money(record.get(key))
        if amount is not None:
            out[key] = amount
    return out


def reconcile(record, parts):
    """
    Do the components add up to what the sheet says it paid?

    Returns a dict the preview renders directly. `ok` is True when the sheet
    states a total and it agrees, False when it disagrees, and None when the
    sheet states no total at all -- three genuinely different situations that
    an is-it-valid boolean would flatten into two.
    """
    earnings = sum((v for k, v in parts.items() if k in ps.EARNING_KEYS), ZERO)
    deductions = sum((v for k, v in parts.items() if k in ps.DEDUCTION_KEYS), ZERO)
    computed_net = earnings - deductions

    stated_gross = money(record.get("gross"))
    stated_net = money(record.get("net"))
    stated_deductions = money(record.get("total_deductions"))

    result = {
        "earnings": earnings,
        "deductions": deductions,
        "computed_gross": earnings,
        "computed_net": computed_net,
        "stated_gross": stated_gross,
        "stated_net": stated_net,
        "stated_deductions": stated_deductions,
        "gross_delta": None,
        "net_delta": None,
        "deductions_delta": None,
        "ok": None,
        "message": "",
    }

    checks = []
    if stated_gross is not None:
        result["gross_delta"] = earnings - stated_gross
        checks.append(("gross", result["gross_delta"]))
    if stated_net is not None:
        result["net_delta"] = computed_net - stated_net
        checks.append(("net", result["net_delta"]))
    if stated_deductions is not None:
        result["deductions_delta"] = deductions - stated_deductions
        checks.append(("total deductions", result["deductions_delta"]))

    if not checks:
        result["message"] = "the sheet states no total, so there is nothing to check against"
        return result

    off = [(what, delta) for what, delta in checks if abs(delta) > TOLERANCE]
    if not off:
        result["ok"] = True
        result["message"] = "components add up to the stated %s" % (
            " and ".join(w for w, _ in checks))
        return result

    result["ok"] = False
    result["message"] = "; ".join(
        "the components come to %s more than the stated %s" % (delta, what)
        if delta > 0 else
        "the components come to %s less than the stated %s" % (-delta, what)
        for what, delta in off)
    return result


# ==========================================================================
# The single path: preview and commit are the same walk
# ==========================================================================

def _blocking(reason):
    return {"severity": "error", "reason": reason}


def evaluate(table, plan, company, period_override=None):
    """
    Walk every row and decide what would happen to it. Writes nothing.

    Preview and commit share this deliberately. The alternative -- a preview
    that estimates and a commit that decides -- is a preview nobody can trust,
    and the one thing a migration screen has to earn is the operator's belief
    that what they approved is what will be written.
    """
    records = build_records(table, plan)
    index = _employee_index(company)
    override = period_override or plan.get("period_override")

    rows, seen = [], {}
    for record in records:
        employee, how, note = resolve_employee(record, index)
        start, end, period_note = resolve_period(record, override)
        parts = components(record)
        check = reconcile(record, parts)

        problems, warnings = [], []

        if employee is None:
            problems.append(note)
        if start is None:
            problems.append(period_note)
        if not parts:
            problems.append("no pay components on this row")

        if employee is not None and start is not None:
            key = (employee.id, start, end)
            if key in seen:
                problems.append("the same person and month appear on row %d"
                                % (seen[key] + 1))
            else:
                seen[key] = record["_row"]
                if Payslip.objects.filter(employee=employee, period_start=start,
                                          period_end=end).exists():
                    problems.append(
                        "%s already has a payslip for %s in this system"
                        % (employee.full_name, start.strftime("%B %Y")))

        if how == "name":
            warnings.append("matched on name alone; no code or email on this row")
        if check["ok"] is False:
            warnings.append(check["message"])
        if check["ok"] is None and parts:
            warnings.append(check["message"])

        rows.append({
            "row": record["_row"],
            "employee_id": employee.id if employee else None,
            "employee_name": employee.full_name if employee else
                             (record.get("full_name") or record.get("work_email")
                              or record.get("employee_code") or "(unidentified)"),
            "matched_by": how,
            "match_note": note,
            "period_start": start,
            "period_end": end,
            "period_label": start.strftime("%B %Y") if start else "",
            "components": parts,
            "check": check,
            "worked_days": number(record.get("worked_days")),
            "expected_days": number(record.get("expected_days")),
            "lop_days": number(record.get("lop_days")),
            "overtime_hours": number(record.get("overtime_hours")),
            "problems": problems,
            "warnings": warnings,
            "importable": not problems,
        })

    return rows


def summarise(rows):
    """Counts the screen puts above the preview, and the demo says out loud."""
    importable = [r for r in rows if r["importable"]]
    periods = sorted({r["period_label"] for r in importable if r["period_label"]})
    return {
        "rows": len(rows),
        "importable": len(importable),
        "blocked": len(rows) - len(importable),
        "warnings": sum(1 for r in rows if r["warnings"]),
        "periods": periods,
        "period_count": len(periods),
        "matched_by_code": sum(1 for r in importable if r["matched_by"] == "code"),
        "matched_by_email": sum(1 for r in importable if r["matched_by"] == "email"),
        "matched_by_name": sum(1 for r in importable if r["matched_by"] == "name"),
        "reconciled": sum(1 for r in importable if r["check"]["ok"] is True),
        "unreconciled": sum(1 for r in importable if r["check"]["ok"] is False),
        "unchecked": sum(1 for r in importable if r["check"]["ok"] is None),
        "total_net": sum((r["check"]["computed_net"] for r in importable), ZERO),
    }


@transaction.atomic
def commit(rows, company, actor=None, structure=None):
    """
    Write the importable rows as real payslips.

    One payrun per period, in `PAID`. Historical pay is already paid, and a
    state that says otherwise would put months of settled money back into the
    payroll operator's queue as though it were waiting for them.

    Atomic on purpose. A half-written month is the one outcome with no good
    recovery: the operator cannot re-run it without tripping the duplicate
    guard on the rows that did land, and cannot tell from the screen which
    those were.
    """
    if structure is None:
        structure = SalaryStructure.objects.filter(active=True).order_by("id").first()
    if structure is None:
        raise ValueError("There is no salary structure to file these payslips against.")

    importable = [r for r in rows if r["importable"]]
    by_period = {}
    for row in importable:
        by_period.setdefault((row["period_start"], row["period_end"]), []).append(row)

    payruns, payslips, lines = [], 0, 0

    for (start, end), group in sorted(by_period.items()):
        payrun = Payrun.objects.filter(
            company=company, period_start=start, period_end=end,
            name__startswith="Imported").first()
        if payrun is None:
            payrun = Payrun.objects.create(
                company=company,
                salary_structure=structure,
                name="Imported - %s" % start.strftime("%B %Y"),
                period_start=start,
                period_end=end,
                state=Payrun.PAID,
                created_by=actor if (actor and actor.is_authenticated) else None,
            )
        payruns.append(payrun)

        for row in group:
            payslip = Payslip.objects.create(
                payrun=payrun,
                employee_id=row["employee_id"],
                salary_structure=structure,
                period_start=start,
                period_end=end,
                state=Payrun.PAID,
                worked_days=row["worked_days"] or ZERO,
                expected_days=row["expected_days"] or ZERO,
                lop_days=row["lop_days"] or ZERO,
                overtime_hours=row["overtime_hours"] or ZERO,
            )
            payslips += 1

            for key, amount in row["components"].items():
                field = ps.FIELDS_BY_KEY[key]
                PayslipLine.objects.create(
                    payslip=payslip,
                    rule=None,
                    name=field["label"],
                    code=field["code"],
                    category=field["category"],
                    sequence=field["sequence"],
                    quantity=Decimal("1.00"),
                    rate=amount,
                    amount=amount,
                    is_employer_cost=False,
                    appears_on_payslip=True,
                )
                lines += 1

    return {
        "payruns": len(payruns),
        "payrun_names": [p.name for p in payruns],
        "payslips": payslips,
        "lines": lines,
    }
