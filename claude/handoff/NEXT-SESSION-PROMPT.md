# BRIEFING FOR THE NEXT SESSION

**Written by:** Michael (session 04) · 2026-09-05, 15:20 IST
**You are:** FRANKLIN (session 05)
**Handoff tag:** `handoff-michael-04`

Read this in full before touching anything. It replaces the boot sequence.

**Two warnings before you start.**

1. **Trust `current-state.md`, the task board and `git log` over any prose,
   including this document.** Session 03 was handed a briefing two sessions
   stale and nearly rebuilt a working application.
2. **The product is finished and works.** Your job is one specific feature and
   some polish — not a rebuild, and not a hunt for missing screens. Session 04
   audited every module against the PDF and mockup and found nothing missing.

---

## §1 — Identity and orientation

You are **Franklin**, second in the rotation `MICHAEL → FRANKLIN → TREVOR`.
Three teammates each hold a separate Claude account; when one runs low it packs
everything into this repository and the next account's session picks up. You
have no memory of session 04 and no way to read its transcript. This repository
is the only channel.

**Before your first commit**, set and verify your git identity:

```bash
git config user.name  "Robo9327study"
git config user.email "rajstudy9327@gmail.com"
git config user.name && git config user.email     # VERIFY, do not assume
```

That is Franklin's row from `claude/workflow/git-strategy.md` §1. But identity
follows the *session*, not the register — check which account is actually
authenticated in your chat, and if it is not Franklin's, use the matching row
and say so. Session 02 was caught by exactly this: the register had guessed
Franklin would be `MeghRaval30`; he was `Robo9327study`.

GitHub attributes commits by **email**, not display name.

**Commit rules — both binding:**

- No Claude or machine attribution (D-010). Enforced by `attribution.commit: ""`
  in `.claude/settings.json`.
- **No character name in the subject** (D-018). Write `feat(seed): …`, not
  `feat(seed): … [franklin]`. Sessions 01 and 02 used the tag; do not copy them.

Work on branches, merge `--no-ff`, tag versions. Never force-push — the settings
file denies it and history rewriting at tool level, deliberately.

---

## §2 — The clock

```
Hackathon start:   2026-09-05  10:00 IST    ✅ confirmed by the user
Hackathon end:     2026-09-06  10:00 IST    ✅ confirmed by the user
Michael closed 04: 2026-09-05  15:20 IST
Elapsed at handoff:  ~5h 20m / 24h        REMAINING: ~18h 40m
Phase: BUILD
```

| Remaining | Phase | Allowed |
|---|---|---|
| > 8h | **BUILD** | New features |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding — seed data, rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only |

**Run `date` yourself and update `current-state.md`.** Do not trust the numbers
above once time has passed.

You have a lot of time and one well-defined task. Resist the urge to find more.

---

## §3 — The product, in ~400 words

**PeoplePay360 — an Integrated HR & Payroll Operations Platform.** Odoo
hackathon, 24 hours, any stack.

The problem statement's framing is the key: basic HR tools store employee
details, attendance, leave and salary as *separate records*, and real teams need
them to *work together*. It asks for "a connected operational flow" rather than
"simple employee CRUD screens", and says judging weights "real-world business
logic … over surface-level UI design" — a phrase that appears twice.

```
Employee ──┬── Contract (period-scoped) ──── wage, salary structure
           ├── Working Schedule ──────────── expected hours
           ├── Attendance ────────────────── actual worked hours
           └── Time Off (Allocation → Request) ── leave balance
                              ↓
              Salary Structure → ordered Salary Rules
                              ↓
              Payrun → Payslips → PDF → Email
                              ↓
                   Payroll Dashboard (live aggregate)
```

Three deliverables, **all of which exist**: a functional platform with
representative data, a five-minute demo of two end-to-end scenarios (now
rehearsed), and a future roadmap (694 lines).

Detail: `claude/context/problem-statement.md`, `claude/context/product-spec.md`
(every field, recovered from the mockup), `claude/context/prd.md` (numbered
requirements). Originals in `claude/source/`.

---

## §4 — The five graded rules

All five are built, proven and visible in the UI. **Demonstrate them; do not
rebuild them.**

1. **Period-based contract resolution** — payroll uses the contract covering the
   payrun period, not the newest. Expired contracts still govern the period they
   covered. No two `RUNNING` contracts may overlap.
2. **Derived weekly hours** — computed from the schedule's day lines. There is
   deliberately no weekly-hours input anywhere.
3. **Allocation-gated leave** — a type marked *requires allocation* refuses
   requests no approved allocation covers. `Remaining = Allocated − Taken`.
4. **Sequenced salary rules** — rules run in `sequence` order, each result
   visible to later ones. Gross and Net read from the lines, never stored.
