"""
Everything wrong with the data, found before anything is written.

The distinction that matters here is error versus warning, and it is not a
severity dial -- it decides whether a row is imported. An error means the row
cannot become a valid employee: no email, no joining date, a duplicate of
somebody already on the roster. A warning means it can, but somebody should
know: no bank account, so this person will raise a payrun warning next month.

Errors skip their row and let the rest of the file through. That is the right
default for a migration: a company arriving with four hundred people and three
bad rows wants three hundred and ninety-seven employees and a list, not a
refusal. The three are reported precisely enough to fix in the source file and
re-run.
"""

import re
from datetime import date

from .profiler import is_blank

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_IFSC = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

#: A monthly wage outside this is not refused, only questioned. The lower bound
#: catches an annual figure that was divided twice; the upper catches one that
#: was not divided at all.
WAGE_FLOOR = 1000
WAGE_CEILING = 5000000


def _issue(row, column, severity, code, message, suggestion="", auto_fix=""):
    return {"row": row, "column": column, "severity": severity, "code": code,
            "message": message, "suggestion": suggestion, "auto_fix": auto_fix}


def derive_email(record, domain, taken):
    """
    Build a work email for a row that has none.

    Offered as a fix rather than applied, because an invented address is a real
    decision -- it is what payslips will be sent to. The pattern matches how
    the rest of the roster is addressed so the derived ones do not stand out.
    """
    first = (record.get("first_name") or "").strip().lower()
    last = (record.get("last_name") or "").strip().lower()
    base = re.sub(r"[^a-z0-9]", "", first) or "employee"
    candidate = "%s@%s" % (base, domain)
    n = 1
    while candidate in taken:
        n += 1
        surname = re.sub(r"[^a-z0-9]", "", last)
        candidate = ("%s.%s@%s" % (base, surname, domain) if surname and n == 2
                     else "%s%d@%s" % (base, n, domain))
    return candidate


