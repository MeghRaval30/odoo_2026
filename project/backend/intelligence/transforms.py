"""
The steps that turn a cell into a value, named so a person can approve them.

Every transform here is small, pure and reversible in description if not in
effect. That is deliberate. The alternative -- one clever function that reads
"Rs 45,000" and returns Decimal("45000") -- works just as well and cannot be
shown to anybody. Splitting it into `strip currency` then `to number` means the
screen can render two chips, the operator can click either one and see it
applied to three real cells, and the question "what is it going to do to my
data" has an answer that is not "trust it".

It also means a wrong guess is cheap to fix: the operator removes one chip
rather than abandoning the import.

`suggest_transforms` is where the profiler's measurements become actions. The
one worth pointing at is `scale`: a salary column whose median is nine hundred
thousand is proposed for division by twelve, because it is plainly annual, and
that proposal is *shown* rather than applied -- getting it wrong silently would
be a twelvefold payroll error.
"""

import re
from decimal import Decimal, InvalidOperation

from .profiler import is_blank, parse_date_value, strip_money

#: Registered by id. `apply_chain` walks these in order.
REGISTRY = {}


def transform(id, label, detail, applies_to=()):
    def wrap(fn):
        REGISTRY[id] = {"id": id, "label": label, "detail": detail,
                        "applies_to": list(applies_to), "fn": fn}
        return fn
    return wrap


def spec(id, **params):
    """A transform as it appears in a plan: id, labels, and its parameters."""
    entry = REGISTRY[id]
    return {"id": id, "label": entry["label"], "detail": _detail(entry, params),
            "params": params}


def _detail(entry, params):
    if entry["id"] == "scale" and params.get("divide_by"):
        return "Divides by %s, so an annual figure becomes monthly" % params["divide_by"]
    if entry["id"] == "parse_date" and params.get("formats"):
        return "Reads %s" % ", ".join(params["formats"][:3])
    return entry["detail"]


# ==========================================================================
# The transforms
# ==========================================================================

@transform("trim", "Trim", "Removes leading and trailing spaces")
def _trim(v, p):
    return (v or "").strip(), True, None


@transform("collapse_space", "Collapse spaces", "Reduces runs of spaces to one")
def _collapse(v, p):
    return re.sub(r"\s+", " ", (v or "")).strip(), True, None


@transform("blank_to_null", "Blanks to empty",
           "Treats NULL, NA and - as empty rather than as text")
def _blank_null(v, p):
    return ("" if is_blank(v) else v), True, None


@transform("title_case", "Title case", "Makes RAJESH KUMAR read as Rajesh Kumar",
           ("name",))
def _title(v, p):
    s = (v or "").strip()
    if not s:
        return s, True, None
    # Only reshape what is clearly mis-cased. A name already written as
    # "McDonald" or "D'Souza" is left alone rather than flattened.
    if s.isupper() or s.islower():
        return " ".join(w.capitalize() for w in s.split()), True, None
    return s, True, None


@transform("upper", "Uppercase", "Codes are stored uppercase", ("ifsc", "pan"))
def _upper(v, p):
    return (v or "").strip().upper(), True, None


@transform("strip_currency", "Strip currency",
           "Removes Rs, INR, the rupee sign, thousands commas and a trailing /-",
           ("money",))
def _strip_currency(v, p):
    if is_blank(v):
        return "", True, None
    cleaned = strip_money(v)
    if cleaned is None:
        return v, False, "not a number once currency marks were removed"
    return cleaned, True, None


@transform("to_decimal", "To number", "Stores it as a number, not text", ("money",))
def _to_decimal(v, p):
    if v in ("", None):
        return None, True, None
    try:
        return Decimal(str(v)), True, None
    except (InvalidOperation, ValueError):
        return None, False, "could not be read as a number"


@transform("scale", "Scale", "Multiplies by a fixed factor", ("money",))
def _scale(v, p):
    if v in ("", None):
        return None, True, None
    try:
        d = Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None, False, "not a number"
    divide_by = Decimal(str(p.get("divide_by") or 1))
    if divide_by == 0:
        return d, True, None
    return (d / divide_by).quantize(Decimal("0.01")), True, None


@transform("parse_date", "Read date", "Understands the formats found in this column",
           ("date",))
def _parse_date(v, p):
    if is_blank(v):
        return None, True, None
    formats = p.get("formats") or []
    parsed = parse_date_value(v, formats[0] if formats else None)
    if parsed is None:
        return None, False, "not a date this column's formats explain"
    return parsed, True, None


@transform("split_name", "Split name", "First word becomes the first name, "
                                       "the rest the last name", ("name",))
