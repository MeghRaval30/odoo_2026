"""
Turning an approved plan into employees and contracts.

Two entry points that share all of their logic and differ in one line: preview
builds every record and writes nothing, commit builds every record and writes
them inside one transaction. Sharing the path is the point -- a preview that is
computed differently from the import is a preview that lies, and the whole
argument for showing one is that it is what will happen.

The contract half deserves a note. An imported employee gets an employee row
*and* a running contract, because in this product a person without a contract
cannot be paid: the payrun resolves a contract for the period it covers and
finds nothing. Creating the pair together is what makes an imported roster
immediately usable in a payrun rather than a directory that needs a second day
of data entry.
"""

import base64
import re
import time
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import Company, Department, JobPosition, WorkLocation
from employees.models import Contract, Employee, WorkingSchedule
from payroll.models import SalaryStructure

from . import codes as code_policy
from . import enrich
from .profiler import is_blank
from .readers import read_table
from .transforms import apply_chain, set_value_mapping
from .validators import blocking_rows, derive_email, validate_rows

#: Employment types the model accepts, and the words a spreadsheet uses for
#: them. Anything unrecognised falls back to full time rather than refusing --
#: a wrong employment type is a correction, a refused import is a lost morning.
_TYPE_WORDS = {
    "full_time": "FULL_TIME", "fulltime": "FULL_TIME", "full time": "FULL_TIME",
    "permanent": "FULL_TIME", "regular": "FULL_TIME", "y": "FULL_TIME",
    "part_time": "PART_TIME", "parttime": "PART_TIME", "part time": "PART_TIME",
    "intern": "INTERN", "internship": "INTERN", "trainee": "INTERN",
    "contract": "CONTRACT", "contractor": "CONTRACT", "consultant": "CONTRACT",
    "temporary": "CONTRACT", "temp": "CONTRACT",
}

_GENDER_WORDS = {"m": "M", "male": "M", "f": "F", "female": "F",
                 "o": "O", "other": "O"}


def load_table(source):
    raw = base64.b64decode(source.content_b64.encode("ascii"))
    return read_table(raw, source.original_filename)


# ==========================================================================
# Plan -> records
# ==========================================================================

def _value_mapping_for(plan, column_index):
    for vm in (plan.get("value_maps") or []):
        if vm.get("column") == column_index:
            return {p["from"]: p["to"] for p in (vm.get("pairs") or [])
                    if p.get("to")}
    return {}


def build_records(table, plan):
    """
    Apply the plan to every row. Returns (records, cell_trace).

    `cell_trace` keeps the before and after of each mapped cell so the preview
    can show the transformation rather than only its result. It is dropped
    before commit -- it exists to be looked at, not stored.
    """
    columns = [c for c in (plan.get("columns") or []) if c.get("field")]
    for col in columns:
        mapping = _value_mapping_for(plan, col["index"])
        if mapping:
            set_value_mapping(col.get("transforms"), mapping)

    records, traces = [], []
    for row in table.rows:
        record, trace = {}, {}
        for col in columns:
            idx = col["index"]
            raw = row[idx] if idx < len(row) else ""
            value, ok, notes = apply_chain(raw, col.get("transforms"))

            if isinstance(value, dict):
                # split_name returns two fields from one column.
                record.update({k: v for k, v in value.items() if v not in (None, "")})
                trace[col["field"]] = {
                    "before": raw, "after": " / ".join(str(v) for v in value.values() if v),
                    "ok": ok, "notes": notes}
                continue

            record[col["field"]] = value
            trace[col["field"]] = {"before": raw,
                                   "after": "" if value is None else str(value),
                                   "ok": ok, "notes": notes}

        # A single name column stands in for both halves.
        if record.get("full_name") and not record.get("first_name"):
            parts = str(record["full_name"]).split()
            record["first_name"] = parts[0] if parts else ""
            record["last_name"] = " ".join(parts[1:])

        records.append(record)
        traces.append(trace)
    return records, traces


def _coerce(record):
    """Normalise the loose values a spreadsheet produces onto model choices."""
    etype = (record.get("employee_type") or "").strip().lower()
    record["employee_type"] = _TYPE_WORDS.get(etype, "FULL_TIME")

    gender = (record.get("gender") or "").strip().lower()
    record["gender"] = _GENDER_WORDS.get(gender, "")

    for key in ("bank_ifsc", "pan_number"):
        if record.get(key):
            record[key] = str(record[key]).strip().upper()
    return record


