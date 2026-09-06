"""
The shape of a *historical payslip*, and the words payroll sheets call it by.

This is the sister of `schema.py`. That one describes a person arriving in the
system; this one describes a month of pay that already happened somewhere else.

The two are deliberately separate files rather than one table with a `target`
column. An employee import and a payslip import disagree about almost
everything that matters: what identifies a row, what "required" means, what a
duplicate is, and above all what the numbers are *for*. In an employee sheet a
money column is a wage -- one figure, one meaning. In a payroll sheet every
money column is a **component**, they are related by arithmetic, and the
arithmetic is the thing worth checking. Merging the two vocabularies would mean
"basic" is a synonym of both `wage` and `basic`, which is how a migration
quietly puts an employee's HRA in their gross.

So: separate vocabulary, separate required set, shared machinery. The reader,
the profiler and the header matcher below are the same code the employee
importer uses -- `match_header` already takes the field list as an argument,
which is the seam this file exists to use.

## Why the components are typed by category

Every money field carries a `category` from `SalaryRule.CATEGORIES`. That is
what lets an imported payslip behave like a computed one: `Payslip.basic`,
`.allowances`, `.deductions`, `.gross` and `.net` are all derived by summing
lines *by category*, so an imported line tagged DEDUCTION subtracts itself with
no further help. A historical payslip and a computed one then read identically
on screen and in the register, which is the whole point of importing them
rather than keeping them in a spreadsheet.
"""

from .schema import _similarity, normalise

# ==========================================================================
# The fields a historical payslip row can fill
# ==========================================================================
#
# `category` is None for anything that is not money.
# `sequence` mirrors the order the salary rules run in, so an imported payslip
# lists its lines in the same order a computed one does.

