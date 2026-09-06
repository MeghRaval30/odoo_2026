"""
Standing rules that watch for a condition and raise a reminder when it is met.

The thing being automated is not a decision -- it is *remembering*. Nobody
forgets how to grant an increment; they forget that the person who joined last
March is now due one. So a playbook never acts. It fires an event that says who
and why, and a person decides.

That restraint is what makes it safe to leave switched on. The worst a
misconfigured rule can do is put a line in an inbox.
"""

from datetime import date, timedelta

from django.utils import timezone

from employees.models import Contract
from .models import Bond, Playbook, PlaybookEvent
from .segments import resolve


def _months_ago(months):
    today = date.today()
    year = today.year + (today.month - 1 - months) // 12
    month = (today.month - 1 - months) % 12 + 1
    return date(year, month, min(today.day, 28))


def _matches(playbook, on=None):
    """The employees this playbook's trigger fires for today, and why."""
    on = on or date.today()
    params = playbook.trigger_params or {}
    people = resolve(playbook.criteria)
    hits = []

    if playbook.trigger == Playbook.TENURE_REACHED:
        months = int(params.get("months") or 6)
        boundary = _months_ago(months)
        # A window rather than a boundary: a rule evaluated weekly would miss
        # anyone whose anniversary fell between two runs.
        window = boundary - timedelta(days=int(params.get("window_days") or 31))
        for employee in people.filter(date_of_joining__lte=boundary,
                                      date_of_joining__gt=window):
            served = (on - employee.date_of_joining).days // 30
            hits.append((employee, "%d months served as of %s"
                         % (served, on.strftime("%d %b %Y"))))

    elif playbook.trigger == Playbook.CONTRACT_ENDING:
        days = int(params.get("days") or 30)
        until = on + timedelta(days=days)
        ending = Contract.objects.filter(
            employee__in=people, state=Contract.RUNNING,
            end_date__isnull=False, end_date__gte=on, end_date__lte=until
        ).select_related("employee")
        for contract in ending:
            hits.append((contract.employee, "Contract ends %s"
                         % contract.end_date.strftime("%d %b %Y")))

    elif playbook.trigger == Playbook.BOND_EXPIRING:
        days = int(params.get("days") or 60)
        until = on + timedelta(days=days)
        for bond in Bond.objects.filter(
                employee__in=people, state__in=(Bond.SIGNED, Bond.ACTIVE),
                end_date__gte=on, end_date__lte=until).select_related("employee"):
            hits.append((bond.employee, "Bond ends %s, %d months left"
                         % (bond.end_date.strftime("%d %b %Y"),
                            bond.months_remaining(on))))

    elif playbook.trigger == Playbook.PROBATION_ENDING:
        days = int(params.get("days") or 30)
        months = int(params.get("probation_months") or 6)
        boundary = _months_ago(months)
        window = boundary - timedelta(days=days)
        for employee in people.filter(date_of_joining__lte=boundary,
                                      date_of_joining__gt=window):
            hits.append((employee, "Probation of %d months is ending" % months))

    elif playbook.trigger == Playbook.NO_BANK_ACCOUNT:
        for employee in people.filter(bank_account_number__isnull=True):
            hits.append((employee, "No bank account on file; a payrun will warn"))
        for employee in people.filter(bank_account_number=""):
            hits.append((employee, "No bank account on file; a payrun will warn"))

    return hits


def _title(playbook, employee):
    if playbook.action == Playbook.PROPOSE_INCREMENT:
        percent = (playbook.action_params or {}).get("percent")
        return ("Review %s for an increment%s"
                % (employee.full_name, " of %s%%" % percent if percent else ""))
    if playbook.action == Playbook.FLAG_REVIEW:
        return "Review %s" % employee.full_name
    return "%s: %s" % (playbook.name, employee.full_name)


def evaluate(playbook, commit=False, on=None):
    """
    Fire a playbook. `commit=False` reports who it would hit and records nothing.

    Events are unique per playbook and employee, so a rule left running does
    not refill the inbox every night with what somebody has already read.
    """
    hits = _matches(playbook, on)
    already = set(PlaybookEvent.objects
                  .filter(playbook=playbook)
                  .values_list("employee_id", flat=True))

    fresh = [(employee, why) for employee, why in hits
             if employee.pk not in already]

    if commit:
        PlaybookEvent.objects.bulk_create([
            PlaybookEvent(playbook=playbook, employee=employee,
                          title=_title(playbook, employee)[:200], detail=why[:400])
            for employee, why in fresh], ignore_conflicts=True)
        playbook.last_run = timezone.now()
        playbook.save(update_fields=["last_run", "updated_at"])

    return {
        "playbook": playbook.name,
        "matched": len(hits),
        "new": len(fresh),
        "already_raised": len(hits) - len(fresh),
        "people": [{"id": e.pk, "name": e.full_name, "email": e.work_email,
                    "reason": why} for e, why in hits[:40]],
    }


def run_all(commit=True, on=None):
    results = [evaluate(p, commit=commit, on=on)
               for p in Playbook.objects.filter(active=True)]
    return {"playbooks": len(results),
            "events_raised": sum(r["new"] for r in results),
            "results": results}
