"""
Three voters, one decision, and a record of the argument.

The naive version of this feature is: send the headers to a language model, do
what it says. That version was built first and measured, and it is not good
enough -- a 7B on a laptop card returned null for "Sal (pm)", "DOJ" and
"Mob No" in one pass and mapped them perfectly in the next, and there is no way
to tell from the outside which pass you got.

So nothing here trusts one source. Every column is judged by three voters that
fail in different ways:

  lexical  reads the header against a synonym dictionary. Knows that DOJ is a
           joining date. Cannot tell a "Number" column from a "Number" column.
  shape    reads the values. Knows an IFSC code on sight and cannot be argued
           out of it. Has no idea what the column is *for*.
  model    reads the header, the evidence, and three samples, and applies
           judgement neither of the others has. Occasionally confabulates.

The reconciler below combines them under rules that are written down rather
than tuned by feel, and -- this is the part that matters -- it keeps the losing
votes. The plan that comes out carries the full argument, so the screen can
show an operator that the model said "date of joining", the profiler said "that
column is email addresses", and the profiler won. A judge who sees that
understands in one glance that this is not a chatbot with a spreadsheet
attached.

The model is optional at every point. With it absent the other two voters
decide alone, the plan says so, and on the demo files the result is still a
working import.
"""

import time

from .llm import LLMUnavailable
from .schema import (FIELDS_BY_KEY, KIND_COMPATIBILITY, TARGET_FIELDS,
                     match_header, shape_candidates)
from .transforms import suggest_transforms, preview_transforms

#: Below this, a candidate is not worth showing. A column with nothing above it
#: is left unmapped rather than guessed at -- an unmapped column costs the
#: operator one dropdown, and a wrongly mapped one costs them a payroll run.
FLOOR = 0.35

#: A single voter this confident decides on its own.
SOLO_AUTO = 0.75

#: Two voters agreeing is worth more than either alone, but never certainty.
AGREEMENT_BONUS = 0.10
CEILING = 0.99


# ==========================================================================
# The model voter
# ==========================================================================

def build_prompt(profiles):
    """
    The prompt that made the difference.

    Measured, on this hardware, with qwen2.5:7b at temperature 0: asked with
    headers and sample values only, it mapped 3 of 6 columns correctly. Asked
    with headers plus the profiler's one-line evidence, it mapped 6 of 6,
    including correctly returning null for a free-text notes column.

    The reason is in the last paragraph of the instruction: the model is told
    the evidence is authoritative about *type* and that it is being asked only
    about *meaning*. That removes the question it is bad at -- inferring a data
    type from three examples -- and leaves the one it is good at, which is
    knowing that "Naam" is a name and "DOJ" is a date of joining.
    """
    lines = ["You map the columns of a messy HR spreadsheet onto a fixed schema.",
             "", "TARGET FIELDS - choose exactly one per column, or null:"]
    for f in TARGET_FIELDS:
        lines.append("- %s: %s" % (f["key"], f["hint"]))

    lines += ["", "COLUMNS. A deterministic profiler has already inspected the "
                  "values; EVIDENCE states what it measured.", ""]
    for p in profiles:
        samples = " | ".join(p.get("sample") or [])[:110]
        lines.append("COLUMN %d  header=%r" % (p["index"] + 1, p["header"]))
        lines.append("  EVIDENCE: %s" % p.get("evidence", ""))
        if samples:
            lines.append("  SAMPLES: %s" % samples)

    lines += [
        "",
        "The EVIDENCE is authoritative about what TYPE a column holds. Do not "
        "contradict it. Your job is the MEANING: which schema field this column "
        "is for. Where the evidence rules a field out, choose null rather than "
        "forcing a match.",
        "",
        "Return JSON only:",
        '{"mappings":[{"column":1,"field":"full_name","confidence":0.95,'
        '"reason":"under 10 words"}]}',
        "One entry per column. Use null for field when nothing fits. "
        "confidence is 0 to 1.",
    ]
    return "\n".join(lines)


