"""
Turning criteria into people.

One function does the work, and every mass operation, playbook and preview in
this app goes through it. That is deliberate: the number a mass increment
previews and the number a segment screen displays have to be the same number,
and the only way to guarantee that is for there to be one query.

Wage is the awkward one. It does not live on the employee -- it lives on the
contract that covers today, which is the same period resolution the payroll
engine does. So filtering by wage means resolving contracts, and this module
does it the same way `Employee.contract_for_period` does rather than inventing
a second answer.
"""

from datetime import date, timedelta

from django.db.models import Q

from employees.models import Contract, Employee

#: Every key a criteria object may carry. Anything else is dropped, loudly --
#: the natural-language compiler validates against this set, so a model that
#: invents `salary_band` gets it removed and the operator is told.
CRITERIA_KEYS = {
    "departments", "job_positions", "locations", "employee_types",
    "wage_min", "wage_max", "joined_before", "joined_after",
    "tenure_months_min", "tenure_months_max", "active", "has_bond",
    "manager_email", "missing_bank_account",
}


def _as_date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _months_ago(months):
    today = date.today()
    year = today.year + (today.month - 1 - months) // 12
    month = (today.month - 1 - months) % 12 + 1
    day = min(today.day, 28)
    return date(year, month, day)


def current_wages(employee_ids=None):
    """
    Wage per employee, from the contract covering today.

    Resolved in one pass rather than per employee -- a segment over four
    hundred people should not issue four hundred queries, and the tenure and
    wage filters both need this.
    """
    today = date.today()
    qs = (Contract.objects
          .filter(state__in=(Contract.RUNNING, Contract.EXPIRED),
                  start_date__lte=today)
          .filter(Q(end_date__gte=today) | Q(end_date__isnull=True))
          .order_by("employee_id", "-start_date")
          .values_list("employee_id", "wage"))
    if employee_ids is not None:
        qs = qs.filter(employee_id__in=employee_ids)

    out = {}
    for employee_id, wage in qs:
        # Ordered newest first, so the first row per employee wins and the
        # rest are older contracts for the same person.
        out.setdefault(employee_id, wage)
    return out


def resolve(criteria):
    """Return the Employee queryset a criteria object describes."""
    criteria = criteria or {}
    qs = Employee.objects.select_related("department", "job_position",
                                         "work_location", "company")

    active = criteria.get("active")
    qs = qs.filter(active=True if active is None else bool(active))

    if criteria.get("departments"):
        qs = qs.filter(department__name__in=criteria["departments"])
    if criteria.get("job_positions"):
        qs = qs.filter(job_position__name__in=criteria["job_positions"])
    if criteria.get("locations"):
        qs = qs.filter(work_location__name__in=criteria["locations"])
    if criteria.get("employee_types"):
        qs = qs.filter(employee_type__in=criteria["employee_types"])
    if criteria.get("manager_email"):
        qs = qs.filter(manager__work_email__iexact=criteria["manager_email"])
    if criteria.get("missing_bank_account"):
        qs = qs.filter(Q(bank_account_number__isnull=True) |
                       Q(bank_account_number=""))

    joined_before = _as_date(criteria.get("joined_before"))
    if joined_before:
        qs = qs.filter(date_of_joining__lt=joined_before)
    joined_after = _as_date(criteria.get("joined_after"))
    if joined_after:
        qs = qs.filter(date_of_joining__gt=joined_after)

    # Tenure is expressed in months because that is how people say it, and
    # converted to a joining-date bound because that is what the database can
    # index. "At least six months here" is "joined before six months ago".
    if criteria.get("tenure_months_min") is not None:
        qs = qs.filter(date_of_joining__lte=_months_ago(
            int(criteria["tenure_months_min"])))
    if criteria.get("tenure_months_max") is not None:
        qs = qs.filter(date_of_joining__gte=_months_ago(
            int(criteria["tenure_months_max"])))

    if criteria.get("has_bond") is not None:
        from .models import Bond
        bonded = Bond.objects.filter(
            state__in=(Bond.SIGNED, Bond.ACTIVE)).values_list("employee_id", flat=True)
        qs = (qs.filter(pk__in=bonded) if criteria["has_bond"]
              else qs.exclude(pk__in=bonded))

    wage_min = criteria.get("wage_min")
    wage_max = criteria.get("wage_max")
    if wage_min is not None or wage_max is not None:
        wages = current_wages()
        keep = []
        for employee_id, wage in wages.items():
            if wage_min is not None and wage < float(wage_min):
                continue
            if wage_max is not None and wage > float(wage_max):
                continue
            keep.append(employee_id)
        qs = qs.filter(pk__in=keep)

    return qs.distinct()