5. **Pre-finalization warnings** — surfaced after Compute, before Validate.

Plus three integrations (D-002): attendance drives worked days and LOP,
overtime is paid through a rule, unpaid leave deducts. **And now proration**
(D-023): a mid-period joiner or leaver is paid only for the days their contract
covers.

---

## §5 — Architecture

React 19 + Vite · Django 6.1 + DRF 3.18 · **SQLite** (D-011 — neither Postgres
nor Docker is installed; `DATABASE_URL` switches engines).

```
project/backend/
├── config/         settings.py, urls.py
├── core/           Company, Department, JobPosition, WorkLocation, Holiday
│   └── management/commands/seed.py      ← your main workplace this session
├── accounts/       User, Role, permissions.py, api.py
├── employees/      WorkingSchedule, ScheduleLine, Employee, Contract
├── attendance/     Attendance + check-in widget endpoints
├── timeoff/        TimeOffType, Allocation, TimeOffRequest
├── payroll/        models, engine.py, pdf.py, mail.py, api.py
├── dashboard/      api.py (aggregation only)
├── verify_rules.py · smoke_api.py · probe_forms.py
project/frontend/src/
├── api.js · index.css · lib/ · components/ · screens/   (18 screens)
```

Money is `Decimal` everywhere. Derived values are Python properties, never
columns.

---

## §6 — What session 04 changed

Four real defects, all of which 158 tests and four green harnesses were blind to:

| | Defect | Fix |
|---|---|---|
| 1 | Payslip PDF could not draw `₹` — Helvetica is WinAnsi, no U+20B9 glyph | Embed a TrueType face; set a base `FONTNAME` on every table, since `FONTNAME` was header-only and body cells fell back |
| 2 | `is_employer_cost` / `appears_on_payslip` were dead config — employer PF reduced the employee's net | Engine honours them; new `employer_cost` / `ctc` on Payslip |
| 3 | A 20 February joiner was paid a full month | Day window clamped to the contract; proration factor scales wage percentages |
| 4 | Dec/Jan payslips read "Worked Days 0.00 / 23.00" | Attendance seeded Dec–Mar; no attendance on public holidays |

Plus a fifth found by rehearsal: the time-off form kept a stale refusal on screen
after switching type.

**Numbers moved.** February is now ₹15,58,667.87 and Engineering alone
₹5,03,589.11. December (₹14,73,360) and January (₹14,82,320) are unchanged, so
the headline comparison holds. The demo script, README and current-state were
updated to match — **if you change the seed, update them again.**

---

## §7 — What is DONE

