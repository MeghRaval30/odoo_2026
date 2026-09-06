"""
What a column actually contains, decided by looking at it.

This module exists because of a measurement. Asked to map a spreadsheet's
headers onto our schema from the header names alone, a 7B model running locally
got three of six columns wrong -- it returned null for "Sal (pm)", "DOJ" and
"Mob No", which a person reads correctly at a glance. Given the same headers
*plus one sentence per column describing what the values look like*, the same
model at the same temperature got six of six right, including correctly
declining to map a free-text notes column.

That is the whole design. A small model is weak at recall and strong at
judgement, so it is never asked to recall anything. It is handed evidence and
asked what the evidence means.

The evidence is also the honest half of the feature. Every claim the profiler
makes is arithmetic over the actual cells, so it holds when the model is
switched off, and it is what overrules the model when the two disagree -- a
column of email addresses is a column of email addresses no matter how
confidently something calls it a joining date.
"""

import re
import statistics
from collections import Counter
from datetime import date, timedelta

SAMPLE_LIMIT = 400

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
_IFSC = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
_PAN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
_PHONE = re.compile(r"^(\+?91[\s-]?|0)?[6-9]\d{9}$")
_INT = re.compile(r"^-?\d+$")
_DEC = re.compile(r"^-?\d+\.\d+$")
_MONEY_MARK = re.compile(r"(^|\s)(rs\.?|inr)\s*|/-\s*$|^\s*[\u20b9$]", re.I)
_THOUSANDS = re.compile(r"^\d{1,3}(,\d{2,3})+(\.\d+)?$")

#: Blank in practice. A machine export writes NULL, a human writes "-" or "NA",
#: and treating any of them as a value poisons every statistic below.
_BLANKS = {"", "-", "--", "n/a", "na", "null", "none", "nil", "nan", ".", "?"}

DATE_FORMATS = [
    "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%m-%d-%Y",
    "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%d.%m.%Y", "%d-%m-%y", "%d/%m/%y",
]

#: Excel keeps dates as days since 1899-12-30. A bare 44000 in a date column is
#: 2020-06-18, and importing it as an integer is a data loss nobody notices.
_EXCEL_EPOCH = date(1899, 12, 30)
_EXCEL_MIN, _EXCEL_MAX = 20000, 60000

#: A monthly Indian salary above this is possible but rare; a column whose
#: median sits above it is far more likely to be annual. Deliberately generous
#: -- the transform it triggers is *proposed*, never applied silently.
ANNUAL_MEDIAN_THRESHOLD = 500000


def is_blank(v):
    return (v or "").strip().lower() in _BLANKS


def strip_money(v):
    """'Rs 45,000' / '52000/-' / '1,04,000' -> '45000'. Returns None if not numeric."""
    s = (v or "").strip()
    s = re.sub(r"(?i)^(rs\.?|inr)\s*", "", s)
    s = re.sub(r"[\u20b9$]", "", s)
    s = re.sub(r"/-\s*$", "", s)
    s = s.replace(",", "").replace(" ", "").strip()
    if _INT.match(s) or _DEC.match(s):
        return s
    return None


def parse_date_value(v, fmt=None):
    """Parse one cell as a date, trying `fmt` first, then the battery."""
    from datetime import datetime

    s = (v or "").strip()
    if not s:
        return None
    if _INT.match(s) and _EXCEL_MIN <= int(s) <= _EXCEL_MAX:
        return _EXCEL_EPOCH + timedelta(days=int(s))
    for f in ([fmt] if fmt else []) + DATE_FORMATS:
        if not f:
            continue
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            continue
    return None


# ==========================================================================
# Detectors -- each returns the fraction of the sample it explains
# ==========================================================================

def _frac(values, predicate):
    if not values:
        return 0.0
    return sum(1 for v in values if predicate(v)) / len(values)


def _date_formats_seen(values):
    from datetime import datetime

    hits = Counter()
    for v in values:
        s = v.strip()
        if _INT.match(s) and _EXCEL_MIN <= int(s) <= _EXCEL_MAX:
            hits["excel-serial"] += 1
            continue
        for f in DATE_FORMATS:
            try:
                datetime.strptime(s, f)
                hits[f] += 1
                break
            except ValueError:
                continue
    return hits


