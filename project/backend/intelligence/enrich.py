"""
Filling the gaps in one file from another.

A company's people data is almost never in one place. HR keeps names, roles and
joining dates; finance keeps bank accounts and PAN numbers in a spreadsheet of
its own; the two are joined by a staff id or, when nobody thought about it, by
the person's name. Asking an operator to merge them by hand in Excel before
importing is asking them to do the hard part of the migration themselves.

So when a required field has no column in the primary file, the studio offers
to fetch it from a second one. Three things have to be worked out, and only the
first is interesting:

  1. **Which columns join the two files.** Not configured -- measured. The pair
     of columns whose values overlap most, subject to both being near-unique,
     is the key. That handles a staff id, an email or a name equally well
     without being told which it is.
  2. What the supplement's other columns mean. The same three-voter mapper the
     primary file went through.
  3. Which rows matched. Reported as three numbers, because "matched 14 of 16"
     is the sentence that tells an operator whether to trust the result, and
     the two that did not match are the ones they need to go and find.

The join is computed against raw cell values rather than mapped fields, so it
works even when the joining column is not something we store -- `FF-101` is
nobody's employee code, and it is still the right key.
"""

import re

from .profiler import is_blank

#: A join key is near-unique by definition. A column where half the values
#: repeat is a department, not a key, and joining on it would multiply rows.
MIN_DISTINCT_RATIO = 0.75

#: Below this share of overlapping values the two files are not about the same
#: people and the operator should be told so rather than shown a bad join.
MIN_OVERLAP = 0.35

#: How confident a column mapping must be to be taken from a supplement.
#: Higher than the ordinary floor because nobody reviews a second file column
#: by column -- see the note in build_enrichment.
SUPPLEMENT_FLOOR = 0.6


def normalise_key(value):
    """
    The comparison form of a join value.

    Case and spacing are noise -- "FF-101" and "ff-101 " are the same key, and
    so are "Harpreet Sandhu" and "harpreet  sandhu". Punctuation is kept,
    because it is load-bearing in an id and dropping it would make FF-101 and
    FF101 collide with each other rather than match.
    """
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def _column_values(table, index):
    return [(row[index] if index < len(row) else "") for row in table.rows]


def _distinct_keys(values):
    return {normalise_key(v) for v in values if not is_blank(v)}


def score_join(primary_values, supplement_values):
    """
    How well do these two columns identify the same people?

    Overlap is measured against the smaller of the two key sets, not their
    union: a supplement covering fourteen of sixteen people is a good join, and
    dividing by the union would score it the same as one covering half.
    """
    p_keys = _distinct_keys(primary_values)
    s_keys = _distinct_keys(supplement_values)
    if not p_keys or not s_keys:
        return 0.0, 0

    p_filled = [v for v in primary_values if not is_blank(v)]
    s_filled = [v for v in supplement_values if not is_blank(v)]
    if (len(p_keys) / max(len(p_filled), 1) < MIN_DISTINCT_RATIO
            or len(s_keys) / max(len(s_filled), 1) < MIN_DISTINCT_RATIO):
        return 0.0, 0

    shared = p_keys & s_keys
    return len(shared) / min(len(p_keys), len(s_keys)), len(shared)


def detect_join(primary_table, supplement_table):
    """
    Find the column pair that links the two files.

    Returns None when nothing overlaps enough to be a join, which is a real
    answer -- it means the second file is about different people.
    """
    from .schema import _similarity, normalise

    best = None
    for p_index, p_header in enumerate(primary_table.headers):
        p_values = _column_values(primary_table, p_index)
        for s_index, s_header in enumerate(supplement_table.headers):
            s_values = _column_values(supplement_table, s_index)
            overlap, shared = score_join(p_values, s_values)
            if overlap < MIN_OVERLAP:
                continue

            # Header similarity breaks ties only. Two columns that genuinely
            # hold the same values are a join whether or not they are named
            # alike -- "Staff ID" and "Emp Code" is a common pairing -- but
            # when two candidates overlap equally, the one whose headers agree
            # is the one a person would have picked.
            affinity = _similarity(normalise(p_header), normalise(s_header))
            score = overlap + affinity * 0.05

            if best is None or score > best["_score"]:
                best = {
                    "_score": score,
                    "primary_column": p_index,
                    "primary_header": p_header,
                    "supplement_column": s_index,
                    "supplement_header": s_header,
                    "overlap": round(overlap, 3),
                    "shared": shared,
                    "confidence": round(min(0.99, overlap), 3),
                }

    if best is None:
        return None

    best.pop("_score")
    p_keys = _distinct_keys(_column_values(primary_table, best["primary_column"]))
    s_keys = _distinct_keys(_column_values(supplement_table,
                                           best["supplement_column"]))
    best["reason"] = ("%d of the %d values in %r also appear in %r"
                      % (best["shared"], len(p_keys),
                         best["primary_header"], best["supplement_header"]))
    best["matched"] = best["shared"]
    best["unmatched"] = len(p_keys) - best["shared"]
    best["unused"] = len(s_keys) - best["shared"]
    return best