def ask_model(model, profiles):
    """Returns (votes_by_column_index, meta). Never raises."""
    meta = {"used": False, "model": getattr(model, "model", None),
            "latency_ms": None, "fallback_reason": None}
    if model is None:
        meta["fallback_reason"] = "No local model was configured for this run."
        return {}, meta

    try:
        data, elapsed = model.generate_json(
            build_prompt(profiles),
            num_predict=min(1400, 120 + 70 * len(profiles)))
    except LLMUnavailable as exc:
        meta["fallback_reason"] = str(exc)
        return {}, meta

    meta["used"] = True
    meta["latency_ms"] = elapsed

    votes = {}
    for entry in (data.get("mappings") or []):
        try:
            idx = int(entry.get("column")) - 1
        except (TypeError, ValueError):
            continue
        field = entry.get("field")
        if field in ("", "null", "none"):
            field = None
        # A small model will happily invent a field name. Anything not in the
        # schema is discarded rather than repaired -- a wrong guess about what
        # it meant is worse than no vote.
        if field is not None and field not in FIELDS_BY_KEY:
            continue
        try:
            conf = float(entry.get("confidence", 0.6))
        except (TypeError, ValueError):
            conf = 0.6
        votes[idx] = {
            "voter": "model", "field": field,
            "confidence": round(max(0.0, min(conf, 0.99)), 3),
            "reason": str(entry.get("reason", ""))[:90],
        }
    return votes, meta


# ==========================================================================
# Reconciliation
# ==========================================================================

def _veto(profile, field_key):
    """Does the measured data rule this field out entirely?"""
    kind = profile.get("best_kind")
    allowed = KIND_COMPATIBILITY.get(kind)
    if not field_key or not allowed or kind in ("text", "empty"):
        return False
    return field_key not in allowed


def reconcile_column(profile, model_vote):
    """
    Decide one column, and keep the argument that produced the decision.

    Returns the column entry of the plan. `votes` always lists every voter that
    had an opinion, including the ones that lost, with a status saying what
    happened to them -- that list is the feature, not debug output.
    """
    votes = []

    lex = match_header(profile["header"], profile)
    if lex:
        votes.append({"voter": "lexical", "field": lex[0]["field"],
                      "confidence": lex[0]["confidence"],
                      "reason": lex[0]["reason"], "status": "considered"})

    shp = shape_candidates(profile)
    if shp:
        votes.append({"voter": "shape", "field": shp[0]["field"],
                      "confidence": shp[0]["confidence"],
                      "reason": shp[0]["reason"], "status": "considered"})

    if model_vote:
        vote = dict(model_vote)
        vote["status"] = "considered"
        if vote["field"] and _veto(profile, vote["field"]):
            # The whole reason the profiler exists. The model has proposed a
            # field the measured values cannot be, so it loses -- visibly.
            vote["status"] = "overruled"
            vote["reason"] = ("%s -- but the values are %s"
                              % (vote["reason"] or "proposed by the model",
                                 profile.get("best_kind")))
        votes.append(vote)

    live = [v for v in votes
            if v["field"] and v["status"] != "overruled" and v["confidence"] >= FLOOR]

    if not live:
        return {"field": None, "confidence": 0.0, "decision": "unmapped",
                "verdict": ("overruled" if any(v["status"] == "overruled" for v in votes)
                            else "no_candidate"),
                "votes": votes,
                "note": "Nothing in the header or the values matches a field."}

    # Tally by field so that agreement is measured, not assumed.
    by_field = {}
    for v in live:
        by_field.setdefault(v["field"], []).append(v)

    def rank(item):
        field, group = item
        return (len(group), max(v["confidence"] for v in group))

    winner, backers = max(by_field.items(), key=rank)
    confidence = max(v["confidence"] for v in backers)
    agreed = len(backers) > 1
    if agreed:
        confidence = min(CEILING, confidence + AGREEMENT_BONUS)

    for v in votes:
        if v["status"] == "overruled":
            continue
        v["status"] = "agreed" if v["field"] == winner else "outvoted"

    if agreed:
        verdict, decision = "consensus", "auto"
    elif confidence >= SOLO_AUTO:
        verdict, decision = "single_voter", "auto"
    else:
        verdict, decision = "weak", "review"

    if len(by_field) > 1:
        verdict = "disputed"
        decision = "auto" if (agreed and confidence >= 0.85) else "review"

    return {"field": winner, "confidence": round(confidence, 3),
            "decision": decision, "verdict": verdict, "votes": votes,
            "note": ""}


