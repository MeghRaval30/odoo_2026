# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:   2026-09-05   10:00 IST   ✅ confirmed by the user
Hackathon end:     2026-09-06   10:00 IST   ✅ confirmed by the user
Session 04 closed: 2026-09-05   15:15 IST   (wall clock, `date`)
Elapsed:           ~5h 15m  /  24h
REMAINING:         ~18h 45m
Phase:             BUILD
```

**Run `date` yourself** and recompute before making any scope call.

### Scope gates — binding

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only. Touch nothing |

---

## WHERE WE ARE

**The product is complete and works end to end.** Session 04 audited it against
the source documents, found and fixed four real defects that all 158 prior tests
and four harnesses were green over, rehearsed the demo for the first time, and
drove every screen in a browser.

Sessions: 01 Michael (backend), 02 Franklin (frontend), 03 Trevor (tests,
deliverables, bug fixes), 04 Michael (audit, rehearsal, correctness fixes).

**No features from the spec are missing.** Remaining work is one requested
feature — a large dataset, deliberately deferred — and optional polish.

---

## ✅ WHAT WORKS — verified, with the command or click-path that proves it

### Four harnesses, all green at 15:10 IST

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py test          # 171 tests OK
./.venv/Scripts/python.exe verify_rules.py         # 28/28
./.venv/Scripts/python.exe smoke_api.py            # 51/51
./.venv/Scripts/python.exe manage.py seed --flush  # smoke_api dirties the DB
# probe_forms needs a live server in another terminal:
./.venv/Scripts/python.exe manage.py runserver
./.venv/Scripts/python.exe probe_forms.py          # 26/26
```

`npm run build` clean. **Always `seed --flush` after `smoke_api.py`** (B-010).

> **Do not start the server with `--noreload`.** Session 04 did, then spent time
> chasing a "bug" that was the server holding pre-fix code. See B-015.

### Driven by hand in a browser this session

**All 18 routes** render real content — no "Not found", no error banner, and an
instrumented sweep recorded **zero failed network requests**.

**The payrun flow, clicked end to end as admin:**

| Step | Observed |
|---|---|
| Wizard step 1 → 2 | **3 payruns before the Create click, 4 after** — steps 1 and 2 create nothing |
| Step 2 | 20 employees, contract resolved for the period (Aarav → 01 Jan 2026, ₹85,000) |
| Before Compute | **Validate button disabled** |
| Compute | `Pre-validation checks — 0 error(s), 2 warning(s)`, shown **before** Validate |
| Validate → Mark Paid | State advances; at PAID all three action buttons disabled |
| Send Payslips | "20 payslip(s) sent, 0 skipped" |
| Payslip PDF | 200, `application/pdf`, 77 KB, valid `%PDF-` header |

**Role scoping:** as `john@oxp.com` the Payroll menu is absent and all five
permission flags are false. **Attendance widget:** `out` → Check In → `in` with
a live session → Check Out.

**Time off (Scenario B):** Comp Off refused with the server's exact wording,
balance table reads 20 / 0 / 20, approving Priya's 08 Mar row moves her
allocation to **20 / 2 / 18**.

### Seed evidence — live, not hardcoded

| Payrun | Net | Why it matters |
|---|---|---|
| Dec 2025 | ₹14,73,360 | Lower than Jan — two employees resolve to older, cheaper contracts |
| Jan 2026 | ₹14,82,320 | |
| Feb 2026 | ₹15,58,668 | Higher — February overtime reached payroll |

Feb filtered to Engineering alone: **₹5,03,589**. Worked days are realistic in
every period (Dec 18–23 of 23, Jan 18–21 of 21, Feb 17–20 of 20).

Counts: 22 employees, 24 contracts, 1,746 attendance, 11 leave requests,
3 payruns, 60 payslips, 960 lines, 6 warnings.

---

## ❌ WHAT IS BROKEN

