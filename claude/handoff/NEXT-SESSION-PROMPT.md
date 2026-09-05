# BRIEFING FOR THE NEXT SESSION

**Written by:** Trevor (session 03) · 2026-09-05, 13:45 IST
**You are:** MICHAEL (session 04)
**Handoff tag:** `handoff-trevor-03`

Read this in full before touching anything. It replaces the boot sequence — when
you finish it you will know everything session 03 knew.

**One warning before you start.** The briefing *I* was handed was two sessions
stale: it told me the frontend was an untouched Vite demo and that my job was to
build it. It had been finished an hour earlier. I nearly started rebuilding a
working application. **Trust `current-state.md`, the task board and `git log`
over any prose — including this document — wherever they disagree.**

---

## §1 — Identity and orientation

You are **Michael**, and this is the second time round the rotation
`MICHAEL → FRANKLIN → TREVOR → MICHAEL`. Three teammates each hold a separate
Claude account; when one runs low it packs everything into this repository and
the next account's fresh session picks up.

You have **no memory** of session 03. There is no shared context and no way to
read my transcript. This repository is the only channel. If something here is
unclear, trust the code and the harnesses over your assumptions, and ask the user
rather than guessing.

**Before your first commit**, set and verify your git identity:

```bash
git config user.name  "TheTeam404"
git config user.email "sohampanchal2229@gmail.com"
git config user.name && git config user.email     # VERIFY, do not assume
```

That is Michael's row from `claude/workflow/git-strategy.md` §1, which is now
**complete and verified for all three characters**. But identity follows the
*session*, not the machine and not the register — check which account is actually
authenticated in your chat, and if it is not Michael's, use the row that matches
and say so. Session 02 was caught by exactly this: the register had guessed
Franklin would be `MeghRaval30`, and he was actually `Robo9327study`.

GitHub attributes commits by **email**, not display name. Misattribution can only
be fixed by rewriting history, which is forbidden here.

**Commit message rules — both binding:**

- No Claude/machine attribution (D-010). Enforced by `attribution.commit: ""` in
  `.claude/settings.json`.
