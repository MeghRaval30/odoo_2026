"""
The shape we are importing *onto*, and the lexical half of recognising it.

Two things live here because they are one thing: the list of fields an imported
row can fill, and the vocabulary each of those fields is known by in the wild.
A synonym list is not a nicety. "DOJ" is what half the HR spreadsheets in India
call a joining date, and a matcher that only knows "date_of_joining" is a
matcher that needs a language model to read a two-letter abbreviation -- which
is exactly the work a 7B is worst at and a dictionary is perfect at.

So the lexical voter here answers the easy questions for free and leaves the
model the ones that are actually ambiguous. On the three demo files it maps
most columns on its own, which is why the import still works with the model
switched off.
"""

import re

#: kind drives which transforms are proposed and which fields a profiled column
#: is allowed to be reconciled onto. See `mapper.KIND_COMPATIBILITY`.
TARGET_FIELDS = [
    {
        "key": "full_name", "label": "Full name", "kind": "name",
        "required": False, "group": "Identity",
        "hint": "The person's whole name in one column; it is split on import.",
        "synonyms": ["name", "full name", "emp name", "employee name",
                     "staff name", "naam", "emp naam", "employee", "person",
                     "candidate name", "worker name", "member name"],
    },
    {
        "key": "first_name", "label": "First name", "kind": "name",
        "required": True, "group": "Identity",
        "hint": "Given name.",
        "synonyms": ["first name", "firstname", "given name", "fname",
                     "first", "forename"],
    },
    {
        "key": "last_name", "label": "Last name", "kind": "name",
        "required": False, "group": "Identity",
        "hint": "Family name.",
        "synonyms": ["last name", "lastname", "surname", "family name",
                     "lname", "last"],
    },
    {
        "key": "employee_code", "label": "Employee code", "kind": "code",
        "required": False, "group": "Identity",
        "hint": "The company's own identifier for the person.",
        "synonyms": ["emp id", "empid", "emp code", "employee id",
                     "employee code", "staff id", "staff no", "code",
                     "token no", "payroll no", "emp no", "sr no", "id"],
    },
    {
        "key": "work_email", "label": "Work email", "kind": "email",
        "required": True, "group": "Contact",
        "hint": "Official email. Must be unique; it identifies the record.",
        "synonyms": ["email", "e mail", "mail", "email id", "mail id",
                     "official email", "work mail", "company email",
                     "email address", "work email", "office email"],
    },
    {
        "key": "personal_email", "label": "Personal email", "kind": "email",
        "required": False, "group": "Contact",
        "hint": "Private address, if the sheet carries one.",
        "synonyms": ["personal email", "private email", "alternate email",
                     "personal mail", "home email"],
    },
    {
        "key": "work_phone", "label": "Work phone", "kind": "phone",
        "required": False, "group": "Contact",
        "hint": "Contact number.",
        "synonyms": ["mobile", "mob", "mob no", "mobile no", "mobile number",
                     "phone", "phone no", "contact", "contact no",
                     "contact number", "cell", "cell no", "telephone"],
    },
    {
        "key": "address", "label": "Address", "kind": "text",
        "required": False, "group": "Contact",
        "hint": "Postal address.",
        "synonyms": ["address", "residential address", "home address",
                     "addr", "location address"],
    },
    {
        "key": "department", "label": "Department", "kind": "category",
        "required": False, "group": "Organisation",
        "hint": "Org unit. Matched against existing departments, or created.",
        "synonyms": ["dept", "department", "division", "team", "function",
                     "vertical", "business unit", "bu", "group", "section"],
    },
    {
        "key": "job_position", "label": "Job position", "kind": "category",
        "required": False, "group": "Organisation",
        "hint": "Role title. Matched against existing positions, or created.",
        "synonyms": ["designation", "title", "job title", "role", "position",
                     "post", "grade", "job position", "profile", "job role"],
    },
    {
        "key": "work_location", "label": "Work location", "kind": "category",
        "required": False, "group": "Organisation",
        "hint": "Office or site.",
        "synonyms": ["location", "work location", "office", "branch", "site",
                     "base location", "city", "place of posting"],
    },
    {
        "key": "employee_type", "label": "Employment type", "kind": "category",
        "required": False, "group": "Organisation",
        "hint": "Full time, part time, intern, contract.",
        "synonyms": ["type", "employee type", "employment type", "emp type",
                     "category", "worker type", "engagement"],
    },
    {
        "key": "manager_email", "label": "Manager (email)", "kind": "email",
        "required": False, "group": "Organisation",
        "hint": "Reporting manager, matched by their work email.",
        "synonyms": ["manager", "manager email", "reporting manager",
                     "reports to", "supervisor", "manager mail"],
    },
    {
        "key": "date_of_joining", "label": "Date of joining", "kind": "date",
        "required": True, "group": "Employment",
        "hint": "The day employment started.",
        "synonyms": ["doj", "date of joining", "joining date", "date of join",
                     "joined", "joined on", "start date", "hire date",
                     "date of employment", "doe", "joining", "commencement"],
    },
    {
        "key": "date_of_birth", "label": "Date of birth", "kind": "date",
        "required": False, "group": "Personal",
        "hint": "Used only to sanity-check the record.",
        "synonyms": ["dob", "date of birth", "birth date", "birthday", "born"],
    },
    {
        "key": "gender", "label": "Gender", "kind": "category",
        "required": False, "group": "Personal",
        "hint": "M, F or O.",
        "synonyms": ["gender", "sex", "m/f"],
    },
    {
        "key": "wage", "label": "Monthly wage", "kind": "money",
        "required": True, "group": "Pay",
        "hint": "Monthly gross on the contract. An annual figure is scaled.",
        "synonyms": ["salary", "sal", "wage", "wages", "monthly salary",
                     "sal pm", "monthly", "pay", "basic", "gross", "ctc",
                     "annual ctc", "package", "remuneration", "compensation",
                     "fixed pay", "monthly pay", "cost to company", "stipend"],
    },
    {
        "key": "contract_start", "label": "Contract start", "kind": "date",
        "required": False, "group": "Pay",
        "hint": "Defaults to the joining date when absent.",
        "synonyms": ["contract start", "contract from", "effective from",
                     "agreement start", "wef"],
    },
    {
        "key": "contract_end", "label": "Contract end", "kind": "date",
        "required": False, "group": "Pay",
        "hint": "Leave empty for an open-ended contract.",
        "synonyms": ["contract end", "contract to", "end date", "valid till",
                     "agreement end", "expiry"],
    },
    {
        "key": "bank_account_number", "label": "Bank account", "kind": "code",
        "required": False, "group": "Bank",
        "hint": "Needed before a payrun can pay this person.",
        "synonyms": ["account", "a/c", "a/c no", "ac no", "acct", "acct no",
                     "account no", "account number", "bank ac", "bank account",
                     "bank a/c", "salary account"],
    },
    {
        "key": "bank_ifsc", "label": "IFSC code", "kind": "ifsc",
        "required": False, "group": "Bank",
        "hint": "Eleven characters, fifth is always zero.",
        "synonyms": ["ifsc", "ifsc code", "branch code", "rtgs code",
                     "neft code"],
    },
    {
        "key": "pan_number", "label": "PAN", "kind": "pan",
        "required": False, "group": "Bank",
        "hint": "Permanent account number.",
        "synonyms": ["pan", "pan no", "pan number", "pan card",
                     "income tax no", "it pan"],
    },
]