def unmatched_examples(primary_table, supplement_table, join, limit=5):
    """Who did not match, by name where we can tell, for the report."""
    p_index = join["primary_column"]
    s_index = join["supplement_column"]
    s_keys = _distinct_keys(_column_values(supplement_table, s_index))

    missing = []
    for row in primary_table.rows:
        raw = row[p_index] if p_index < len(row) else ""
        if is_blank(raw) or normalise_key(raw) in s_keys:
            continue
        # Show the widest text cell alongside the key -- usually the name, and
        # a key on its own tells nobody who to go and ask about.
        label = max((c for c in row if not is_blank(c)), key=len, default="")
        missing.append({"key": str(raw).strip(),
                        "label": label.strip()[:40]})
        if len(missing) >= limit:
            break
    return missing


def build_enrichment(primary_table, supplement_table, supplement_profiles,
                     source, already_sourced, model=None, known_values=None):
    """
    Work out how a second file completes the first.

    `already_sourced` is the set of fields the primary file already provides;
    the supplement is only mapped onto what is still missing, so a second file
    that happens to carry a name column does not fight the first one for it.
    """
    from .mapper import build_plan

    join = detect_join(primary_table, supplement_table)

    plan = build_plan(supplement_table, supplement_profiles, model=model,
                      known_values=known_values or {})

    # Everything the primary already has is dropped rather than offered, and
    # the join column itself is not a field to import -- it is the key.
    columns = []
    for column in plan["columns"]:
        if join and column["index"] == join["supplement_column"]:
            column = dict(column, field=None, decision="join_key",
                          verdict="join_key",
                          note="Used to match rows against the first file.")
        elif column.get("field") in already_sourced:
            column = dict(column, field=None, decision="already_present",
                          verdict="already_present",
                          note="The first file already provides this.")
        elif (column.get("field")
              and column.get("confidence", 0) < SUPPLEMENT_FLOOR):
            # A supplement is a secondary source, and the operator is not
            # reading it column by column the way they read the first file, so
            # it is held to a higher bar. A bank sheet's "Account Type" of
            # Savings and Current scores just above the ordinary mapping floor
            # for work location, and filling everybody's office with "Savings"
            # is a worse outcome than leaving the column alone.
            #
            # The bar is a confidence, not a decision. A column can be marked
            # for review because two voters picked different runners-up while
            # still being an obvious match -- "Bank A/C Number" lands at 0.79
            # that way -- and dropping that would be throwing away the thing
            # the operator opened the second file for.
            column = dict(column, field=None, decision="unsure",
                          verdict="unsure",
                          note=("Not confident enough to take from a second "
                                "file. Map it on the first file if you need it."))
        columns.append(column)

    fields = [c["field"] for c in columns if c.get("field")]

    return {
        "source_id": source.pk,
        "name": source.name,
        "filename": source.original_filename,
        "rows": supplement_table.row_count,
        "join": join,
        "columns": columns,
        "fields": fields,
        "value_maps": plan.get("value_maps", []),
        "llm": plan.get("llm", {}),
        "unmatched_examples": (unmatched_examples(primary_table,
                                                  supplement_table, join)
                               if join else []),
    }


def build_lookup(supplement_table, enrichment):
    """
    Key -> {field: transformed value}, for the fields this supplement provides.

    Built at import time from the stored source rather than from values kept in
    the plan, so that editing the supplement's mapping takes effect and the
    plan stays small.
    """
    from .transforms import apply_chain

    join = enrichment.get("join")
    if not join:
        return {}

    key_index = join["supplement_column"]
    mapped = [c for c in enrichment.get("columns", []) if c.get("field")]

    lookup = {}
    for row in supplement_table.rows:
        raw_key = row[key_index] if key_index < len(row) else ""
        if is_blank(raw_key):
            continue
        key = normalise_key(raw_key)
        # First row wins. A supplement with the same key twice is a data
        # problem in that file, and silently taking the last one would make
        # the result depend on row order.
        if key in lookup:
            continue

        values = {}
        for column in mapped:
            index = column["index"]
            cell = row[index] if index < len(row) else ""
            if is_blank(cell):
                continue
            value, ok, _ = apply_chain(cell, column.get("transforms"))
            if ok and value not in (None, ""):
                values[column["field"]] = value
        if values:
            lookup[key] = values
    return lookup


def apply_enrichment(primary_table, records, enrichment, lookup):
    """
    Fill blanks in `records` from the supplement. Never overwrites.

    A value the primary file supplied is the one the operator saw on screen and
    approved; a supplement may only fill what was empty. Records that took a
    value carry `_enriched` so the preview can mark those cells as having come
    from the second file.
    """
    join = enrichment.get("join")
    if not join or not lookup:
        return 0

    key_index = join["primary_column"]
    filled = 0
    for record, row in zip(records, primary_table.rows):
        raw_key = row[key_index] if key_index < len(row) else ""
        extra = lookup.get(normalise_key(raw_key))
        if not extra:
            continue
        for field, value in extra.items():
            if record.get(field) in (None, "", []):
                record[field] = value
                record.setdefault("_enriched", {})[field] = enrichment["name"]
                filled += 1
    return filled