PAYSLIP_FIELDS = [
    # -- who this payslip belongs to ---------------------------------------
    {
        "key": "employee_code", "label": "Employee code", "kind": "code",
        "required": False, "group": "Identity", "category": None,
        "hint": "Matched against the employee code already on the record.",
        "synonyms": ["emp id", "empid", "emp code", "employee id",
                     "employee code", "staff id", "staff no", "token no",
                     "payroll no", "emp no", "code", "pf no", "ticket no"],
    },
    {
        "key": "work_email", "label": "Work email", "kind": "email",
        "required": False, "group": "Identity", "category": None,
        "hint": "The surest way to match a row to a person.",
        "synonyms": ["email", "e mail", "mail", "email id", "mail id",
                     "official email", "work mail", "company email",
                     "email address", "work email", "office email"],
    },
    {
        "key": "full_name", "label": "Employee name", "kind": "name",
        "required": False, "group": "Identity", "category": None,
        "hint": "Used to match only when no code or email is present.",
        "synonyms": ["name", "full name", "emp name", "employee name",
                     "staff name", "employee", "person", "worker name"],
    },

    # -- which month ---------------------------------------------------------
    {
        "key": "period_month", "label": "Pay month", "kind": "text",
        "required": False, "group": "Period", "category": None,
        "hint": "'Dec 2025', '12/2025' or '2025-12'. Expands to the whole month.",
        "synonyms": ["month", "pay month", "salary month", "period",
                     "pay period", "payroll month", "month year", "mon",
                     "wage month", "for the month of", "pay cycle", "cycle"],
    },
    {
        "key": "period_start", "label": "Period start", "kind": "date",
        "required": False, "group": "Period", "category": None,
        "hint": "First day covered. Defaults to the first of the pay month.",
        "synonyms": ["period start", "from date", "from", "start date",
                     "period from", "salary from", "wef"],
    },
    {
        "key": "period_end", "label": "Period end", "kind": "date",
        "required": False, "group": "Period", "category": None,
        "hint": "Last day covered. Defaults to the last of the pay month.",
        "synonyms": ["period end", "to date", "till", "end date",
                     "period to", "salary to", "upto"],
    },

    # -- attendance carried on the payslip -----------------------------------
    {
        "key": "worked_days", "label": "Worked days", "kind": "decimal",
        "required": False, "group": "Attendance", "category": None,
        "hint": "Days actually paid for.",
        "synonyms": ["worked days", "days worked", "paid days", "present days",
                     "payable days", "days paid", "attendance", "working days",
                     "no of days", "days"],
    },
    {
        "key": "expected_days", "label": "Expected days", "kind": "decimal",
        "required": False, "group": "Attendance", "category": None,
        "hint": "Days in the month the contract required.",
        "synonyms": ["expected days", "total days", "month days",
                     "standard days", "calendar days", "gross days"],
    },
    {
        "key": "lop_days", "label": "Loss of pay days", "kind": "decimal",
        "required": False, "group": "Attendance", "category": None,
        "hint": "Unpaid absence in the period.",
        "synonyms": ["lop", "lop days", "loss of pay", "lwp", "absent days",
                     "unpaid days", "absent", "leave without pay"],
    },
    {
        "key": "overtime_hours", "label": "Overtime hours", "kind": "decimal",
        "required": False, "group": "Attendance", "category": None,
        "hint": "Hours of overtime, not the amount paid for them.",
        "synonyms": ["ot hours", "overtime hours", "ot hrs", "extra hours",
                     "overtime hrs"],
    },

    # -- earnings ------------------------------------------------------------
    {
        "key": "basic", "label": "Basic", "kind": "money",
        "required": True, "group": "Earnings",
        "category": "BASIC", "code": "BASIC", "sequence": 10,
        "hint": "The base component every other rule is a percentage of.",
        "synonyms": ["basic", "basic salary", "basic pay", "basic wage",
                     "basic amount", "bsc", "basic da", "basic + da"],
    },
    {
        "key": "hra", "label": "House rent allowance", "kind": "money",
        "required": False, "group": "Earnings",
        "category": "ALLOWANCE", "code": "HRA", "sequence": 20,
        "hint": "Typically 40 or 50 percent of basic.",
        "synonyms": ["hra", "house rent", "house rent allowance", "rent allowance",
                     "h r a", "hra amount"],
    },
    {
        "key": "conveyance", "label": "Conveyance", "kind": "money",
        "required": False, "group": "Earnings",
        "category": "ALLOWANCE", "code": "CONV", "sequence": 30,
        "hint": "Travel allowance.",
        "synonyms": ["conveyance", "conveyance allowance", "travel allowance",
                     "transport allowance", "ta", "conv"],
    },
    {
        "key": "medical_allowance", "label": "Medical allowance", "kind": "money",
        "required": False, "group": "Earnings",
        "category": "ALLOWANCE", "code": "MED", "sequence": 35,
        "hint": "Medical reimbursement paid as an allowance.",
        "synonyms": ["medical", "medical allowance", "medical reimbursement",
                     "med allowance", "mediclaim allowance"],
    },
    {
        "key": "special_allowance", "label": "Special allowance", "kind": "money",
        "required": False, "group": "Earnings",
        "category": "ALLOWANCE", "code": "SPL", "sequence": 40,
        "hint": "The balancing allowance most Indian structures carry.",
        "synonyms": ["special allowance", "special pay", "spl allowance",
                     "spl", "other allowance", "misc allowance",
                     "balance allowance", "flexi pay"],
    },
    {
        "key": "overtime_amount", "label": "Overtime paid", "kind": "money",
        "required": False, "group": "Earnings",
        "category": "ALLOWANCE", "code": "OT", "sequence": 50,
        "hint": "The money paid for overtime, not the hours.",
        "synonyms": ["ot", "ot amount", "overtime", "overtime amount",
                     "overtime pay", "ot pay", "extra hours pay"],
    },
    {
        "key": "bonus", "label": "Bonus", "kind": "money",
        "required": False, "group": "Earnings",
        "category": "ALLOWANCE", "code": "BONUS", "sequence": 55,
        "hint": "Statutory or performance bonus paid in this month.",
        "synonyms": ["bonus", "incentive", "performance bonus", "ex gratia",
                     "exgratia", "statutory bonus", "variable pay"],
    },
    {
        "key": "arrears", "label": "Arrears", "kind": "money",
        "required": False, "group": "Earnings",
        "category": "ALLOWANCE", "code": "ARREAR", "sequence": 58,
        "hint": "Back pay settled in this month.",
        "synonyms": ["arrears", "arrear", "back pay", "salary arrears",
                     "arrear amount"],
    },

    # -- the stated totals ---------------------------------------------------
    #
    # Gross and net are read but never stored as lines: they are *derived* from
    # the components on our side. They are imported so the arithmetic check has
    # something to check against -- see `payslips.reconcile`.
    {
        "key": "gross", "label": "Gross (stated)", "kind": "money",
        "required": False, "group": "Totals", "category": None,
        "hint": "Checked against the components; not stored as a line.",
        "synonyms": ["gross", "gross salary", "gross pay", "total earnings",
                     "total earning", "gross earnings", "gross amount",
                     "total gross", "earnings total"],
    },
    {
        "key": "total_deductions", "label": "Total deductions (stated)",
        "kind": "money",
        "required": False, "group": "Totals", "category": None,
        "hint": "Checked against the deduction components; not stored as a line.",
        "synonyms": ["total deduction", "total deductions", "total ded",
                     "deduction total", "gross deduction", "gross deductions",
                     "total recovery", "less deductions", "deductions"],
    },
    {
        "key": "net", "label": "Net pay (stated)", "kind": "money",
        "required": False, "group": "Totals", "category": None,
        "hint": "Checked against the components; not stored as a line.",
        "synonyms": ["net", "net pay", "net salary", "take home", "takehome",
                     "net amount", "net payable", "amount payable",
                     "salary payable", "in hand", "net paid"],
    },

    # -- deductions ----------------------------------------------------------
    {
        "key": "pf_employee", "label": "Provident fund", "kind": "money",
        "required": False, "group": "Deductions",
        "category": "DEDUCTION", "code": "PF", "sequence": 100,
        "hint": "The employee's own PF, not the employer's share.",
        "synonyms": ["pf", "epf", "provident fund", "pf employee",
                     "employee pf", "pf deduction", "epf employee",
                     "pf ee", "12% pf"],
    },
    {
        "key": "esic_employee", "label": "ESIC", "kind": "money",
        "required": False, "group": "Deductions",
        "category": "DEDUCTION", "code": "ESIC", "sequence": 110,
        "hint": "Employee state insurance, employee share.",
        "synonyms": ["esi", "esic", "esi employee", "employee esi",
                     "esic deduction", "esi ee"],
    },
    {
        "key": "professional_tax", "label": "Professional tax", "kind": "money",
        "required": False, "group": "Deductions",
        "category": "DEDUCTION", "code": "PT", "sequence": 120,
        "hint": "State professional tax.",
        "synonyms": ["pt", "ptax", "prof tax", "professional tax",
                     "p tax", "profession tax"],
    },
    {
        "key": "income_tax", "label": "Income tax (TDS)", "kind": "money",
        "required": False, "group": "Deductions",
        "category": "DEDUCTION", "code": "TDS", "sequence": 130,
        "hint": "Tax deducted at source.",
        "synonyms": ["tds", "income tax", "it", "tax", "tax deducted",
                     "itax", "tds deduction"],
    },
    {
        "key": "lwf", "label": "Labour welfare fund", "kind": "money",
        "required": False, "group": "Deductions",
        "category": "DEDUCTION", "code": "LWF", "sequence": 140,
        "hint": "Labour welfare fund contribution.",
        "synonyms": ["lwf", "labour welfare", "labour welfare fund",
                     "lwf deduction", "welfare fund"],
    },
    {
        "key": "loan_deduction", "label": "Loan / advance", "kind": "money",
        "required": False, "group": "Deductions",
        "category": "DEDUCTION", "code": "LOAN", "sequence": 150,
        "hint": "Loan or salary advance recovered this month.",
        "synonyms": ["loan", "advance", "loan deduction", "salary advance",
                     "advance recovery", "loan emi", "recovery"],
    },
    {
        "key": "other_deductions", "label": "Other deductions", "kind": "money",
        "required": False, "group": "Deductions",
        "category": "DEDUCTION", "code": "OTHDED", "sequence": 160,
        "hint": "Anything else withheld.",
        "synonyms": ["other deduction", "other deductions", "misc deduction",
                     "other ded", "sundry deduction", "misc ded",
                     "sundry", "other recovery"],
    },
]