# ==========================================================================

def _defaults(company):
    schedule = (WorkingSchedule.objects.filter(company=company, active=True)
                .order_by("id").first())
    structure = (SalaryStructure.objects.filter(active=True).order_by("id").first()
                 if hasattr(SalaryStructure, "active")
                 else SalaryStructure.objects.order_by("id").first())
    return schedule, structure


def _resolve_named(model, company, name, cache, create):
    """Find a Department / JobPosition / WorkLocation by name, or make one."""
    key = (name or "").strip()
    if not key:
        return None, False
    lowered = key.lower()
    if lowered in cache:
        return cache[lowered], False
    existing = model.objects.filter(company=company, name__iexact=key).first()
    if existing:
        cache[lowered] = existing
        return existing, False
    if not create:
        return None, False
    made = model.objects.create(company=company, name=key)
    cache[lowered] = made
    return made, True


def _plan_summary(records, issues, table):
    blocked = blocking_rows(issues)
    return {
        "rows": len(records),
        "ok": len(records) - len(blocked),
        "blocked": len(blocked),
        "errors": sum(1 for i in issues if i["severity"] == "error"),
        "warnings": sum(1 for i in issues if i["severity"] == "warning"),
    }


def run(source, plan, commit=False, actor=None, company=None, apply_fixes=None,
        email_domain=None):
    """
    The single path. `commit=False` computes everything and writes nothing.

    `apply_fixes` names the auto-fixes the operator accepted, e.g.
    {"derive_email"} -- applied here rather than in the browser so that the
    preview and the import agree about what the data is.
    """
    started = time.time()
    apply_fixes = set(apply_fixes or [])
    company = company or Company.objects.order_by("id").first()

    table = load_table(source)
    records, traces = build_records(table, plan)
    records = [_coerce(r) for r in records]

    # Second files are applied before validation, so the issue list reflects
    # the data as it will actually be imported. Validating first would report
    # sixteen missing bank accounts and then quietly fix fourteen of them.
    enrichment_stats = apply_enrichments(table, records, plan)

    existing_emails = set(Employee.objects.values_list("work_email", flat=True))
    existing_codes = set(Employee.objects.values_list("employee_code", flat=True))

    # Derived emails are settled before validation, so the issue list reflects
    # the data as it will actually be imported rather than as it arrived.
    if "derive_email" in apply_fixes:
        domain = email_domain_for(records, email_domain)
        taken = {e.lower() for e in existing_emails}
        taken |= {(r.get("work_email") or "").lower() for r in records if r.get("work_email")}
        for rec in records:
            if is_blank(rec.get("work_email")) and rec.get("first_name"):
                made = derive_email(rec, domain, taken)
                rec["work_email"] = made
                rec["_derived_email"] = True
                taken.add(made.lower())

    issues = validate_rows(records, existing_emails, existing_codes)
    blocked = blocking_rows(issues)

    # Codes are assigned over the rows that will actually be written, so a
    # blocked row does not consume a number and leave a gap in the sequence.
    policy = plan.get("code_policy") or {}
    keeping = [r for i, r in enumerate(records) if i not in blocked]
    assigned = code_policy.assign(keeping, policy, existing_codes)
    for record, code in zip(keeping, assigned):
        if code:
            record["employee_code"] = code
            record["_generated_code"] = True

    result = {
        "counts": _plan_summary(records, issues, table),
        "issues": issues,
        "llm": plan.get("llm", {}),
        "enrichment": enrichment_stats,
        "code_policy": {
            **code_policy.normalise_policy(policy),
            "description": code_policy.describe(policy),
            "examples": [c for c in assigned[:6] if c],
        },
        "duration_ms": None,
    }

    if not commit:
        dept_names, pos_names, loc_names = _pending_names(records, company)
        result["records"] = _preview_rows(records, traces, blocked, limit=25)
        result["will_create"] = {
            "employees": len(records) - len(blocked),
            "contracts": sum(1 for i, r in enumerate(records)
                             if i not in blocked and r.get("wage") is not None),
            "departments": dept_names,
            "job_positions": pos_names,
            "work_locations": loc_names,
        }
        result["email_domain"] = email_domain_for(records, email_domain)
        result["duration_ms"] = int((time.time() - started) * 1000)
        return result

    created = _commit(records, blocked, company, actor)
    created["duration_ms"] = int((time.time() - started) * 1000)
    result.update(created)
    result["duration_ms"] = created["duration_ms"]
    return result