FIELDS_BY_KEY = {f["key"]: f for f in TARGET_FIELDS}
FIELD_KEYS = [f["key"] for f in TARGET_FIELDS]

#: Fields that must be satisfied for a row to become an employee. `full_name`
#: satisfies `first_name` on its own, because splitting it is a transform
#: rather than a second column -- see `mapper.missing_required`.
REQUIRED_KEYS = [f["key"] for f in TARGET_FIELDS if f["required"]]

#: Which target fields a profiled column is *allowed* to be. This is the table
#: that lets hard evidence overrule the model: a column of email addresses
#: cannot be a joining date no matter how confidently something says so.
KIND_COMPATIBILITY = {
    "email": {"work_email", "personal_email", "manager_email"},
    "phone": {"work_phone"},
    "date": {"date_of_joining", "date_of_birth", "contract_start", "contract_end"},
    "money": {"wage"},
    "ifsc": {"bank_ifsc"},
    "pan": {"pan_number"},
    "name": {"full_name", "first_name", "last_name", "job_position",
             "department", "work_location"},
    "categorical": {"department", "job_position", "work_location",
                    "employee_type", "gender"},
    "boolean": {"gender", "employee_type"},
    "integer": {"bank_account_number", "employee_code", "wage"},
    "decimal": {"wage"},
    "text": set(FIELD_KEYS),
    "empty": set(),
}