def _detect(header, values, total=None):
    """Score every kind against the non-blank sample. Highest wins."""
    # Separators are normalised to spaces first: "ANNUAL_CTC" lowercases to
    # "annual_ctc", and a word boundary finds nothing inside it because underscore is a
    # word character -- so the money check silently missed every machine export
    # in the world until this line existed.
    h = re.sub(r"[_\-.]+", " ", (header or "").lower())
    n = len(values)
    scores = {}

    scores["email"] = _frac(values, lambda v: bool(_EMAIL.match(v.strip())))
    scores["ifsc"] = _frac(values, lambda v: bool(_IFSC.match(v.strip().upper())))
    scores["pan"] = _frac(values, lambda v: bool(_PAN.match(v.strip().upper())))
    scores["phone"] = _frac(values, lambda v: bool(
        _PHONE.match(re.sub(r"[\s()-]", "", v.strip()))))

    date_hits = _date_formats_seen(values)
    # An Excel serial is a bare integer, and a monthly Indian salary is a bare
    # integer in exactly the same range -- 45000 is both a plausible wage and
    # 2023-03-15. Counting serials as confidently as a parsed date read every
    # such salary column as a date, and since KIND_COMPATIBILITY lets a date be
    # a contract end, the column then mapped to one. So a serial only carries
    # its full weight when the header agrees it is a date; otherwise it is a
    # weak signal that a real format string outranks.
    header_date = bool(re.search(
        r"(date|doj|dob|dt|day|joining|joined|birth|start|end|expiry|"
        r"valid|from|till|until)", h))
    serials = date_hits.get("excel-serial", 0)
    parsed = sum(v for k, v in date_hits.items() if k != "excel-serial")
    weight = 1.0 if header_date else 0.35
    scores["date"] = ((parsed + weight * serials) / n) if n else 0.0

    money_marked = _frac(values, lambda v: bool(_MONEY_MARK.search(v)) or
                         bool(_THOUSANDS.match(v.strip())))
    numeric = _frac(values, lambda v: strip_money(v) is not None)
    header_money = bool(re.search(
        r"\b(sal|salary|wage|ctc|pay|basic|gross|net|amount|cost|stipend|"
        r"remuneration|package|compensation)\b", h))
    if numeric > 0.8 and (money_marked > 0.15 or header_money):
        scores["money"] = min(0.99, numeric * (0.75 + money_marked * 0.25 +
                                               (0.2 if header_money else 0)))
    else:
        scores["money"] = 0.0

    scores["integer"] = _frac(values, lambda v: bool(_INT.match(v.strip())))
    scores["decimal"] = _frac(values, lambda v: bool(_DEC.match(v.strip())))

    # Every money value is also an integer, so on raw counts "integer" wins the
    # tie and a salary column reads as an id. Money is the more specific claim
    # and the evidence for it -- a currency mark, thousands grouping, or a
    # header that says salary -- is evidence a plain integer does not have.
    if scores["money"] > 0.75:
        scores["integer"] = min(scores["integer"], scores["money"] - 0.05)
        scores["decimal"] = min(scores["decimal"], scores["money"] - 0.05)

    # Same tie, other direction: an Excel serial date column really is a column
    # of integers, so on raw counts the two score identically and the more
    # specific reading loses on a coin flip. A header that says "joining date"
    # settles it.
    if header_date and scores["date"] > 0.75:
        scores["integer"] = min(scores["integer"], scores["date"] - 0.05)
    scores["boolean"] = _frac(values, lambda v: v.strip().lower() in
                              {"y", "n", "yes", "no", "true", "false", "0", "1"})

    # A name is 2-3 alphabetic tokens and nearly always unique. Distinctness is
    # what separates it from a job title, which has the same shape and repeats.
    def _nameish(v):
        toks = v.strip().split()
        return (1 <= len(toks) <= 4 and
                all(re.match(r"^[A-Za-z][A-Za-z.'-]*$", t) for t in toks))
    name_shape = _frac(values, _nameish)
    distinct_ratio = len(set(v.strip().lower() for v in values)) / n if n else 0
    scores["name"] = name_shape * (0.35 + 0.65 * distinct_ratio)

    distinct = len(set(v.strip().lower() for v in values))
    if n >= 4 and distinct <= 25 and distinct_ratio < 0.6:
        scores["categorical"] = 0.6 + 0.35 * (1 - distinct_ratio)
    else:
        scores["categorical"] = 0.0

    scores["text"] = 0.25  # the floor; anything is text if nothing else fits

    fill_ratio = n / max(total or n, 1)
    if fill_ratio < 0.5:
        for weak in ("name", "categorical"):
            scores[weak] *= fill_ratio

    return scores, date_hits, distinct, distinct_ratio


# ==========================================================================