def apply_enrichments(table, records, plan):
    """
    Fill blanks from every second file attached to this run.

    Each supplement is re-read from its stored source and re-transformed rather
    than replayed from values cached in the plan, so that editing a
    supplement's mapping takes effect and the plan stays small enough to hand
    to a browser.
    """
    from .models import ImportSource

    stats = []
    for entry in (plan.get("enrichments") or []):
        source = ImportSource.objects.filter(pk=entry.get("source_id")).first()
        if source is None:
            stats.append({"name": entry.get("name"), "filled": 0,
                          "error": "The second file is no longer stored."})
            continue

        supplement = load_table(source)
        lookup = enrich.build_lookup(supplement, entry)
        filled = enrich.apply_enrichment(table, records, entry, lookup)

        join = entry.get("join") or {}
        stats.append({
            "name": entry.get("name"),
            "fields": entry.get("fields", []),
            "matched": join.get("matched", 0),
            "unmatched": join.get("unmatched", 0),
            "unused": join.get("unused", 0),
            "joined_on": join.get("primary_header"),
            "values_filled": filled,
        })
    return stats


def _commonest_domain(emails):
    counts = {}
    for email in emails:
        email = (email or "").strip()
        if "@" in email:
            domain = email.rsplit("@", 1)[1].lower()
            counts[domain] = counts.get(domain, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: kv[1])[0]


def email_domain_for(records, override=None):
    """
    Which domain a derived address should use.

    Three sources, in the order that gets it right most often:

      1. what the operator typed, if they typed one;
      2. the domain the rest of the file uses, so derived addresses sit
         alongside the ones that were supplied;
      3. the domain the existing roster uses, which is the answer when the file
         has no email column at all -- these people are joining *this* company,
         so its own domain is a better guess than anything in their old
         employer's spreadsheet.

    The fallback is deliberately obvious rather than plausible. An address at
    example.com is visibly a placeholder; one at a real-looking domain that
    happens to be wrong would be found months later by a bounced payslip.
    """
    if override:
        cleaned = str(override).strip().lstrip("@").lower()
        if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", cleaned):
            return cleaned

    from_file = _commonest_domain(rec.get("work_email") for rec in records)
    if from_file:
        return from_file

    from_roster = _commonest_domain(
        Employee.objects.values_list("work_email", flat=True)[:500])
    return from_roster or "example.com"


def _pending_names(records, company):
    """Which reference values do not exist yet and would be created."""
    def missing(model, key):
        wanted = {(r.get(key) or "").strip() for r in records if (r.get(key) or "").strip()}
        if not wanted:
            return []
        have = {n.lower() for n in
                model.objects.filter(company=company).values_list("name", flat=True)}
        return sorted(w for w in wanted if w.lower() not in have)

    return (missing(Department, "department"),
            missing(JobPosition, "job_position"),
            missing(WorkLocation, "work_location"))


def _preview_rows(records, traces, blocked, limit=25):
    out = []
    for i, (rec, trace) in enumerate(zip(records, traces)):
        if i >= limit:
            break
        # Cells that came from a second file are marked so the preview can
        # colour them differently. An operator looking at a bank account needs
        # to know it was not in the file they uploaded.
        cells = dict(trace)
        for field, origin in (rec.get("_enriched") or {}).items():
            cells[field] = {"before": "", "after": str(rec.get(field) or ""),
                            "ok": True, "notes": [], "from": origin}
        if rec.get("_generated_code"):
            cells["employee_code"] = {
                "before": "", "after": str(rec.get("employee_code") or ""),
                "ok": True, "notes": [], "generated": True}

        out.append({
            "row": i,
            "blocked": i in blocked,
            "derived_email": bool(rec.get("_derived_email")),
            "enriched": sorted((rec.get("_enriched") or {}).keys()),
            "generated_code": rec.get("employee_code")
                              if rec.get("_generated_code") else None,
            "values": {k: ("" if v is None else str(v))
                       for k, v in rec.items() if not k.startswith("_")},
            "cells": cells,
        })
    return out


# ==========================================================================