FIELDS_BY_KEY = {f["key"]: f for f in PAYSLIP_FIELDS}
FIELD_KEYS = [f["key"] for f in PAYSLIP_FIELDS]

#: Money fields that become an actual `PayslipLine`. Gross and net are excluded
#: on purpose -- they are totals we recompute, not components we store.
COMPONENT_FIELDS = [f for f in PAYSLIP_FIELDS if f.get("code")]
COMPONENT_KEYS = [f["key"] for f in COMPONENT_FIELDS]

EARNING_KEYS = [f["key"] for f in COMPONENT_FIELDS
                if f["category"] in ("BASIC", "ALLOWANCE")]
DEDUCTION_KEYS = [f["key"] for f in COMPONENT_FIELDS
                  if f["category"] == "DEDUCTION"]

#: Fields that identify the person. At least one is needed for any row to
#: import at all -- which is why "required" here means something different from
#: the employee schema's version. See `missing_required`.
IDENTITY_KEYS = ["employee_code", "work_email", "full_name"]

#: Fields that fix the month. `period_month` alone is enough; so is a start and
#: an end together.
PERIOD_KEYS = ["period_month", "period_start", "period_end"]


def missing_required(columns):
    """
    What this plan still cannot answer.

    Three questions have to be answerable before a payslip row means anything:
    *who*, *when*, and *how much*. Each is satisfied by any one of a set of
    columns rather than by one named column, which is why this cannot reuse the
    employee importer's `missing_required` -- that one asks "is field X mapped"
    and here the honest question is "is question Q answered".

    Returns a list of `{key, label, why}`, empty when the plan is importable.
    """
    mapped = {c.get("field") for c in (columns or []) if c.get("field")}
    gaps = []

    if not (mapped & set(IDENTITY_KEYS)):
        gaps.append({
            "key": "identity",
            "label": "Something that identifies the employee",
            "why": "Map an employee code, a work email or a name. Without one "
                   "of these there is no way to say whose payslip this is.",
        })

    has_month = "period_month" in mapped
    has_range = "period_start" in mapped and "period_end" in mapped
    if not (has_month or has_range):
        gaps.append({
            "key": "period",
            "label": "The month this pay covers",
            "why": "Map a pay month, or both a period start and a period end. "
                   "A payslip with no period cannot be filed against a payrun.",
        })

    if not (mapped & set(EARNING_KEYS)):
        gaps.append({
            "key": "earnings",
            "label": "At least one earning component",
            "why": "Map Basic, or any allowance. A payslip with no earnings "
                   "is not a payslip.",
        })

    return gaps