def _split_name(v, p):
    s = re.sub(r"\s+", " ", (v or "").strip())
    if not s:
        return {"first_name": "", "last_name": ""}, True, None
    parts = s.split(" ")
    if len(parts) == 1:
        return {"first_name": parts[0], "last_name": ""}, True, None
    return {"first_name": parts[0], "last_name": " ".join(parts[1:])}, True, None


@transform("normalize_phone", "Normalise phone",
           "Drops +91, spaces and dashes, keeping the ten digits", ("phone",))
def _normalize_phone(v, p):
    digits = re.sub(r"\D", "", (v or ""))
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not digits:
        return "", True, None
    if len(digits) != 10:
        return digits, False, "does not have ten digits"
    return digits, True, None


@transform("strip_non_digits", "Digits only", "Keeps only the digits", ("code",))
def _digits(v, p):
    return re.sub(r"\D", "", (v or "")), True, None


@transform("map_values", "Apply value map",
           "Rewrites each value to the one chosen in the plan", ("category",))
def _map_values(v, p):
    mapping = p.get("mapping") or {}
    s = (v or "").strip()
    return mapping.get(s, s), True, None


@transform("default", "Fill blanks", "Uses a fixed value where the cell is empty")
def _default(v, p):
    return (p.get("value") if is_blank(v) else v), True, None


# ==========================================================================

def apply_chain(value, chain):
    """
    Run a transform chain over one cell.

    Returns (value, ok, notes). A step that cannot do its job stops the chain
    and says why, rather than passing something unusable to the next step --
    the row then surfaces as an issue with the actual reason attached instead
    of failing at the database.
    """
    current, notes = value, []
    for step in chain or []:
        entry = REGISTRY.get(step.get("id"))
        if not entry:
            continue
        try:
            current, ok, note = entry["fn"](current, step.get("params") or {})
        except Exception as exc:
            return current, False, notes + ["%s failed: %s" % (entry["label"], exc)]
        if note:
            notes.append(note)
        if not ok:
            return current, False, notes
    return current, True, notes


def preview_transforms(samples, chain):
    """Before and after for a handful of real cells, for the screen."""
    before, after = [], []
    for raw in (samples or [])[:3]:
        value, ok, _ = apply_chain(raw, chain)
        before.append(str(raw))
        if isinstance(value, dict):
            after.append(" / ".join(str(v) for v in value.values() if v))
        elif value is None:
            after.append("" if ok else "could not read")
        else:
            after.append(str(value))
    return before, after


# ==========================================================================

def suggest_transforms(field_key, profile):
    """
    Build the default chain for a column, from what the profiler measured.

    Everything proposed here is derived from the data rather than assumed from
    the field, which is why the same target field gets different chains from
    different files: a wage column of "Rs 45,000" needs the currency stripped
    and one of 1080000 needs dividing by twelve.
    """
    from .schema import FIELDS_BY_KEY

    field = FIELDS_BY_KEY.get(field_key)
    if not field:
        return []

    kind = field["kind"]
    flags = profile.get("flags") or []
    chain = [spec("trim")]

    if "has_blanks" in flags or profile.get("blank"):
        chain.append(spec("blank_to_null"))

    if kind == "name":
        chain.append(spec("collapse_space"))
        if "inconsistent_case" in flags:
            chain.append(spec("title_case"))
        if field_key == "full_name":
            chain.append(spec("split_name"))

    elif kind == "money":
        chain.append(spec("strip_currency"))
        chain.append(spec("to_decimal"))
        if "looks_annual" in flags:
            # Proposed, never silent. Getting this wrong in either direction is
            # a twelvefold error in somebody's pay, so it is a chip the
            # operator can see and remove.
            chain.append(spec("scale", divide_by=12))

    elif kind == "date":
        formats = [f for f in (profile.get("detected_date_formats") or [])
                   if f != "excel-serial"]
        chain.append(spec("parse_date", formats=formats))

    elif kind == "phone":
        chain.append(spec("normalize_phone"))

    elif kind in ("ifsc", "pan"):
        chain.append(spec("upper"))

    elif kind == "email":
        chain.append(spec("collapse_space"))

    elif kind == "category":
        chain.append(spec("collapse_space"))
        chain.append(spec("map_values", mapping={}))

    elif kind == "code":
        chain.append(spec("collapse_space"))

    return chain


def set_value_mapping(chain, mapping):
    """Fill the value map into an already-built chain, in place."""
    for step in chain or []:
        if step.get("id") == "map_values":
            step["params"] = {"mapping": mapping}
    return chain