def describe(criteria):
    """The criteria as an English sentence, for a rule card and an audit line."""
    criteria = criteria or {}
    parts = []
    if criteria.get("departments"):
        parts.append("in " + " or ".join(criteria["departments"]))
    if criteria.get("job_positions"):
        parts.append("working as " + " or ".join(criteria["job_positions"]))
    if criteria.get("locations"):
        parts.append("based at " + " or ".join(criteria["locations"]))
    if criteria.get("employee_types"):
        parts.append("employed " + " or ".join(
            t.replace("_", " ").lower() for t in criteria["employee_types"]))
    if criteria.get("joined_before"):
        parts.append("who joined before %s" % criteria["joined_before"])
    if criteria.get("joined_after"):
        parts.append("who joined after %s" % criteria["joined_after"])
    if criteria.get("tenure_months_min") is not None:
        parts.append("with at least %s months here" % criteria["tenure_months_min"])
    if criteria.get("tenure_months_max") is not None:
        parts.append("with under %s months here" % criteria["tenure_months_max"])
    if criteria.get("wage_min") is not None:
        parts.append("earning at least %s" % _money(criteria["wage_min"]))
    if criteria.get("wage_max") is not None:
        parts.append("earning under %s" % _money(criteria["wage_max"]))
    if criteria.get("has_bond") is True:
        parts.append("with an active bond")
    if criteria.get("has_bond") is False:
        parts.append("without a bond")
    if criteria.get("missing_bank_account"):
        parts.append("with no bank account on file")
    if criteria.get("manager_email"):
        parts.append("reporting to %s" % criteria["manager_email"])
    if not parts:
        return "Everyone currently employed"
    return "Everyone " + ", ".join(parts)


def _money(value):
    try:
        return "INR {:,.0f}".format(float(value))
    except (TypeError, ValueError):
        return str(value)


def summarise(criteria, limit=20):
    """Count plus a sample, which is what every preview in this app needs."""
    qs = resolve(criteria)
    wages = current_wages()
    people = list(qs[:limit])
    return {
        "count": qs.count(),
        "description": describe(criteria),
        "employees": [{
            "id": e.pk,
            "name": e.full_name,
            "email": e.work_email,
            "department": e.department.name if e.department else None,
            "job_position": e.job_position.name if e.job_position else None,
            "date_of_joining": e.date_of_joining.isoformat(),
            "wage": str(wages.get(e.pk) or ""),
        } for e in people],
    }


def clean_criteria(raw):
    """
    Keep only what `resolve` understands, and say what was thrown away.

    Used on everything a language model produces. The model is asked to pick
    from a closed list and mostly does; when it invents a key or a department
    that does not exist, dropping it silently would leave a segment that reads
    correctly and matches the wrong people.
    """
    from core.models import Department, JobPosition, WorkLocation

    raw = raw or {}
    kept, dropped = {}, []

    for key, value in raw.items():
        if key not in CRITERIA_KEYS:
            dropped.append("%s (not a filter this system has)" % key)
            continue
        if value in (None, "", [], {}):
            continue
        kept[key] = value

    def narrow(field, model, label):
        wanted = kept.get(field)
        if not wanted:
            return
        known = {n.lower(): n for n in model.objects.values_list("name", flat=True)}
        good, bad = [], []
        for name in (wanted if isinstance(wanted, list) else [wanted]):
            match = known.get(str(name).strip().lower())
            (good.append(match) if match else bad.append(str(name)))
        if bad:
            dropped.append("%s %s (no such %s)" % (label, ", ".join(bad), label))
        if good:
            kept[field] = good
        else:
            kept.pop(field, None)

    narrow("departments", Department, "department")
    narrow("job_positions", JobPosition, "job position")
    narrow("locations", WorkLocation, "location")

    types = kept.get("employee_types")
    if types:
        allowed = {c[0] for c in Employee.EMPLOYEE_TYPES}
        good = [t for t in types if t in allowed]
        bad = [t for t in types if t not in allowed]
        if bad:
            dropped.append("employment type %s" % ", ".join(bad))
        kept["employee_types"] = good or None
        if not good:
            kept.pop("employee_types")

    for key in ("wage_min", "wage_max", "tenure_months_min", "tenure_months_max"):
        if key in kept:
            try:
                kept[key] = float(kept[key]) if "wage" in key else int(kept[key])
            except (TypeError, ValueError):
                dropped.append("%s (not a number)" % key)
                kept.pop(key)

    for key in ("joined_before", "joined_after"):
        if key in kept:
            parsed = _as_date(kept[key])
            if parsed is None:
                dropped.append("%s (not a date)" % key)
                kept.pop(key)
            else:
                kept[key] = parsed.isoformat()

    return kept, dropped
