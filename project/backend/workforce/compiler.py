"""
An English sentence in, a rule out.

"Engineers who joined before 2022 and earn under 60,000" is how somebody
actually describes a group of people. Six dropdowns is how software usually
makes them say it. This module closes that gap, and the reason it can be
trusted to is that it never executes what the model produced -- it produces a
*proposal*, which is validated against the real filter vocabulary and the real
department names, shown to the operator as a rule they can read and edit, and
only then run by the deterministic resolver in `segments`.

That ordering is the entire safety argument. The model's output cannot do
anything on its own. The worst a confabulation can do is show somebody a rule
that says something they did not mean, next to a live count of who it matches,
which they then correct.

There is a keyword fallback underneath, because a company with no GPU should
still get something useful out of typing a sentence. It handles the shapes that
recur -- a department name, a year, an amount, a tenure, a bond -- and says
plainly that it is the one that ran.
"""

import re
from datetime import date

from intelligence.llm import LLMUnavailable, LocalModel

from .segments import clean_criteria, describe

_MONEY = re.compile(r"(?:rs\.?|inr|₹)?\s*([\d][\d,]*)\s*(k|lakh|lac|l)?\b", re.I)


def known_values():
    from core.models import Department, JobPosition, WorkLocation
    return {
        "departments": list(Department.objects.values_list("name", flat=True)),
        "job_positions": list(JobPosition.objects.values_list("name", flat=True)),
        "locations": list(WorkLocation.objects.values_list("name", flat=True)),
    }


# ==========================================================================
# The model path
# ==========================================================================

def _segment_prompt(text, known):
    return "\n".join([
        "Convert a sentence about a company's staff into a filter object.",
        "",
        "AVAILABLE FILTERS (use only these keys):",
        "  departments: list, chosen ONLY from: %s" % ", ".join(known["departments"]),
        "  job_positions: list, chosen ONLY from: %s" % ", ".join(known["job_positions"]),
        "  locations: list, chosen ONLY from: %s" % ", ".join(known["locations"]),
        "  employee_types: list from FULL_TIME, PART_TIME, INTERN, CONTRACT",
        "  wage_min / wage_max: monthly rupees, a number",
        "  joined_before / joined_after: a date, YYYY-MM-DD",
        "  tenure_months_min / tenure_months_max: whole months of service",
        "  has_bond: true or false",
        "  missing_bank_account: true",
        "  active: true or false",
        "",
        "Today is %s." % date.today().isoformat(),
        "Include only the filters the sentence actually asks for. Omit the rest.",
        "Never invent a department or job position that is not in the lists above;",
        "choose the closest one that is, or leave the key out.",
        "",
        "SENTENCE: %s" % text,
        "",
        'Return JSON only: {"criteria": {...}, "reading": "one short sentence '
        'saying how you read it"}',
    ])


def _playbook_prompt(text, known):
    return "\n".join([
        "Convert a sentence describing a standing HR reminder into a rule.",
        "",
        "TRIGGERS (pick one):",
        "  TENURE_REACHED    when somebody has served N months. "
        "trigger_params: {\"months\": N}",
        "  CONTRACT_ENDING   when a contract ends within N days. "
        "trigger_params: {\"days\": N}",
        "  BOND_EXPIRING     when a bond ends within N days. "
        "trigger_params: {\"days\": N}",
        "  PROBATION_ENDING  when probation ends within N days. "
        "trigger_params: {\"days\": N}",
        "  NO_BANK_ACCOUNT   when somebody has no bank account. trigger_params: {}",
        "",
        "ACTIONS (pick one):",
        "  NOTIFY             raise a reminder",
        "  PROPOSE_INCREMENT  raise a reminder suggesting a raise. "
        "action_params: {\"percent\": N}",
        "  FLAG_REVIEW        flag the person for review",
        "",
        "WHO it applies to goes in criteria, using only these keys:",
        "  departments (from: %s)" % ", ".join(known["departments"]),
        "  job_positions (from: %s)" % ", ".join(known["job_positions"]),
        "  employee_types (FULL_TIME, PART_TIME, INTERN, CONTRACT)",
        "  wage_min, wage_max, has_bond, missing_bank_account",
        "",
        "SENTENCE: %s" % text,
        "",
        'Return JSON only: {"name": "short name", "trigger": "...", '
        '"trigger_params": {...}, "criteria": {...}, "action": "...", '
        '"action_params": {...}, "reading": "one short sentence"}',
    ])