@transaction.atomic
def _commit(records, blocked, company, actor):
    """
    Write the roster. All of it or none of it.

    Atomic on purpose: a migration that half-succeeds leaves an operator
    guessing which of four hundred people made it, and the honest recovery is
    to fix the file and run it again against a clean database.
    """
    schedule, structure = _defaults(company)
    dept_cache, pos_cache, loc_cache = {}, {}, {}
    made = {"employees": 0, "contracts": 0, "departments": 0,
            "job_positions": 0, "work_locations": 0}
    employee_ids = []
    failures = []

    for i, rec in enumerate(records):
        if i in blocked:
            continue
        try:
            department, new_d = _resolve_named(Department, company,
                                               rec.get("department"), dept_cache, True)
            position, new_p = _resolve_named(JobPosition, company,
                                             rec.get("job_position"), pos_cache, True)
            location, new_l = _resolve_named(WorkLocation, company,
                                             rec.get("work_location"), loc_cache, True)
            made["departments"] += int(new_d)
            made["job_positions"] += int(new_p)
            made["work_locations"] += int(new_l)

            doj = rec.get("date_of_joining")
            if not isinstance(doj, date):
                doj = date.today()

            employee = Employee.objects.create(
                # Blank falls through to Employee.save(), which numbers
                # EMP/<year>/0001 -- the "auto" policy, and the default.
                employee_code=(rec.get("employee_code") or "").strip()[:20],
                first_name=(rec.get("first_name") or "").strip()[:80],
                last_name=(rec.get("last_name") or "").strip()[:80],
                work_email=(rec.get("work_email") or "").strip().lower(),
                work_phone=(rec.get("work_phone") or "")[:20],
                company=company,
                department=department,
                job_position=position,
                work_location=location,
                working_schedule=schedule,
                employee_type=rec.get("employee_type") or "FULL_TIME",
                date_of_joining=doj,
                date_of_birth=rec.get("date_of_birth") if isinstance(
                    rec.get("date_of_birth"), date) else None,
                gender=rec.get("gender") or "",
                personal_email=(rec.get("personal_email") or "")[:254],
                personal_phone=(rec.get("personal_phone") or "")[:20],
                address=rec.get("address") or "",
                bank_account_number=(rec.get("bank_account_number") or None) or None,
                bank_ifsc=(rec.get("bank_ifsc") or None) or None,
                pan_number=(rec.get("pan_number") or None) or None,
            )
            made["employees"] += 1
            employee_ids.append(employee.pk)

            wage = rec.get("wage")
            if wage is not None:
                start = rec.get("contract_start")
                if not isinstance(start, date):
                    start = doj
                end = rec.get("contract_end")
                Contract.objects.create(
                    employee=employee,
                    department=department,
                    job_position=position,
                    start_date=start,
                    end_date=end if isinstance(end, date) else None,
                    wage=Decimal(str(wage)).quantize(Decimal("0.01")),
                    working_schedule=schedule,
                    salary_structure=structure,
                    state=Contract.RUNNING,
                    notes="Created by data import.",
                )
                made["contracts"] += 1
        except Exception as exc:
            failures.append({"row": i, "message": str(exc)[:200]})

    return {"created": made, "skipped": len(blocked), "failed": len(failures),
            "failures": failures, "employee_ids": employee_ids}


def resolve_managers(records, employee_ids):
    """
    Second pass for manager links.

    Deliberately separate and deliberately after: a manager may be later in the
    same file than the person reporting to them, so the link can only be made
    once every row exists.
    """
    wanted = [(pk, (rec.get("manager_email") or "").strip().lower())
              for pk, rec in zip(employee_ids, records)
              if rec.get("manager_email")]
    if not wanted:
        return 0
    lookup = {e.work_email.lower(): e
              for e in Employee.objects.filter(
                  work_email__in=[m for _, m in wanted])}
    linked = 0
    for pk, email in wanted:
        manager = lookup.get(email)
        if manager and manager.pk != pk:
            Employee.objects.filter(pk=pk).update(manager=manager)
            linked += 1
    return linked


def finish(run_obj, result):
    run_obj.stats = {k: v for k, v in result.items()
                     if k in ("created", "skipped", "failed", "counts", "duration_ms")}
    run_obj.state = run_obj.DONE
    run_obj.completed_at = timezone.now()
    run_obj.save(update_fields=["stats", "state", "completed_at", "updated_at"])
    return run_obj