# ==========================================================================
# Recognising a payroll column
# ==========================================================================
#
# This cannot reuse `schema.match_header`. That function vetoes a candidate by
# looking the profiled kind up in `schema.KIND_COMPATIBILITY`, whose values are
# *employee* field keys -- handed a payslip field list it would demote every
# single candidate to a quarter confidence and the plan would come back empty.
# The veto is worth keeping, so the table is restated here over this file's
# vocabulary instead.

#: Which payslip fields a profiled column is allowed to be.
#:
#: The money row is the important one. Nearly every column in a payroll sheet
#: is money, so the shape of the values narrows almost nothing and the header
#: has to do the work. That is the opposite of the employee importer, where an
#: email column can only ever be one of three things.
KIND_COMPATIBILITY = {
    "email": {"work_email"},
    "phone": set(),
    "date": {"period_start", "period_end", "period_month"},
    "money": set(EARNING_KEYS) | set(DEDUCTION_KEYS) | {"gross", "net", "total_deductions"},
    "decimal": (set(EARNING_KEYS) | set(DEDUCTION_KEYS)
                | {"gross", "net", "total_deductions"}
                | {"worked_days", "expected_days", "lop_days",
                   "overtime_hours"}),
    "integer": (set(EARNING_KEYS) | set(DEDUCTION_KEYS)
                | {"gross", "net", "total_deductions", "employee_code",
                   "worked_days", "expected_days", "lop_days",
                   "overtime_hours"}),
    "name": {"full_name", "employee_code", "period_month"},
    "code": {"employee_code"},
    "categorical": {"period_month", "employee_code", "full_name"},
    "ifsc": set(),
    "pan": set(),
    "boolean": set(),
    "text": set(FIELD_KEYS),
    "empty": set(),
}