- **No character name in the subject either** (D-018, new this session, at the
  user's explicit request). Write `fix(payroll): …`, not
  `fix(payroll): … [trevor]`. Sessions 01 and 02 used the tag; do not copy them.

Work on branches, merge with `--no-ff`, tag versions. Never force-push. The
settings file denies force-push and history rewriting at the tool level.

---

## §2 — The clock

```
Hackathon start:  2026-09-05  10:00 IST    ✅ confirmed by the user
Hackathon end:    2026-09-06  10:00 IST    ✅ confirmed by the user
Trevor closed:    2026-09-05  13:45 IST
Elapsed at handoff:  ~3h 45m / 24h        REMAINING: ~20h 15m
Phase: BUILD
```

| Remaining | Phase | Allowed |
|---|---|---|
| > 8h | **BUILD** | New features |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding — seed data, rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only |

**Run `date` yourself and update `current-state.md`.** Do not trust the numbers
above once time has passed — session 01 recorded a handoff timestamp that was
ahead of the real wall clock.

You have a great deal of time and very little that must be built. That is a
genuinely unusual position, and §9 explains why the right response is *not* to
find new features.

---

## §3 — The product, in ~500 words

**PeoplePay360 — an Integrated HR & Payroll Operations Platform.** An Odoo
hackathon problem statement, 24 hours, any stack permitted.

The problem statement's own framing is the key to everything: basic HR tools
store employee details, attendance, leave and salary as *separate records*, and
real teams need them to *work together*. It says explicitly that the goal is to go
"beyond simple employee CRUD screens" into "a connected operational flow", and
that judging weights "real-world business logic … over surface-level UI design".
That phrase appears twice in the PDF.

So this is not a CRUD app with a payroll screen bolted on. The Employee record is
a hub; Contracts and Working Schedules supply payroll context; Attendance and
Time Off capture daily activity; Salary Structures and Rules define computation;
and the Payrun is where all of it converges into a payslip.

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

Deliverables are three: a functional platform with representative data; a
five-minute live demo of two end-to-end scenarios; and a future roadmap. **All
three exist.** The roadmap is 694 lines and the demo script 233; both are
committed. What has not happened is a rehearsal — see §14, which is the most
important section in this briefing.

Full detail: `claude/context/problem-statement.md` (the PDF distilled),
`claude/context/product-spec.md` (every field, recovered from the mockup),
`claude/context/prd.md` (numbered requirements with acceptance criteria).
Originals are in `claude/source/`.

---

## §4 — The five graded business rules

These are where the marks are. **All five are built, proven, and now visible in
the UI.** Your job is to demonstrate them, not to rebuild them.

1. **Period-based contract resolution.** An employee has several contracts over
   time; payroll must use the one covering the *payrun period*, not the newest.
   No two `RUNNING` contracts may overlap.
   *Visible at:* payrun wizard step 2, the payslip's "Contract resolved for this
   period" card, and `Contracts → Resolve by period`.
2. **Derived weekly hours.** Computed from the schedule's day lines, never typed.
   *Visible at:* Working Schedules — there is deliberately no weekly-hours input.
3. **Allocation-gated leave.** If a Time Off Type requires allocation, a request
   is refused unless an approved allocation covers it with enough balance.
   `Remaining = Allocated − Taken`, all derived.
   *Visible at:* the balance table on the request form, and the server's own
   refusal text when nothing covers the request.
4. **Sequenced salary rules.** Rules run in `sequence` order, each result visible
   to later rules. Gross and Net are derived from lines, never stored.
   *Visible at:* the payslip's "Salary computation — evaluated in sequence order".
5. **Pre-finalization warnings.** Problems surface *before* Validate — missing
   bank account, duplicate payslip, no contract, negative net, no structure.
   *Visible at:* the payrun's pre-validation panel, populated after Compute and
   before Validate becomes available.

Plus three integrations chosen in D-002, all working: attendance drives worked
days and LOP; overtime is paid through a rule; unpaid leave deducts.

Proof, which you should run in your first ten minutes — see §12.

---

## §5 — Architecture as actually built

**Stack:** React 19 + Vite 8 · Django 6.1 + DRF 3.18 · **SQLite** (D-011 — neither
PostgreSQL nor Docker is installed on the build machine; `DATABASE_URL` switches
engines if anyone wants it).

```
project/backend/
├── config/         settings.py, urls.py — all routing lives here
├── core/           Company, Department, JobPosition, WorkLocation, Holiday
│   └── management/commands/seed.py
├── accounts/       User, Role, permissions.py, api.py, tests.py (830 lines)
├── employees/      WorkingSchedule, ScheduleLine, Employee, Contract
├── attendance/     Attendance + check-in/out widget endpoints
├── timeoff/        TimeOffType, Allocation, TimeOffRequest
├── payroll/        models, engine.py, pdf.py, mail.py, api.py
├── dashboard/      api.py (aggregation only, no models)
├── verify_rules.py business-rule proof harness      28/28
├── smoke_api.py    HTTP proof harness               51/51
└── probe_forms.py  UI-payload probe                 26/26   ← needs a server

project/frontend/src/
├── api.js              client, auth, error flattening, money/date formatters
├── index.css           the whole design system
├── App.jsx             route table (87 lines)
├── lib/router.js       hash router
├── components/         Shell.jsx, AttendanceWidget.jsx, ErrorBoundary.jsx, ui.jsx
└── screens/            18 screens, one per area
```

**Backend conventions.** Each app puts serializers and viewsets together in
`api.py`. Money is always `Decimal`, never float. Derived values are Python
properties, not columns. Permission classes live in `accounts/permissions.py` and
are applied per viewset.

**Self-service is a per-viewset carve-out, and there are two different shapes:**

- `AttendanceViewSet` uses `SELF_SERVICE_ACTIONS` + `perform_create`, forcing the
  employee *after* validation.
- `TimeOffRequestViewSet` substitutes the employee *before* validation, inside an
  overridden `create()`. **This difference is deliberate and load-bearing** —
  D-016 explains why, and a test fails if anyone "simplifies" it. Read D-016
  before touching either.

**Frontend conventions.** Hash routing; `api.js` redirects to `#/login` on 401.
`Shell.jsx` holds a `MENUS` array — the six top-bar menus are fixed by the spec,
and individual items carry an optional `perm` string filtered through
`auth.can()`. `auth.user` carries `employee_id`, `employee_name`, `roles` and a
`permissions` object with the five capability booleans.

**Hiding a button is not enforcement.** Every permission is checked server-side;
the UI gating is cosmetic on top of that. Keep it that way.

---

## §6 — Data model walkthrough

Full schema in `claude/context/data-model.md`. The relationships that matter:

- `Employee` is the hub — self-referential `manager`, and reverse relations
  `contracts`, `attendances`, `allocations`, `timeoff_requests`, `payslips`.
- `Contract` is **period-scoped**. `Employee.contract_for_period(start, end)` is
  the single most important query in the system. It matches `RUNNING` **and**
  `EXPIRED` contracts — lifecycle state and period coverage are different things,
  and an expired contract is still the right basis for the period it governed.
- `Allocation.taken` and `.remaining` are properties over **approved** requests,
  so cancelling a request restores balance for free. **A `DRAFT` request does not
  move the balance** — this matters for the demo script, see §14.
- `Payslip.gross` / `.net` read from `PayslipLine` by category. Nothing stored
  twice.
- `unique(payslip, code)` on `PayslipLine` makes recompute idempotent.
- `unique(employee, period_start, period_end)` on `Payslip` is the duplicate
  guard.
- `TimeOffRequest.half_day` is a **CharField with choices `FIRST` / `SECOND`,
  blank allowed** — *not* a boolean. Assuming otherwise broke the request form for
  the entire life of the project; see §13.

**Derived, never stored** — storing any of these as an editable field is a
correctness bug: schedule weekly hours and days, line hours, attendance worked
hours, allocation taken/remaining, payslip gross/net/worked days/LOP/overtime,
and the employee smart-button counts.

---

## §7 — What is DONE

**Effectively everything.** The board has one open item that matters (§9).

| Area | Evidence |
|---|---|
| Models, 7 apps, migrations | `manage.py migrate` clean |
| Five graded rules | `verify_rules.py` 28/28 |
| REST API, roles, wizard, PDF, email, dashboard | `smoke_api.py` 51/51 |
| Every UI create + update payload | `probe_forms.py` 26/26 |
| Django test suite, 7 apps | `manage.py test` 158/158 |
| Frontend, 18 screens | `npm run build` clean; browser pass below |
| Demo script (T-060), roadmap (T-061), README (T-062) | committed |

**Verified by hand in a browser during session 03**, not merely by harness:

- **Payrun, end to end as admin.** Wizard step 1 creates nothing → step 2 lists
  20 employees each with the contract resolved *for that period* (Aarav Mehta on
  his 01 Jan 2026 contract at ₹85,000) → Create → Compute (Gross ₹16,85,299.68,
  Net ₹15,79,019.68) → **0 errors, 2 warnings shown before Validate** → Validate
  → Mark Paid, after which every action button is correctly disabled.
- **Payslip detail** shows the resolved-contract card and the sequence-ordered
  computation table (seq 1, 10, 20, 30…), with worked days 20/21 and overtime
  7.88h derived from attendance.
- **Employee self-service as `john@oxp.com`.** The Payroll menu is absent, lists
  are scoped to him, the request form fills his name read-only, the balance table
  loads live (20 / 2 / 18), a two-day request saves with duration 2.00 and a
  same-day First-half request saves with **0.50**.

### Seed evidence — live, not hardcoded

| Payrun | Net | Why it matters |
|---|---|---|
| Dec 2025 | ₹14,73,360 | **Lower** than Jan — two employees resolve to older, cheaper contracts |
| Jan 2026 | ₹14,82,320 | |
| Feb 2026 | ₹15,63,028 | **Higher** — February overtime reached payroll |

Feb filtered to Engineering alone: **₹5,03,998**. Those three facts are the demo;
they prove nothing is hardcoded.

Counts: 22 employees, 24 contracts, 859 attendance, 11 leave requests, 3 payruns,
60 payslips, 840 lines, 6 warnings.

---

## §8 — What is HALF-DONE

**Nothing, in the code.** The working tree is clean, every branch is merged into
`main`, and `main` is pushed. There is no stranded work anywhere — I checked with
`git branch --no-merged main`, which is empty.

What is unfinished is **rehearsal**, and it carries a specific risk:

### The demo script has never been walked against a running app

`claude/deliverables/demo-script.md` was written partly from source. Two things in
it need checking, and one of them is serious:

1. **Scenario B steps B2–B3 are built on the New Time Off Request form — which
   could not submit at all until session 03 fixed it.** The script's line
   *"Submit, and it saves"* would have failed live on stage with
   `half_day: "False" is not a valid choice`. The form works now and the fix is
   verified, but the script's exact click path has not been replayed.

2. **B5 claims "Taken two. Remaining eighteen."** A newly submitted request is
   `DRAFT`, and `Allocation.taken` counts only **approved** requests — so the
   request submitted at B3 does not move the balance by itself. Either B4
   approves it (check), or the narration is describing pre-existing seeded state
   and is misleading as written. This is the step most likely to embarrass
   someone on stage.

3. Minor: the form now has a **Half day** field (Full day / First half / Second
   half) between the date row and Reason. The default is Full day so the path
   still works, but the script does not mention the field.

Fixing this is §12, action 3.

---

## §9 — What is NOT STARTED, in priority order

| Order | Task | Why this order |
|---|---|---|
| 1 | **T-063 — rehearse the demo, correcting the script in place** | The only remaining item with real risk. See §8 and §14 |
| 2 | Re-ask the deployed-demo question (§11) | Asked twice, never answered. Cheap now, expensive at hour 22 |
| 3 | Polish, *only* if the rehearsal surfaces something | |
| 4 | T-075 — frontend tests | Genuinely lowest value for a 24h build; the browser pass and `probe_forms.py` cover the ground more cheaply |

**Read this next paragraph twice.** With ~20 hours left and a complete board, the
temptation is to invent work. Resist it. The failure mode from here is not running
out of time — it is **breaking something that already works**. Three harnesses and
a test suite are green; a fourth of them going red at hour 20 with no time to
diagnose is how this project actually loses marks.

If the user asks for more scope, build it on a branch and keep `main` green. If
you find yourself refactoring something that passes its tests, stop.

---

## §10 — Decisions already made — do not relitigate

Full text with rationale in `claude/context/decisions.md` (D-001 … D-020).

| | |
|---|---|
| D-001 | React + Django/DRF |
| D-002 | Full spec + 3 integrations — all three shipped |
| D-003 | India, ₹, PF/ESIC/PT/LWF, single company |
| D-004 | File-based handoff through the repo |
| D-005 | `CLAUDE.md` as the auto-loaded failsafe |
| D-006 | Heartbeat commits for **code** |
| D-007 | ~~No branches~~ — reversed by D-008 |
| D-008 | Feature branches, `--no-ff` merges, version tags |
| D-009 | Each session commits as its own teammate |
| D-010 | No machine attribution in commits |
| D-011 | **SQLite, not PostgreSQL** |
| D-012 | Context folder updated **only** at MEGATRON LAUNCH |
| D-013 | UI design language is binding |
| D-014 | A harness that builds its own inputs tests the server, not the product |
| D-015 | Parallel sessions require a written file-ownership split |
| **D-016** | **Time-off ownership is substituted *before* validation** — the allocation gate reads that field |
| **D-017** | Payrun DELETE gated on `can_configure_payroll` |
| **D-018** | **No character name in commit subjects** |
| **D-019** | A test documenting an open bug is *reversed* when fixed, never deleted |
| **D-020** | Every frontend create form must have a `probe_forms.py` case |

D-012 governs your rhythm: commit code as you go, but leave `claude/` alone until
the user says **MEGATRON LAUNCH**. The user asked for this explicitly and repeated
it in session 03's opening prompt.

---

## §11 — Known bugs and blockers, including what was already tried

**No known bugs.** All four harnesses green, `npm run build` clean.

Read `claude/state/blockers.md` in full before debugging anything. The headlines:

**B-014 — the main checkout is on a stale branch. This will bite you first.**
`C:\Users\raval\Desktop\odoo_2026` is checked out on `test/backend-suite` at
`b8b65ca`, which is merged but **seven commits behind `main`**. Session 03's
second half ran in a git worktree, so the main checkout was never switched back.

```bash
cd C:/Users/raval/Desktop/odoo_2026
git checkout main && git pull
git log --oneline -1        # expect the session-03 handoff commit
```

Skip that and you will read stale source and rediscover fixed bugs. Do **not**
delete `test/backend-suite`; it is merged history.

**Also note:** `.venv` and `db.sqlite3` live only in the main checkout and are
gitignored. A fresh worktree has neither. You can borrow the interpreter by
absolute path — a venv's `site-packages` are absolute, so this works.

**Accepted risks, not obstacles:**

- **B-011** — the formula sandbox denies substrings (`__`, `import`, `getattr`…),
  not capabilities. The eval context holds live model instances and attribute
  access is unrestricted, so a chain reaching `_meta` is not prevented. Accepted:
  writing formulas needs `can_configure_payroll`. **If you ever open rule
  authoring to a lower role, fix this first.**
- **B-009** — large fan-out subagent workflows can exhaust the account session
  limit and return nothing while still burning the budget. Check capacity first.

**Dead ends — do not repeat these:**

- **PostgreSQL / Docker** (B-005) — neither installed, no install directory.
  SQLite is a deliberate decision.
- **`gh` CLI** (B-002) — not installed. Plain `git` over HTTPS works; credentials
  are cached.
- **WeasyPrint** — needs GTK on Windows. ReportLab is a pure wheel and works.
- **Force-pushing to strip a Claude trailer from `12a632f`** — blocked by the
  classifier, then denied at settings level. Harmless; leave it.

**The one open question for the user, asked twice and never answered:**
*Is a deployed demo required, or does a local walkthrough suffice?* It changes
what the roadmap and demo script should assume. Ask it in your first message.

---

## §12 — Your first three actions

**1. Fix your checkout and set your identity.**

```bash
cd C:/Users/raval/Desktop/odoo_2026
git checkout main && git pull
git config user.name "TheTeam404" && git config user.email "sohampanchal2229@gmail.com"
git config user.name && git config user.email
date                                  # then correct the clock in current-state.md
```

**2. Prove everything still works — ten minutes, do not skip.**

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py seed --flush
./.venv/Scripts/python.exe verify_rules.py     # expect 28/28
./.venv/Scripts/python.exe smoke_api.py        # expect 51/51
./.venv/Scripts/python.exe manage.py seed --flush   # smoke_api dirties the DB (B-010)
./.venv/Scripts/python.exe manage.py test      # expect 158/158
```

Then, in **two** terminals, because `probe_forms.py` needs a live server:

```bash
./.venv/Scripts/python.exe manage.py runserver     # terminal 1
./.venv/Scripts/python.exe probe_forms.py          # terminal 2 — expect 26/26
```

**3. Rehearse the demo and correct the script in place.** This is the real work
of your session.

```bash
cd project/frontend && npm install && npm run dev
```

Sign in `admin@oxp.com` / `demo1234` and walk
`claude/deliverables/demo-script.md` from A1 to C2 with the script open beside
you. **Start with Scenario B steps B2–B5**, which are the least trustworthy part
of the document for the reasons in §8. Fix the script wherever the app disagrees
with it — the script is a graded deliverable, so correcting it *is* the task, not
overhead on the way to it.

---

## §13 — Traps that cost previous sessions time

1. **Open the screen.** Three sessions read `TimeOff.jsx`; the one that clicked it
   found that the form had never been able to submit. Reading code told everyone
   it was fine. This is the single most valuable line in this briefing.
2. **`half_day` is a choice field, not a boolean.** The form seeded it as `false`
   and rendered no control, so every POST returned 400 from the day the screen
   was written. A field present in the payload but absent from the form can never
   be corrected by a human — its default is load-bearing, and nothing type-checks
   it against the model.
3. **A green harness on an incomplete list reads as proof.** `probe_forms.py` was
   24/24 while covering twelve of thirteen create forms — and the uncovered one
   was the broken one. Hence D-020.
4. **`probe_forms.py` needs a running server**, unlike `smoke_api.py`. Without one
   it dies with a raw `WinError 10061` traceback that looks like a broken harness.
5. **`smoke_api.py` writes to the dev database** (B-010), creating an
   `April 2026 (smoke)` payrun that the dashboard then opens on. Always
   `seed --flush` afterwards.
6. **Never print non-ASCII from a Python script.** The console is cp1252 and a
   rupee sign aborts the command — this killed the seed once *after* it had
   written data. Use `INR` in console output; files, API and PDFs are fine.
7. **`Payslip.employee` is `PROTECT`.** Delete Payruns before Employees or the
   flush fails. The seed's order is correct — copy it.
8. **`contract_for_period` must include `EXPIRED`.** Filtering `state=RUNNING`
   gave December 20 `NO_CONTRACT` errors and a zero payrun.
9. **Recompute must delete lines, never append** (`unique(payslip, code)`), and
   must not delete payrun-level warnings carrying an `employee`, or you lose the
   record of who was skipped as a duplicate.
10. **The dashboard's previous-period comparison anchors to the previous payroll
    period,** not a rolling N-day window — a 28-day window from 1 Feb starts on
    4 Jan and excludes January entirely.
11. **Chained heredocs in one Bash call fail to parse** (B-007). Use the Write and
    Edit tools. Note also that the auto-mode classifier blocked a Python heredoc
    and one `manage.py test <label>` call during session 03 — if a Bash call is
    refused, reach for the dedicated tool rather than rephrasing the command.
12. **The probe's `first()` appends its own `?page_size=1`**, so passing a path
    that already has a query string silently drops the filter (B-013). Use the
    `every()` helper and filter in Python.

---

## §14 — Demo script status

`claude/deliverables/demo-script.md` — 233 lines, with click paths, real seeded
names, verified totals and narration.

**Scenario A (employee → payrun → payslip): works end to end, driven in a
browser during session 03.** Wizard, compute, the two pre-validation warnings,
validate, mark paid, and the payslip detail with its resolved-contract card and
sequence-ordered computation table. This half you can trust.

**Scenario B (allocation → request → balance): the mechanism works, the script
does not yet.** The form it depends on could not submit until session 03 fixed
it, so the exact click path in the document has never been executed. Two specific
things to check, both explained in §8: the missing **Half day** field, and B5's
**"Taken two. Remaining eighteen."** claim against a request that is still
`DRAFT` and therefore does not move `Allocation.taken`.

**The closing move (C1–C2) is the strongest thing in the demo and it works
today.** On the Payroll Dashboard, change Period from February 2026 to December
2025 and every card re-drives together:

> ₹15,63,028 → ₹14,73,360, then set Department to Engineering → ₹5,03,998.

Six models re-queried from one dropdown. The script routes this as
**Reports → Payroll Dashboard** — the hop matters, because Reports became a
dropdown in session 02 and a script that says "click Reports and the dashboard
appears" is wrong on stage.

---

## Closing note

The build is done. Backend, frontend, tests, harnesses, README, roadmap and demo
script all exist, and everything green was verified green at 13:35 IST today, not
assumed.

What is left is the least glamorous and highest-value hour in the project: sit in
front of the running app with the demo script and walk it, fixing the script where
reality disagrees. Session 03 found a completely broken screen by doing exactly
that for ten minutes. There may be another one.

Do not go looking for features. Go looking for the gap between what the documents
claim and what the application does.

Good luck, Michael.