# ==========================================================================
# Normalising and comparing header labels
# ==========================================================================

_ABBREV = {
    "no": "number", "nos": "number", "num": "number", "dept": "department",
    "emp": "employee", "empl": "employee", "mob": "mobile", "tel": "telephone",
    "addr": "address", "desig": "designation", "dt": "date", "amt": "amount",
    "sal": "salary", "acct": "account", "ac": "account", "yr": "year",
    "mgr": "manager", "id": "identifier",
}


def normalise(label):
    """
    'A/C No.' -> 'account number'.  'ANNUAL_CTC' -> 'annual ctc'.

    Splits camelCase, flattens every separator to a space, drops parenthetical
    units, and expands the abbreviations that actually recur in HR sheets.
    """
    s = (label or "").strip()
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s)
    s = s.lower()
    s = re.sub(r"[\(\[].*?[\)\]]", " ", s)     # "Sal (pm)" -> "sal"
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = [t for t in s.split() if t]
    tokens = [_ABBREV.get(t, t) for t in tokens]
    return " ".join(tokens)


def tokens(label):
    return [t for t in normalise(label).split() if t]


def levenshtein(a, b):
    """Plain DP edit distance. Header labels are short; this is never hot."""
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _similarity(a, b):
    if not a or not b:
        return 0.0
    return 1.0 - levenshtein(a, b) / max(len(a), len(b))


def match_header(header, profile=None, fields=None):
    """
    Rank target fields for one column header, on the label alone.

    This is the lexical voter. It knows nothing about the values -- the profile
    is used only to *discount* a match that the data contradicts, never to
    make one, so that the two voters stay genuinely independent and their
    agreement means something.
    """
    fields = fields or TARGET_FIELDS
    norm = normalise(header)
    if not norm:
        return []
    toks = set(norm.split())
    best_kind = (profile or {}).get("best_kind")

    out = []
    for field in fields:
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

        # The data gets a veto but not a vote: a strong label match on a column
        # whose values are the wrong shape is demoted rather than dropped, so
        # the disagreement stays visible in the plan instead of disappearing.
        if best_kind and best_kind in KIND_COMPATIBILITY:
            allowed = KIND_COMPATIBILITY[best_kind]
            if allowed and field["key"] not in allowed:
                score *= 0.25
                why += "; values do not look like %s" % field["label"].lower()

        out.append({"field": field["key"], "confidence": round(min(score, 0.99), 3),
                    "reason": why})

    out.sort(key=lambda c: c["confidence"], reverse=True)
    return out[:3]


def shape_candidates(profile):
    """
    The value-shape voter: what could this column be, judged only by its data?

    Deliberately blunt. It proposes every field its detected kind permits, at a
    confidence that reflects how distinctive that kind is -- an IFSC code can
    only be one thing, a category could be four. Its value is not precision; it
    is that it is computed from the cells and therefore cannot be talked out of
    its answer by a persuasive header or a confident model.
    """
    kind = profile.get("best_kind")
    allowed = KIND_COMPATIBILITY.get(kind) or set()
    if not allowed or kind in ("text", "empty"):
        return []

    top = (profile.get("types") or [{}])[0].get("confidence", 0.5)
    # Splitting the confidence across the possibilities is the honest move: one
    # candidate means the shape identifies the field, six means it narrows it.
    per = top * (1.0 if len(allowed) == 1 else max(0.35, 1.0 / len(allowed) ** 0.5))

    out = []
    for key in allowed:
        conf = per
        # Within a kind, the flags break ties the shape alone cannot.
        if key == "wage" and "looks_annual" in (profile.get("flags") or []):
            conf = min(0.95, conf + 0.15)
        out.append({
            "field": key,
            "confidence": round(min(conf, 0.95), 3),
            "reason": profile.get("evidence", "") or ("values look like %s" % kind),
        })
    out.sort(key=lambda c: c["confidence"], reverse=True)
    return out[:4]