**Nothing known.** All four harnesses green, build clean, and every flow above
was driven by hand after the last commit.

---

## 🚧 WHAT IS HALF-DONE

**Nothing in the code.** Working tree clean, every branch merged into `main`,
`main` pushed.

---

## ⬜ NOT STARTED

### 1. A 200–300 employee dataset — requested, deferred on purpose

The user asked for a large roster to demonstrate scalability, then said: *"keep
the dataset building for the end don't do it right now — let's first ensure that
the software is running perfectly and the workflow is perfect."* **That
verification is now done, so this is the next piece of work.**

Notes for whoever picks it up:

- The demo script depends on specific seeded people — **John Dsouza, Priya
  Sharma, Audrey Peterson, Anita Oliver, Meera Iyer, Aarav Mehta**. They must
  survive the expansion with their exact contracts and balances.
- The seed inserts rows one at a time. At 250 employees the attendance loop
  alone is ~20,000 inserts — use `bulk_create` or it will crawl.
- Prefer a `--employees N` flag over replacing the roster, so the demo-safe
  22-person set stays the default and the demo script stays true.
- PRD-7.2 asks for a payrun of 20 in under 5 seconds. **Measure at 250 and
  record the number** — scalability is the whole point of the exercise.

### 2. PRD success criterion 4 — the one unmet criterion

> "A payrun surfaces at least **two distinct** warnings before validation."

Only `AC_MISSING` fires (×2). The engine supports six codes — `DUPLICATE`,
`NO_CONTRACT`, `NEGATIVE_NET`, `NO_STRUCTURE`, `RULE_ERROR` — and the seed
exercises none of them. A 250-person roster with joiners and leavers naturally
produces more, so **fold this into the dataset work**.

### 3. T-075 — frontend tests

None exist. Lowest priority; `probe_forms.py` and the browser pass cover the
same ground more cheaply for a 24-hour build.

---

## ➡️ THE SINGLE NEXT ACTION

Build the large dataset (item 1), keeping the demo-critical employees intact,
and use the joiners and leavers it produces to close PRD criterion 4.

---

## ⚠️ OPEN DECISION FOR THE USER — do not act alone

The user said **"remove your commits"** and the session ended before it was
resolved. The facts, checked:

- **Every commit in the repository is authored by one of the three teammates.**
  There is no Claude-authored commit. Session 04's commits are all
  `TheTeam404 <sohampanchal2229@gmail.com>` — the user's own account.
- **Exactly one commit carries a Claude co-author trailer:** `12a632f`, the root
  scaffold commit from session 01, written before D-010 was decided. That single
  trailer is why `claude` appears in GitHub's contributor list.
- Removing it means rewriting ~117 commits and force-pushing, which would break
  the other teammates' clones and risk losing in-flight work. Force-push and
  `filter-branch` are denied in `.claude/settings.json` by design.

**Ask before touching history.** If the user confirms a rewrite, first confirm
both other teammates have pushed and are idle. It is also possible they meant
"revert session 04's code changes" — that would drop four live bug fixes, so
establish which they mean rather than guessing.

---

## LOCKED-IN CONTEXT

See `claude/context/decisions.md`. Do not reopen.

| | |
|---|---|
| **Stack** | React + Django/DRF. **SQLite, not Postgres** *(D-011)* |
| **Scope** | Full spec + 3 integration connections *(D-002)* — all built |
| **Locale** | India, ₹, PF / ESIC / PT / LWF, single company *(D-003)* |
| **Repo** | `https://github.com/MeghRaval30/odoo_2026` |
| **Git identity** | Each session commits as its own teammate *(D-009)* |
| **Commits** | No machine attribution *(D-010)*, no character tag *(D-018)* |
| **Context folder** | Updated **only** at MEGATRON LAUNCH *(D-012)* |

Contribution split at handoff: `Robo9327study` 75 · `TheTeam404` 25 ·
`MeghRaval30` 17.
