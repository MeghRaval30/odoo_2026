"""
Giving imported employees a code.

Most files arrive with an identifier of some kind, and it is almost never one
you want to keep: `FF-101` is Fieldforce's numbering, and after the migration
these people work here. So the studio asks, rather than assuming, and offers
three answers:

  keep      the file has codes and they are worth keeping (a company merging
            its own two divisions, say)
  generate  build them to a pattern, which is the usual answer
  auto      leave it to the model layer, which numbers EMP/<year>/0001 the way
            the rest of the system already does

The pattern is previewed against the real rows before anything is written,
because a numbering scheme is one of those decisions that is very cheap to get
right now and very expensive to change once payslips carry it.

Sequence numbers continue from what is already in the database rather than
restarting at one, so importing a second file does not collide with the first.
"""

import re
from datetime import date

DEFAULT_POLICY = {
    "mode": "generate",
    "prefix": "EMP",
    "separator": "/",
    "include_year": True,
    "year_source": "joining",     # or "current"
    "width": 4,
    "start": 1,
}

MODES = ("keep", "generate", "auto")


def normalise_policy(policy):
    """Fill in what the caller left out, and refuse nonsense quietly."""
    out = dict(DEFAULT_POLICY)
    out.update({k: v for k, v in (policy or {}).items() if v is not None})

    if out.get("mode") not in MODES:
        out["mode"] = "generate"

    prefix = re.sub(r"[^A-Za-z0-9_-]", "", str(out.get("prefix") or ""))[:12]
    out["prefix"] = prefix.upper() or "EMP"

    separator = str(out.get("separator") or "")
    out["separator"] = separator if separator in ("/", "-", "_", "", ".") else "/"

    try:
        out["width"] = max(1, min(8, int(out["width"])))
    except (TypeError, ValueError):
        out["width"] = 4
    try:
        out["start"] = max(1, int(out["start"]))
    except (TypeError, ValueError):
        out["start"] = 1

    out["include_year"] = bool(out.get("include_year"))
    if out.get("year_source") not in ("joining", "current"):
        out["year_source"] = "joining"
    return out


def render(policy, sequence, joining=None):
    """One code. `sequence` is 1-based within this import."""
    policy = normalise_policy(policy)
    parts = [policy["prefix"]]

    if policy["include_year"]:
        if policy["year_source"] == "joining" and isinstance(joining, date):
            parts.append(str(joining.year))
        else:
            parts.append(str(date.today().year))

    parts.append(str(sequence).zfill(policy["width"]))
    return policy["separator"].join(parts)


def describe(policy):
    policy = normalise_policy(policy)
    if policy["mode"] == "keep":
        return "Codes are taken from the file as they are."
    if policy["mode"] == "auto":
        return "Codes are numbered EMP/<year>/0001, the way the rest of the system does."
    bits = [policy["prefix"]]
    if policy["include_year"]:
        bits.append("<%s year>" % policy["year_source"])
    bits.append("0" * policy["width"])
    return "Codes look like %s." % policy["separator"].join(bits)


def next_sequence(policy):
    """
    Where this import's numbering starts.

    Continues from the highest code already issued under the same prefix, so a
    second import does not reissue the first one's numbers. Codes that do not
    fit the pattern are ignored rather than parsed hopefully -- a stray
    `EMP/OLD/7` should not push the counter to eight.
    """
    from employees.models import Employee

    policy = normalise_policy(policy)
    separator = re.escape(policy["separator"]) if policy["separator"] else ""
    pattern = re.compile(
        r"^%s%s%s(\d{%d,})$" % (
            re.escape(policy["prefix"]),
            separator,
            (r"\d{4}" + separator) if policy["include_year"] else "",
            policy["width"]))

    highest = policy["start"] - 1
    for code in Employee.objects.exclude(employee_code="").values_list(
            "employee_code", flat=True):
        match = pattern.match(code or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def assign(records, policy, existing_codes=None):
    """
    Give every record a code, in file order, skipping ones that keep theirs.

    Returns the list of codes assigned, aligned with `records`, with None where
    the record keeps whatever the file gave it. Collisions with codes already
    in the database are stepped over rather than failing the import.
    """
    policy = normalise_policy(policy)
    if policy["mode"] in ("keep", "auto"):
        return [None] * len(records)

    taken = {c.lower() for c in (existing_codes or []) if c}
    sequence = next_sequence(policy)

    codes = []
    for record in records:
        joining = record.get("date_of_joining")
        code = render(policy, sequence, joining)
        while code.lower() in taken:
            sequence += 1
            code = render(policy, sequence, joining)
        taken.add(code.lower())
        codes.append(code)
        sequence += 1
    return codes


def preview(records, policy, existing_codes=None, limit=6):
    """What the first few codes will be, for the screen."""
    codes = assign(records[:limit], policy, existing_codes)
    return [c for c in codes if c]