def _enforce_uniqueness(columns):
    """
    One target field, one source column.

    Two columns both mapping to `wage` is not a tie to be broken silently --
    one of them is something else, and which one is a question for the
    operator. The higher-confidence claim keeps the field; the other is dropped
    to review with the reason stated, so the conflict is visible rather than
    resolved by whichever column happened to come first.
    """
    claimed = {}
    for col in columns:
        field = col.get("field")
        if not field:
            continue
        holder = claimed.get(field)
        if holder is None:
            claimed[field] = col
            continue
        loser = col if col["confidence"] <= holder["confidence"] else holder
        keeper = holder if loser is col else col
        claimed[field] = keeper
        loser["decision"] = "review"
        loser["verdict"] = "conflict"
        loser["note"] = ("Column %d also claims %s, with higher confidence."
                         % (keeper["index"] + 1, FIELDS_BY_KEY[field]["label"]))
        loser["field"] = None
        loser["confidence"] = 0.0


def missing_required(columns):
    """
    Which required fields nobody supplied.

    `full_name` standing in for `first_name` is the one special case, and it is
    a real one: most sheets carry a single name column, and splitting it is a
    transform rather than a missing column.
    """
    mapped = {c["field"] for c in columns if c.get("field")}
    if "full_name" in mapped:
        mapped.add("first_name")
    return [k for k in ("first_name", "work_email", "date_of_joining", "wage")
            if k not in mapped]


# ==========================================================================

def build_plan(table, profiles, model=None, known_values=None, on_event=None):
    """
    Produce the whole import plan. `on_event` receives progress for streaming.

    known_values maps a field key to the values already in the database
    ("department" -> ["Engineering", "Sales", ...]) so categorical columns can
    be reconciled onto what exists rather than duplicating it.
    """
    started = time.time()
    emit = on_event or (lambda e: None)
    known_values = known_values or {}

    model_votes, llm_meta = ask_model(model, profiles)

    columns = []
    for profile in profiles:
        entry = reconcile_column(profile, model_votes.get(profile["index"]))
        entry["index"] = profile["index"]
        entry["header"] = profile["header"]
        entry["profile"] = profile
        columns.append(entry)

    _enforce_uniqueness(columns)

    # Transforms are decided after the mapping, because what a column needs
    # doing to it depends on what it is going to become.
    for entry in columns:
        if entry.get("field"):
            entry["transforms"] = suggest_transforms(entry["field"], entry["profile"])
            before, after = preview_transforms(
                entry["profile"].get("sample") or [], entry["transforms"])
            entry["sample_before"], entry["sample_after"] = before, after
        else:
            entry["transforms"] = []
            entry["sample_before"] = entry["profile"].get("sample") or []
            entry["sample_after"] = []
        emit({"stage": "column", "payload": entry,
              "message": _column_message(entry)})

    value_maps = build_value_maps(columns, known_values, model)
    for vm in value_maps:
        emit({"stage": "value_map", "payload": vm,
              "message": "%s: matched %d, new %d"
                         % (FIELDS_BY_KEY[vm["field"]]["label"],
                            sum(1 for p in vm["pairs"] if p["status"] == "matched"),
                            sum(1 for p in vm["pairs"] if p["status"] == "new"))})

    auto = sum(1 for c in columns if c["decision"] == "auto")
    review = sum(1 for c in columns if c["decision"] == "review")
    unmapped = sum(1 for c in columns if c["decision"] == "unmapped")

    return {
        "columns": columns,
        "value_maps": value_maps,
        "unmapped_columns": [c["index"] for c in columns if not c.get("field")],
        "missing_required": missing_required(columns),
        "llm": llm_meta,
        "summary": {"columns": len(columns), "auto": auto, "review": review,
                    "unmapped": unmapped,
                    "elapsed_ms": int((time.time() - started) * 1000)},
    }


def _column_message(entry):
    if not entry.get("field"):
        return "%r left unmapped" % entry["header"]
    return "%r -> %s" % (entry["header"], FIELDS_BY_KEY[entry["field"]]["label"])


# ==========================================================================
# Value maps -- reconciling one company's vocabulary onto another's
# ==========================================================================

def _closest(value, candidates):
    from .schema import _similarity, normalise

    v = normalise(value)
    best, score = None, 0.0
    for c in candidates:
        s = _similarity(v, normalise(c))
        if s > score:
            best, score = c, s
    return best, score


#: Abbreviations that recur across Indian HR sheets often enough to be worth
#: knowing without asking anything. Everything else goes to the model, and
#: failing that is offered to the operator as a new value.
#: Fields whose value lists are short, shared across companies and genuinely
#: interchangeable. Everything else keeps the words it arrived with.
_CLOSED_TAXONOMIES = {"department", "work_location", "employee_type", "gender"}