def profile_column(index, header, raw_values):
    values = [v for v in (raw_values or []) if not is_blank(v)]
    sample_pool = values[:SAMPLE_LIMIT]
    total = len(raw_values or [])
    blank = total - len(values)

    if not sample_pool:
        return {
            "index": index, "header": header, "non_null": 0, "blank": blank,
            "total": total, "distinct": 0, "distinct_ratio": 0.0,
            "min_len": 0, "max_len": 0, "types": [], "best_kind": "empty",
            "detected_date_formats": [], "sample": [],
            "numeric_min": None, "numeric_max": None, "numeric_median": None,
            "evidence": "empty in every row",
            "flags": ["all_blank"],
        }

    scores, date_hits, distinct, distinct_ratio = _detect(
        header, sample_pool, total)
    ranked = sorted(((k, round(v, 3)) for k, v in scores.items() if v > 0.05),
                    key=lambda kv: kv[1], reverse=True)
    best_kind = ranked[0][0] if ranked else "text"

    lengths = [len(v.strip()) for v in sample_pool]
    numbers = [float(strip_money(v)) for v in sample_pool if strip_money(v) is not None]

    flags = []
    if blank:
        flags.append("has_blanks")
    if distinct < len(sample_pool):
        flags.append("has_duplicates")
    if len([f for f in date_hits if f != "excel-serial"]) > 1:
        flags.append("mixed_date_formats")
    if any(v != v.strip() for v in sample_pool):
        flags.append("leading_trailing_space")
    if best_kind in ("name", "categorical"):
        cased = [v.strip() for v in sample_pool if v.strip()]
        if any(c.isupper() for c in cased) and any(c.islower() for c in cased):
            flags.append("inconsistent_case")
    median = statistics.median(numbers) if numbers else None
    if best_kind == "money" and median and median > ANNUAL_MEDIAN_THRESHOLD:
        flags.append("looks_annual")

    profile = {
        "index": index,
        "header": header,
        "non_null": len(values),
        "blank": blank,
        "total": total,
        "distinct": distinct,
        "distinct_ratio": round(distinct_ratio, 3),
        "min_len": min(lengths),
        "max_len": max(lengths),
        "types": [{"kind": k, "confidence": v} for k, v in ranked[:4]],
        "best_kind": best_kind,
        "detected_date_formats": [f for f, _ in date_hits.most_common()],
        "sample": [v.strip()[:40] for v in sample_pool[:3]],
        "distinct_values": (sorted(set(v.strip() for v in sample_pool))[:30]
                            if distinct <= 30 else []),
        "numeric_min": min(numbers) if numbers else None,
        "numeric_max": max(numbers) if numbers else None,
        "numeric_median": median,
        "flags": flags,
    }
    profile["evidence"] = describe(profile)
    return profile


def describe(p):
    """
    One ASCII sentence, under ~120 characters, stating what was measured.

    This string is doing two jobs at once and both matter: it is rendered in
    the UI beside the column so an operator can check the machine's reasoning,
    and it is pasted into the model's prompt as the evidence it reasons over.
    Writing it once for both is deliberate -- if the operator and the model are
    shown different descriptions of the same column, only one of them can be
    debugging the actual behaviour.
    """
    kind = p["best_kind"]
    bits = []

    if kind == "money":
        bits.append("currency-like")
        if p["numeric_min"] is not None:
            bits.append("values %d to %d" % (p["numeric_min"], p["numeric_max"]))
        if "looks_annual" in p["flags"]:
            bits.append("median %d, high for a monthly figure" % p["numeric_median"])
    elif kind == "date":
        fmts = [f for f in p["detected_date_formats"]]
        bits.append("dates")
        if fmts:
            bits.append("%d format%s (%s)" % (len(fmts), "" if len(fmts) == 1 else "s",
                                              ", ".join(fmts[:3])))
    elif kind == "name":
        bits.append("person-name shaped, %d to %d chars" % (p["min_len"], p["max_len"]))
    elif kind == "categorical":
        vals = p.get("distinct_values") or []
        bits.append("%d repeated values" % p["distinct"])
        if vals:
            bits.append("e.g. %s" % ", ".join(vals[:4]))
    elif kind in ("email", "phone", "pan", "ifsc"):
        bits.append("%s format" % kind)
    elif kind in ("integer", "decimal"):
        bits.append("numeric")
        if p["numeric_min"] is not None:
            bits.append("%d to %d" % (p["numeric_min"], p["numeric_max"]))
    elif kind == "boolean":
        bits.append("yes/no flag")
    else:
        bits.append("free text, %d to %d chars" % (p["min_len"], p["max_len"]))

    bits.append("%d of %d filled" % (p["non_null"], p["total"]))
    if p["distinct_ratio"] >= 0.98 and p["non_null"] > 3:
        bits.append("all distinct")
    elif "has_duplicates" in p["flags"] and kind not in ("categorical", "boolean"):
        bits.append("%d distinct" % p["distinct"])

    return ", ".join(bits)[:150]


def profile_table(table):
    """Profile every column of a ParsedTable, left to right."""
    out = []
    for i, header in enumerate(table.headers):
        column = [(row[i] if i < len(row) else "") for row in table.rows]
        out.append(profile_column(i, header, column))
    return out