# ==========================================================================
# The keyword path
# ==========================================================================

def _amount(token, suffix):
    n = float(token.replace(",", ""))
    if suffix:
        s = suffix.lower()
        if s == "k":
            n *= 1000
        elif s in ("lakh", "lac", "l"):
            n *= 100000
    return n


def _heuristic_criteria(text, known):
    """
    The shapes people actually type, matched without a model.

    Not clever, and it does not need to be: it is the floor under the feature,
    and it is honest about being the floor. What it catches is a department or
    role name, a year, an amount with an "under"/"over" next to it, a tenure in
    months or years, and the word bond.
    """
    lowered = " " + text.lower() + " "
    criteria = {}

    for name in known["departments"]:
        if re.search(r"\b%s\b" % re.escape(name.lower()), lowered):
            criteria.setdefault("departments", []).append(name)
    # "engineers" should find Engineering; a bare stem match is enough here.
    if "departments" not in criteria:
        for name in known["departments"]:
            stem = name.lower()[:5]
            if len(stem) >= 4 and stem in lowered:
                criteria.setdefault("departments", []).append(name)

    for name in known["job_positions"]:
        if re.search(r"\b%s\b" % re.escape(name.lower()), lowered):
            criteria.setdefault("job_positions", []).append(name)

    for word, code in (("intern", "INTERN"), ("part time", "PART_TIME"),
                       ("part-time", "PART_TIME"), ("contractor", "CONTRACT"),
                       ("full time", "FULL_TIME"), ("full-time", "FULL_TIME")):
        if word in lowered:
            criteria.setdefault("employee_types", []).append(code)

    year = re.search(r"\b(before|after|since)\s+(\d{4})\b", lowered)
    if year:
        boundary = "%s-01-01" % year.group(2)
        criteria["joined_before" if year.group(1) == "before"
                 else "joined_after"] = boundary

    for direction, key in ((r"under|below|less than|<", "wage_max"),
                           (r"over|above|more than|at least|>", "wage_min")):
        hit = re.search(r"(?:%s)\s+%s" % (direction, _MONEY.pattern), lowered, re.I)
        if hit:
            criteria[key] = _amount(hit.group(1), hit.group(2))

    tenure = re.search(r"\b(\d+)\s*(month|year)s?\b", lowered)
    if tenure:
        months = int(tenure.group(1)) * (12 if tenure.group(2) == "year" else 1)
        criteria["tenure_months_min"] = months

    if "bond" in lowered:
        criteria["has_bond"] = "without" not in lowered and "no bond" not in lowered
    if "bank" in lowered and ("no " in lowered or "missing" in lowered
                              or "without" in lowered):
        criteria["missing_bank_account"] = True

    return criteria


# ==========================================================================

def compile_segment(text, model=None):
    """Returns a proposal. Always succeeds; `source` says which path ran."""
    known = known_values()
    model = model if model is not None else LocalModel()
    reading, source, note = "", "heuristic", None

    raw = None
    if model is not None:
        try:
            data, _ = model.generate_json(_segment_prompt(text, known),
                                          num_predict=420)
            raw = data.get("criteria") or {}
            reading = str(data.get("reading") or "")[:200]
            source = "model"
        except LLMUnavailable as exc:
            note = str(exc)

    if raw is None:
        raw = _heuristic_criteria(text, known)
        reading = ("Matched on keywords. %s"
                   % (note or "The local model was not available."))

    criteria, dropped = clean_criteria(raw)

    if dropped:
        # What the model got wrong is shown, not swallowed. A rule that quietly
        # lost a filter is a rule that matches the wrong people while reading
        # exactly as the operator intended.
        reading = ("%s Ignored: %s." % (reading, "; ".join(dropped))).strip()

    return {
        "criteria": criteria,
        "description": describe(criteria),
        "reading": reading,
        "dropped": dropped,
        "source": source,
        "confidence": 0.85 if source == "model" and not dropped else 0.6,
    }