def validate_rows(records, existing_emails=None, existing_codes=None, today=None):
    """
    Check every mapped row. `records` are post-transform dicts keyed by field.

    Returns a list of issue dicts in the shape the screen renders.
    """
    existing_emails = {e.lower() for e in (existing_emails or [])}
    existing_codes = {c.lower() for c in (existing_codes or []) if c}
    today = today or date.today()

    issues = []
    seen_emails = {}
    seen_codes = {}

    for i, rec in enumerate(records):
        email = (rec.get("work_email") or "").strip()
        name = (rec.get("first_name") or rec.get("full_name") or "").strip()

        # -- identity ----------------------------------------------------
        if not name:
            issues.append(_issue(i, "first_name", "error", "MISSING_REQUIRED",
                                 "No name in this row.",
                                 "Map a name column, or remove the row."))

        if not email:
            issues.append(_issue(
                i, "work_email", "error", "MISSING_REQUIRED",
                "No work email%s." % (" for %s" % name if name else ""),
                "Derive one from the name, or skip the row.", "derive_email"))
        elif not _EMAIL.match(email):
            issues.append(_issue(i, "work_email", "error", "BAD_EMAIL",
                                 "%r is not a valid email address." % email[:60],
                                 "Correct it in the source file."))
        else:
            key = email.lower()
            if key in existing_emails:
                issues.append(_issue(
                    i, "work_email", "error", "DUPLICATE_EMAIL",
                    "%s already belongs to an employee here." % email,
                    "Skip this row, or import as an update.", "skip_row"))
            elif key in seen_emails:
                issues.append(_issue(
                    i, "work_email", "error", "DUPLICATE_IN_FILE",
                    "%s appears twice in this file (also row %d)."
                    % (email, seen_emails[key] + 1),
                    "Keep the first and skip this one.", "skip_row"))
            else:
                seen_emails[key] = i

        code = (rec.get("employee_code") or "").strip()
        if code:
            if code.lower() in existing_codes:
                issues.append(_issue(i, "employee_code", "warning", "DUPLICATE_CODE",
                                     "Employee code %s is already in use." % code,
                                     "A new code will be generated instead."))
            elif code.lower() in seen_codes:
                issues.append(_issue(i, "employee_code", "warning", "DUPLICATE_CODE",
                                     "Employee code %s repeats in this file." % code,
                                     "A new code will be generated instead."))
            else:
                seen_codes[code.lower()] = i

        # -- dates -------------------------------------------------------
        doj = rec.get("date_of_joining")
        if not doj:
            issues.append(_issue(i, "date_of_joining", "error", "MISSING_REQUIRED",
                                 "No joining date%s." % (" for %s" % name if name else ""),
                                 "Map a date column, or set one for the whole file."))
        elif isinstance(doj, date) and doj > today:
            issues.append(_issue(i, "date_of_joining", "warning", "FUTURE_JOINING",
                                 "Joining date %s is in the future." % doj.isoformat(),
                                 "Fine for a future hire; check it is not a typo."))

        dob = rec.get("date_of_birth")
        if isinstance(dob, date) and isinstance(doj, date):
            age = (doj - dob).days / 365.25
            if age < 15 or age > 75:
                issues.append(_issue(i, "date_of_birth", "warning", "IMPLAUSIBLE_AGE",
                                     "Age at joining works out as %d." % age,
                                     "Check the date format on this column."))

        # -- money -------------------------------------------------------
        wage = rec.get("wage")
        if wage is None:
            issues.append(_issue(i, "wage", "error", "MISSING_REQUIRED",
                                 "No wage%s." % (" for %s" % name if name else ""),
                                 "Map a salary column. Without one there is no "
                                 "contract to pay against."))
        else:
            try:
                amount = float(wage)
            except (TypeError, ValueError):
                amount = None
            if amount is None:
                issues.append(_issue(i, "wage", "error", "NON_POSITIVE_WAGE",
                                     "Wage %r could not be read as a number." % wage,
                                     "Check the currency transforms on that column."))
            elif amount <= 0:
                issues.append(_issue(i, "wage", "error", "NON_POSITIVE_WAGE",
                                     "Wage is %s." % amount,
                                     "A contract needs a positive wage."))
            elif amount < WAGE_FLOOR:
                issues.append(_issue(i, "wage", "warning", "IMPLAUSIBLE_WAGE",
                                     "Monthly wage of %s looks low." % amount,
                                     "Check whether a scale step was applied twice."))
            elif amount > WAGE_CEILING:
                issues.append(_issue(i, "wage", "warning", "IMPLAUSIBLE_WAGE",
                                     "Monthly wage of %s looks like an annual figure."
                                     % amount,
                                     "Add a scale step dividing by 12."))

        # -- bank --------------------------------------------------------
        ifsc = (rec.get("bank_ifsc") or "").strip().upper()
        if ifsc and not _IFSC.match(ifsc):
            issues.append(_issue(i, "bank_ifsc", "warning", "BAD_IFSC",
                                 "%s is not a valid IFSC code." % ifsc[:20],
                                 "Eleven characters, fifth is a zero."))

        pan = (rec.get("pan_number") or "").strip().upper()
        if pan and not _PAN.match(pan):
            issues.append(_issue(i, "pan_number", "warning", "BAD_PAN",
                                 "%s is not a valid PAN." % pan[:20],
                                 "Five letters, four digits, one letter."))

        if is_blank(rec.get("bank_account_number")):
            issues.append(_issue(
                i, "bank_account_number", "warning", "NO_BANK_ACCOUNT",
                "No bank account%s." % (" for %s" % name if name else ""),
                "The employee imports fine, but a payrun will warn until one "
                "is added."))

    return issues


def blocking_rows(issues):
    """Row indexes that carry at least one unresolved error."""
    return {iss["row"] for iss in issues
            if iss["severity"] == "error" and not iss.get("resolved")}