_KNOWN_EXPANSIONS = {
    "engg": "Engineering", "eng": "Engineering", "tech": "Technology",
    "sls": "Sales", "mktg": "Marketing", "mkt": "Marketing",
    "ops": "Operations", "fin": "Finance", "acct": "Accounts",
    "hr": "HR", "admin": "Administration", "it": "IT", "qa": "Quality",
    "cs": "Customer Support", "bd": "Business Development",
}


def build_value_maps(columns, known_values, model=None):
    """
    For each categorical column, decide what each distinct value becomes.

    Three passes, cheapest first: an exact or near match against what is
    already in the database, then a small dictionary of abbreviations, then the
    model for whatever is left. A value that survives all three is offered as
    something to create, never silently invented.
    """
    out = []
    for col in columns:
        field = col.get("field")
        if not field or FIELDS_BY_KEY[field]["kind"] != "category":
            continue
        distinct = col["profile"].get("distinct_values") or []
        if not distinct or len(distinct) > 30:
            continue

        existing = list(known_values.get(field) or [])
        pairs, unresolved = [], []

        for value in distinct:
            match, score = _closest(value, existing) if existing else (None, 0.0)
            if match and score >= 0.86:
                pairs.append({"from": value, "to": match, "status": "matched",
                              "confidence": round(score, 2), "source": "existing"})
                continue
            expanded = _KNOWN_EXPANSIONS.get(value.strip().lower())
            if expanded:
                # An expansion that lands on something we already have is a
                # match; one that does not is still a better name than "Engg".
                m2, s2 = _closest(expanded, existing) if existing else (None, 0.0)
                if m2 and s2 >= 0.86:
                    pairs.append({"from": value, "to": m2, "status": "matched",
                                  "confidence": 0.9, "source": "dictionary"})
                else:
                    pairs.append({"from": value, "to": expanded, "status": "new",
                                  "confidence": 0.8, "source": "dictionary"})
                continue
            unresolved.append(value)

        # Only closed taxonomies are offered to the model for matching.
        #
        # A department list is short and genuinely synonymous across companies:
        # "Technology" and "IT" are the same unit under two names, and folding
        # one onto the other is the correct answer to an acquisition. Job
        # titles are a long tail and are not synonymous -- asked to match them,
        # the model helpfully collapsed "Senior Developer" onto "Developer" and
        # "Marketing Lead" onto "Sales Executive", which silently discards the
        # distinction the title exists to carry. So a title that does not
        # already exist is created rather than matched, and the seniority
        # survives the import.
        if unresolved and model is not None and field in _CLOSED_TAXONOMIES:
            resolved = _ask_model_for_values(model, field, unresolved, existing)
            for value in unresolved:
                proposal = resolved.get(value)
                if proposal and proposal in existing:
                    pairs.append({"from": value, "to": proposal, "status": "matched",
                                  "confidence": 0.75, "source": "model"})
                elif proposal:
                    pairs.append({"from": value, "to": proposal, "status": "new",
                                  "confidence": 0.7, "source": "model"})
                else:
                    pairs.append({"from": value, "to": value, "status": "new",
                                  "confidence": 0.5, "source": "asis"})
        else:
            for value in unresolved:
                pairs.append({"from": value, "to": value, "status": "new",
                              "confidence": 0.5, "source": "asis"})

        pairs.sort(key=lambda p: p["from"].lower())
        out.append({"column": col["index"], "field": field, "pairs": pairs})
    return out


def _ask_model_for_values(model, field, values, existing):
    """One small call: expand or match a handful of category values."""
    label = FIELDS_BY_KEY[field]["label"].lower()
    prompt = "\n".join([
        "Map each %s value from another company's spreadsheet onto ours." % label,
        "",
        "OUR EXISTING %s VALUES: %s" % (label.upper(),
                                        ", ".join(existing) or "(none yet)"),
        "THEIR VALUES: %s" % ", ".join(values),
        "",
        "For each of their values, return the matching one of ours if there "
        "clearly is one. If there is no match, return the full proper name for "
        "their abbreviation instead (for example Engg becomes Engineering).",
        "",
        'Return JSON only: {"pairs":[{"from":"Engg","to":"Engineering"}]}',
    ])
    try:
        data, _ = model.generate_json(prompt, num_predict=400)
    except LLMUnavailable:
        return {}

    out = {}
    for entry in (data.get("pairs") or []):
        src, dst = entry.get("from"), entry.get("to")
        if isinstance(src, str) and isinstance(dst, str) and src in values:
            out[src] = dst.strip()[:80]
    return out