PLAYBOOK_TRIGGERS = {"TENURE_REACHED", "CONTRACT_ENDING", "BOND_EXPIRING",
                     "PROBATION_ENDING", "NO_BANK_ACCOUNT"}
PLAYBOOK_ACTIONS = {"NOTIFY", "PROPOSE_INCREMENT", "FLAG_REVIEW"}


def compile_playbook(text, model=None):
    known = known_values()
    model = model if model is not None else LocalModel()
    source, reading, data = "heuristic", "", None

    if model is not None:
        try:
            data, _ = model.generate_json(_playbook_prompt(text, known),
                                          num_predict=460)
            source = "model"
        except LLMUnavailable:
            data = None

    if data is None:
        data = _heuristic_playbook(text, known)
        reading = "Matched on keywords; the local model was not available."

    trigger = str(data.get("trigger") or "").upper()
    if trigger not in PLAYBOOK_TRIGGERS:
        trigger = "TENURE_REACHED"
    action = str(data.get("action") or "").upper()
    if action not in PLAYBOOK_ACTIONS:
        action = "NOTIFY"

    criteria, dropped = clean_criteria(data.get("criteria") or {})
    params = data.get("trigger_params") or {}
    params = {k: v for k, v in params.items() if k in ("months", "days")}
    if trigger == "TENURE_REACHED" and "months" not in params:
        params["months"] = 6
    if trigger != "TENURE_REACHED" and trigger != "NO_BANK_ACCOUNT" \
            and "days" not in params:
        params["days"] = 30

    reading = (str(data.get("reading") or reading))[:200]
    if dropped:
        reading = ("%s Ignored: %s." % (reading, "; ".join(dropped))).strip()

    return {
        "name": str(data.get("name") or text)[:120],
        "trigger": trigger,
        "trigger_params": params,
        "criteria": criteria,
        "action": action,
        "action_params": {k: v for k, v in (data.get("action_params") or {}).items()
                          if k == "percent"},
        "description": describe(criteria),
        "reading": reading,
        "dropped": dropped,
        "source": source,
    }


def _heuristic_playbook(text, known):
    lowered = text.lower()
    trigger, params = "TENURE_REACHED", {}

    if "bond" in lowered:
        trigger, params = "BOND_EXPIRING", {"days": 60}
    elif "contract" in lowered:
        trigger, params = "CONTRACT_ENDING", {"days": 30}
    elif "probation" in lowered:
        trigger, params = "PROBATION_ENDING", {"days": 30}
    elif "bank" in lowered:
        trigger, params = "NO_BANK_ACCOUNT", {}
    else:
        tenure = re.search(r"\b(\d+)\s*(month|year)s?\b", lowered)
        params = {"months": (int(tenure.group(1)) *
                             (12 if tenure.group(2) == "year" else 1))
                  if tenure else 6}

    action = "NOTIFY"
    percent = re.search(r"(\d+)\s*%", lowered)
    if "increment" in lowered or "raise" in lowered or "increase" in lowered:
        action = "PROPOSE_INCREMENT"
    elif "review" in lowered or "flag" in lowered:
        action = "FLAG_REVIEW"

    return {
        "name": text[:80],
        "trigger": trigger,
        "trigger_params": params,
        "criteria": _heuristic_criteria(text, known),
        "action": action,
        "action_params": {"percent": int(percent.group(1))} if percent else {},
    }