#: Attendance counts and money are both numbers, and a sheet that writes
#: "Days" next to "Basic" gives the profiler no way to tell them apart. These
#: fields are therefore held to a plausible range as well as a shape: nobody
#: works 40,000 days and nobody is paid 26 rupees a month.
_DAY_FIELDS = {"worked_days", "expected_days", "lop_days"}


def _magnitude_supports(field_key, profile):
    """
    Does the size of these numbers fit this field?

    A cheap, entirely arithmetic check that catches the one confusion this
    vocabulary is genuinely prone to. A median above 400 is not a count of days
    in a month; a median below 100 across a whole column is not somebody's
    basic pay.
    """
    median = profile.get("numeric_median") if profile else None
    if median is None:
        return True
    if field_key in _DAY_FIELDS:
        return median <= 400
    if field_key == "overtime_hours":
        return median <= 400
    if (field_key in EARNING_KEYS
            or field_key in ("gross", "net", "total_deductions")):
        return median >= 100
    return True


def match_header(header, profile=None):
    """
    Rank payslip fields for one column header, on the label alone.

    Same two-part shape as the employee importer's voter: the label proposes,
    the values may only veto. Keeping the profile out of the proposal is what
    makes the model's opinion and the data's opinion independent, so their
    agreement is evidence rather than an echo.
    """
    norm = normalise(header)
    if not norm:
        return []
    toks = set(norm.split())
    best_kind = (profile or {}).get("best_kind")

    out = []
    for field in PAYSLIP_FIELDS:
        vocabulary = [field["label"]] + field["synonyms"] + [field["key"]]
        score, why = 0.0, ""

        for phrase in vocabulary:
            p = normalise(phrase)
            if not p:
                continue
            if p == norm:
                score, why = 0.97, "header matches '%s' exactly" % phrase
                break
            ptoks = set(p.split())
            overlap = len(toks & ptoks) / len(toks | ptoks) if (toks | ptoks) else 0
            if overlap > 0:
                cand = 0.45 + 0.45 * overlap
                if cand > score:
                    score, why = cand, "header shares '%s' with '%s'" % (
                        " ".join(sorted(toks & ptoks)), phrase)
            sim = _similarity(norm, p)
            if sim > 0.82:
                cand = 0.4 + 0.5 * sim
                if cand > score:
                    score, why = cand, "header reads like '%s'" % phrase

        if score <= 0:
            continue

        if best_kind and best_kind in KIND_COMPATIBILITY:
            allowed = KIND_COMPATIBILITY[best_kind]
            if allowed and field["key"] not in allowed:
                score *= 0.25
                why += "; values do not look like %s" % field["label"].lower()

        if not _magnitude_supports(field["key"], profile):
            score *= 0.2
            why += "; the numbers are the wrong size for %s" % field["label"].lower()

        out.append({"field": field["key"], "confidence": round(min(score, 0.99), 3),
                    "reason": why})

    out.sort(key=lambda c: c["confidence"], reverse=True)
    return out[:3]