Everything. 63 of 65 tasks. Verified, not merely written.

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py test          # 171 OK
./.venv/Scripts/python.exe verify_rules.py         # 28/28
./.venv/Scripts/python.exe smoke_api.py            # 51/51
./.venv/Scripts/python.exe manage.py seed --flush  # smoke_api dirties the DB
./.venv/Scripts/python.exe manage.py runserver     # terminal 1
./.venv/Scripts/python.exe probe_forms.py          # 26/26, terminal 2
```

All 18 routes were driven in a browser with zero failed requests. The payrun
state machine, role scoping and the attendance widget were all verified by hand.

---

## §8 — What is HALF-DONE

**Nothing.** Working tree clean, every branch merged, `main` pushed.

---

## §9 — YOUR JOB: a 200–300 employee dataset

The user asked for a large roster to prove the software scales, then said to hold
it until the app and workflow were verified. **That verification is done. This is
now the top item (T-089).**

### Constraints that matter

- **The demo script depends on named people.** John Dsouza, Priya Sharma,
  Audrey Peterson, Anita Oliver, Meera Iyer and Aarav Mehta must survive with
  their exact contracts, allocations and balances. Read
  `claude/deliverables/demo-script.md` §"seeded records this script depends on"
  before you touch `seed.py`.
- **Prefer `--employees N` over replacing the roster.** Keep the demo-safe
  22-person set as the default so the demo script stays true, and let the large
  roster be opt-in.
- **Use `bulk_create`.** The seed inserts row by row. At 250 employees the
  attendance loop alone is roughly 20,000 inserts and will crawl.
- **Measure and record.** PRD-7.2 asks for a payrun of 20 in under 5 seconds.
  Time a 250-employee payrun and put the number in `current-state.md` —
  demonstrating scale is the entire point, so the figure is the deliverable.
- Watch the dashboard too: it aggregates six models and was only ever exercised
  at 22 employees.

### Fold in T-090 while you are there

PRD success criterion 4 — *"a payrun surfaces at least two distinct warnings"* —
is **the one unmet criterion**. Only `AC_MISSING` fires. The engine supports
`DUPLICATE`, `NO_CONTRACT`, `NEGATIVE_NET`, `NO_STRUCTURE` and `RULE_ERROR` and
the seed exercises none.

A large roster naturally contains mid-month joiners and leavers, so this is
nearly free — but note the severities. `NO_CONTRACT`, `NEGATIVE_NET` and
`NO_STRUCTURE` are **ERROR** and block Validate, so a payrun containing one
cannot be marked Paid. Seed them so they appear in a payrun the demo *creates*,
not in the three historical ones, or the seeded history will not validate.

---

## §10 — Decisions — do not relitigate

Full text in `claude/context/decisions.md`.

| | |
|---|---|
| D-001 | React + Django/DRF |
| D-002 | Full spec + 3 integrations |
| D-003 | India, ₹, PF/ESIC/PT/LWF, single company |
| D-008 | Feature branches, `--no-ff` merges, version tags |
| D-009 | Each session commits as its own teammate |
| D-010 | No machine attribution in commits |
| D-011 | **SQLite, not PostgreSQL** |
| D-012 | **Context folder updated only at MEGATRON LAUNCH** |
| D-018 | No character tag in commit subjects |
| D-021 | Employer contributions separated from employee pay |
| D-022 | PDF embeds a rupee-capable font |
| D-023 | Pay prorated to the contract's dates |
| D-024 | Seed overtime confined to February onward |

D-012 governs your rhythm: **commit code as you go, but leave `claude/` alone**
until the user says MEGATRON LAUNCH.

---

## §11 — Traps that cost session 04 time

Full list in `claude/state/blockers.md`; these five are new.

1. **Never `runserver --noreload`** (B-016). Session 04 did, then chased a
   phantom bug that was the server holding pre-fix code while a shell running
   the same code was correct.
2. **A harness that counts bytes proves nothing** (B-017). `smoke_api.py`
   asserted the PDF was `application/pdf` and >1,500 bytes and stayed green while
   every money figure rendered wrong. The user found it by downloading one.
3. **`pdftotext` misreads subset fonts** (B-018). Some `₹` extract as `s` even
   when correct. Check the ToUnicode CMap for `<01> <20B9>` instead.
4. **The Browser pane will not render a PDF** (B-019) — it triggers a download.
5. **Inline `python -c` and heredocs corrupt content** (B-020). A heredoc turned
   `\Fonts\arial.ttf` into a literal 0x07 byte that the Edit tool then could not
   match. Write a `.py` file to the scratchpad and run it.

Also standing: **the console is cp1252** — never print `₹` from a management
command (B-006). It aborted the seed once, after data had been written.

---

## §12 — Your first three actions

**1. Orient and set identity.**

```bash
git pull --rebase
date                                   # recompute the clock yourself
git config user.name "Robo9327study" && git config user.email "rajstudy9327@gmail.com"
git config user.name && git config user.email
```

**2. Prove it still works — ten minutes, do not skip.**

Run all four harnesses (§7). If any goes red, fix that before anything else.
Then start both servers and sign in as `admin@oxp.com` / `demo1234`.

**3. Start T-089.** Branch `feat/large-dataset`. Read the demo script's seeded
records section first, then extend `core/management/commands/seed.py` behind an
`--employees N` flag.

---

## §13 — Ask the user about this before acting

The user said **"remove your commits"** and session 04 ended before it was
resolved. The facts, checked:

- **Every commit is authored by one of the three teammates.** There is no
  Claude-authored commit anywhere in the history.
- **Exactly one commit carries a Claude co-author trailer:** `12a632f`, the root
  scaffold commit from session 01, written before D-010 existed. That trailer is
  why `claude` appears in GitHub's contributor list.
- Removing it means rewriting ~117 commits and force-pushing, which would break
  the other teammates' clones and risk losing in-flight work.

**Do not touch history on your own.** If the user confirms a rewrite, first
confirm the other two have pushed and are idle. It is also possible they meant
"revert session 04's code changes" — that would drop four live bug fixes, so
establish which they mean.

---

## §14 — Demo status

`claude/deliverables/demo-script.md` is **rehearsed and stamped** (T-063).
Scenario B was walked click by click; Scenario A's data verified against the
database. Every claim holds, including the previously suspect
"Taken two, Remaining eighteen" — B4 approves the March row first, and that is
what moves the balance, so B4 must not be skipped.

If your dataset work changes any seeded figure, **re-verify the script and
update the numbers in it, in `README.md`, and in `current-state.md`.** Session 04
had to do exactly that when February moved.

---

## Closing note

There is a lot of time and very little that must be built. The temptation will be
to add features; the spec has none outstanding. Spend the time on the dataset,
on measuring what it proves, and on making sure the demo still runs afterwards.

Good luck, Franklin.
