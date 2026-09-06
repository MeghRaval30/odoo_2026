# NEXT SESSION — you are FRANKLIN, session 10

> Rewritten from scratch by Trevor at MEGATRON LAUNCH, 2026-09-06 06:20 IST.
> Header corrected 06:35 IST: Michael is unavailable, so Franklin takes this
> slot. Never append to this file. Rewrite it.

---

## 1. Identity and orientation

You are **Franklin**, the tenth session of a relay building PeoplePay360 for a
24-hour Odoo hackathon. Three Claude sessions work this project in rotation on
three teammates' separate accounts:

> **MICHAEL → FRANKLIN → TREVOR → (repeat)**

**The rotation is being taken out of order.** By the strict order Michael would
have session 10, but Michael is unavailable and the clock does not wait, so it
comes back to you. You last ran session 08. That changes nothing about how you
work: you still have **no memory** of session 09, the repository is still the
only channel, and your git identity is still your own.

Trevor just finished session 09. You have **no memory** of it. Every handoff is
a cold start in a brand-new chat, possibly on a different machine. **This
repository is the only channel between sessions.** Anything not written to a
file and pushed is gone.

### Before your first edit

```bash
git fetch origin
git config user.name  "Robo9327study"
git config user.email "rajstudy9327@gmail.com"
git config user.name && git config user.email    # VERIFY. Do not assume.
```

That is Franklin's row from `claude/workflow/git-strategy.md` §1, confirmed in
session 02. **Do not** commit as `MeghRaval30` (Trevor) or `TheTeam404`
(Michael) — identity follows the session, not the machine, and all three
teammates must appear as authors on this repository. Getting it wrong
is **not silently recoverable** — fixing misattributed commits needs a history
rewrite, which this relay forbids.

**You probably cannot check out `main`.** See §11, B-038. Base on `origin/main`
and push with `git push origin HEAD:main`.

**Check whether another session is running before you write anything** (B-030).

---

## 2. The clock

```
Start:  2026-09-05 10:00 IST      End: 2026-09-06 10:00 IST
Trevor closed session 09 at 2026-09-06 06:20 IST
Elapsed ~20h 20m   REMAINING ~3h 40m
```

**Run `date` yourself.** By the time you read this it will be less.

| Remaining | Phase |
|---|---|
| < 4h | **POLISH — stop coding. Demo script, rehearsal, roadmap** |
| < 2h | DEMO — rehearse only, touch nothing |

You are in **POLISH**, close to DEMO. **Do not start a feature.** The product is
larger than it has ever been and what it lacks is not code.

---

## 3. The product, in about 500 words

**PeoplePay360** is an integrated HR and payroll operations platform for a
single Indian company. The thing being graded is that HR data *drives* payroll
through rules a human can inspect.

An **Employee** has a **Contract** carrying a wage, a salary structure and a
working schedule. The contract is period-resolved: an employee may have many
contracts over time, and payroll for December must use the contract that covered
December, not the one running today. A **Working Schedule** defines the days and
hours of a week, and its weekly hours are **derived from its lines**, never
typed. **Attendance** records real check-in/check-out, from which worked days,
hours and overtime are computed. **Time Off** is requested against an
**Allocation** that must exist and be approved first, and unpaid leave becomes a
payroll deduction.

A **Payrun** covers a period and a set of employees. Computing it produces one
**Payslip** each, and each payslip is a sequence of **Payslip Lines**, one per
**Salary Rule** that fired. Rules run in sequence and later rules read earlier
results by code, which is how `HRA = 40% of BASIC` works without hard-coded
arithmetic. Before validation a payrun is checked, and problems surface as
**warnings** — a missing bank account, a duplicate payslip, a negative net.

The locale is India: rupees, PF, ESIC, Professional Tax, LWF. Employer
contributions are computed and reported as cost-to-company but **never move the
employee's gross or net** (D-021).

The second half of the product is **who may do what**. The top bar is built
**server-side** from the signed-in account's capabilities, so a role that cannot
use a menu does not see it — and the same table enforces the API, so hiding a
control is never mistaken for enforcing a rule.

**Session 09 added a third half.** The biggest obstacle to a company adopting
this software is not the software: it is five years of people data sitting in
whatever they keep it in today. So there is now an **Import Studio** that reads a
messy spreadsheet, and a **workforce ecosystem** for the operations that act on
hundreds of people at once — mass increments, offboarding, bonds, and standing
rules that raise reminders. All of it is **Admin-only** (D-060).

The Import Studio's design is the interesting part, and it came from a
measurement rather than a preference. The obvious version — hand the headers to a
local model and do what it says — was built first and measured: `qwen2.5:7b`
returned `null` for `Sal (pm)`, `DOJ` and `Mob No` in one pass and mapped all
three correctly in the next, with nothing to tell the two apart. So the model is
**one voter of three**, fed the profiler's measured evidence rather than raw
values, and the reconciler keeps the losing votes so the screen can show
arithmetic overruling the model.

The demo's headline evidence is still three months of real payroll where
**December < January < February**, each gap with a cause you can point at. That
is the sentence the whole build exists to let someone say.

---

## 4. The five graded business rules

These are the product. Everything else is scaffolding.

| # | Rule | Acceptance |
|---|---|---|
| 1 | **Period-based contract resolution** | `john@oxp.com` draws ₹1,03,000 for December and ₹1,10,000 for January. `core/tests.py` pins both. **Session 09 added a second demonstration**: a mass increment closes the current contract and opens a new one rather than editing a wage, so a period before the raise still resolves to the old contract — pinned by `workforce/tests.py::test_an_increment_does_not_rewrite_history` |
| 2 | **Derived weekly hours** | "40 Hours / Week" derives 40.00h over 5 days; "Part-time 20h" derives 20.00h over 4. No weekly-hours input exists anywhere |
| 3 | **Allocation-gated leave** | A request with no approved allocation covering it is refused, in the serializer's `validate()`, against the *requester's own* balance |
| 4 | **Sequenced salary rules** | Rules run in `sequence` order and later rules read earlier results by code. `verify_rules.py` proves all 28 checks |
| 5 | **Pre-finalization warnings** | A negative net raises `NEGATIVE_NET` at ERROR severity, `can_validate` goes false, and `validate_payrun` refuses |

**PRD success criterion 4** — two *distinct* warning codes firing during the
demo — is met and **proven by clicking**. The seed leaves a March off-cycle
payslip in `Computed` so the March payrun the operator creates finds a
`DUPLICATE` alongside two `AC_MISSING` (D-033). **Do not mark that run paid.**

**Three D-002 integrations** must stay visible: attendance → worked days/LOP,
overtime → a salary rule, unpaid leave → a deduction.

---

## 5. Architecture as actually built

```
project/
  backend/        Django 6.1.1 + DRF 3.18, SQLite (D-011)
    accounts/     identity, roles, THE CAPABILITY MATRIX, security, audit
    employees/    Employee, Contract, WorkingSchedule, ScheduleLine
    attendance/   Attendance + the check-in widget
    timeoff/      TimeOffType, Allocation, TimeOffRequest
    payroll/      SalaryStructure, SalaryRule, Payrun, Payslip, engine, pdf
    dashboard/    the four role dashboards
    core/         Holiday, formatting, the seed command
    intelligence/ NEW s09 — the Import Studio
    workforce/    NEW s09 — segments, bulk ops, bonds, playbooks
  frontend/       React 19 + Vite, no router library (hash routing)
test-data/import/ NEW s09 — seven demo rosters + README
scripts/          NEW s09 — setup-ai.ps1 / setup-ai.sh
docs/AI-SETUP.md  NEW s09
```

### The one file that matters most

**`project/backend/accounts/capabilities.py`** — the single home of "who may do
what". Capability vocabulary, the five role sets, the navigation manifest, and
which dashboard each role lands on. Permission classes, the menu and the
frontend all read this one table.

Session 09 added `DATA_IMPORT`, `WORKFORCE_READ`, `WORKFORCE_WRITE`, held by the
**Admin only** (D-060), and a `workforce` navigation group with six entries.

### The Import Studio, module by module

| File | Job |
|---|---|
| `readers.py` | Parse CSV/TSV/XLSX. **Finds the header row by scoring**, drops junk rows, blank columns and a trailing TOTAL |
| `profiler.py` | Measure each column and render one ASCII evidence sentence, used by the UI *and* the prompt |
| `schema.py` | 22 target fields, Indian-HR-aware synonyms, the lexical voter, the shape voter, `CLOSED_VOCABULARY` |
| `llm.py` | Ollama client. Never raises into a caller — `LLMUnavailable` is caught everywhere |
| `mapper.py` | **The three-voter reconciler.** Keeps losing votes. Builds value maps |
| `transforms.py` | Named composable steps, and `suggest_transforms` deriving them from the profile |
| `validators.py` | Row checks. Error blocks a row, warning does not |
| `enrich.py` | **Second-file join.** Finds the key by measuring value overlap |
| `codes.py` | Employee numbering policy, previewed against real rows |
| `importer.py` | The single path: `preview` writes nothing, `commit` writes in one transaction |
| `api.py` | Viewsets plus the **streaming** analyse endpoint |

### Conventions that are enforced, not preferred

* **Server-side enforcement, always**, and never offer a control the server will
  refuse.
* **Name a shared answer once, on the server** (D-034, D-051, and now D-065 —
  the same rule found a third time from a third direction).
* **Breadth of read is decided by a read capability** (D-045).
* **A workflow state is not an input field** (D-054).
* `claude/context/ui-design-language.md` is **binding** for any frontend work.
* Money is `Decimal`, quantised to 2dp.
* **ASCII only in Python that prints.** The Windows console is cp1252.

---

## 6. Data model, the parts that matter

* **Employee → Contract** is one-to-many. `employee.contract_for_period()` is
  graded rule #1 and deliberately includes `EXPIRED` contracts.
* **Contract → WorkingSchedule → ScheduleLine.** `ScheduleLine.hours` is what
  rule #2 derives from, and the seed reads these lines to generate attendance.
* **Payslip totals are derived properties, not columns.**
* **`Payslip` has a unique constraint** on (employee, period_start, period_end).
* **`TimeOffRequest`** is created into `TO_APPROVE` (D-053); `state` is
  read-only (D-054).
* **User ↔ Employee is optional in both directions.** `admin@oxp.com` has **no
  employee record**, and that case has bitten five screens.
* **User ↔ Role is many-to-many but capped at one** (D-044).

New in session 09:

* **`ImportSource` / `ImportRun` / `ImportIssue`.** The run's `plan` is a JSON
  blob holding columns, votes, transforms, value maps, **enrichments**,
  **code_policy** and **apply_fixes**. It is written once by the mapper, edited
  by the operator, and read back whole.
* **`Segment`** stores *criteria*, not a list of people, so it means the same
  thing next month.
* **`Bond`** carries `remaining_liability` pro-rata by months served — the
  figure a mass-exit preview totals.
* **`BulkOperation`** stores its preview *and* its result, so what was promised
  can be compared with what happened.
* **`Playbook` / `PlaybookEvent`** with a unique constraint on
  (playbook, employee) so a rule does not refill the inbox nightly.

---

## 7. What is DONE — and how to prove each

Run these; do not take my word for it.

| Area | Proof |
|---|---|
| Backend suite | `manage.py test` → **314 tests OK** |
| The five graded rules | `verify_rules.py` → **28/28**, at 22 employees *and* at 200 |
| The permission model | `audit_permissions.py` → every cell, 16 refusals |
| HTTP layer | `smoke_api.py` → **53/53** |
| Every UI create/update payload | `probe_forms.py` → **26/26** (needs a live server) |
| Local model | `manage.py ai_doctor` → all pass, 711 ms warm |
| Frontend build | `npm run build` → clean, ~835 kB JS |
| **Admin-only enforcement** | 9 endpoints × 4 other roles → **all 403**; menu absent for all four |
| Import, end to end | `04-fieldforce-incomplete.xlsx` + `04b` → 11 employees, 11 contracts, 2 departments, walked in a browser |
| Import, control case | `01-meridian-complete.xlsx` → 22/22, zero issues |
| Annual-salary detection | `03-northgate-legacy-export.xlsx` → `scale ÷12`, 1080000 → 90000.00 |
| Second-file join | 14 of 16 on `Staff ID`, names the two it could not find |
| Employee numbering | `EMP/2021/0023…`, continuing from the 22 already issued |
| Segments from a sentence | *"interns who have been here more than 6 months"* → 2 people, named |
| Playbooks | `run_playbooks --dry-run` → 9 events across 2 rules |

Everything from sessions 01–08 still holds. The 22 original screens are
untouched.

---

## 8. What is HALF-DONE

### T-107 / B-036 — the demo script. This is the whole job.

`claude/deliverables/demo-script.md` is stale in **two** ways now.

**One**, inherited: its figures were verified in session 08 but its *prose*
predates the permission rebuild. Five specific things changed under it and were
never folded in:

* **Reports opens on February 2026, 20 payslips** (was March's single payslip). D-051.
* **The register exports as `register-February-2026.csv`**, a distinct file per
  month (was `register.csv` every time). D-052.
* **Employees → Change Requests** is a menu entry, Admin and HR Manager only. D-056.
* **A leave request reads "To Approve"**, not Draft, and HR sees Approve/Refuse. D-053.
* The Administration dashboard **opens on an empty audit log** after a reseed and
  fills as the demo signs in. D-050. Worth saying aloud — it is a better story
  than a table of stale rows.

**Two**, new and larger: an entire top-bar group — **Workforce**, with six
entries — does not appear in the script at all.

**What to do**: seed, start both servers, sign in as `aarav@oxp.com`, read
scenario A aloud A1→A10 against the screen and fix the words. Then B. Then
**write a scenario C for the Import Studio** as `admin@oxp.com`; the narration
is already in `test-data/README.md` and the click-path is in §14 below.

### T-156 / B-037 — the 240-row import has not been watched

`06-vantage-240-headcount.xlsx` is proven through the API only. Low risk — the
render is bounded and the code path is identical to the files that were walked —
but it is the file you would show for scale and nobody has watched it. **Ten
minutes.**

### T-157 — the seed size is an open question

The user asked for "at least 200 employees". `--employees 200` is verified
(223 contracts, 545 payslips, 28/28 rules). D-066 chose **not** to make it the
default because the script's three-month narrative quotes figures that only
hold for 22 people, and told the scale story through the 240-row import instead.
**That choice was made without the user confirming it. Ask them.**

---

## 9. NOT STARTED, in priority order

1. **T-107 / B-036 — the demo script.** Everything else is optional.
2. **T-156** — walk the 240-row import. Ten minutes.
3. **T-157** — confirm the seed size with the user.
4. **T-134 / B-034 — the leave self-approval guard.** Real, small, not reachable
   in the demo.
5. **T-126 / B-032** — two reads answer 400 for an account with no employee.
   Cosmetic; deliberately left alone four times.
6. **T-127 / B-033** — a frontend test runner. Session 09 is more evidence:
   six of its nine defects were frontend-adjacent and every one was found by hand.
7. **T-111** — Ledger's primary button is 3.05:1, failing WCAG AA at 13px. One
   token closes it, but Ledger is the shipped signature look and is fixed by
   `ui-design-language.md` §2. **Needs the user's decision and has been carried
   unasked across four sessions. Ask them.**

### Dead — do not resurrect without the user asking

Nothing. **Note that session 08's briefing said "the AI features are dead" — that
is superseded.** The user re-commissioned them in session 09; they are built,
tested and on `main`.

---

## 10. Decisions already made — do not relitigate

Full rationale for each is in `claude/context/decisions.md`.

| ID | Decision |
|---|---|
| **D-057** | The local model is **one voter of three** and never the decider |
| **D-058** | The model is given the profiler's **evidence**, not raw values — 3/6 → 6/6 |
| **D-059** | Local model only. Headers + evidence + 3 samples reach it; full rows never do |
| **D-060** | The bulk and inference tools are **Admin-only** (the user's instruction) |
| **D-061** | Cross-company vocabulary resolves from a **dictionary** before the model, and only for closed taxonomies |
| **D-062** | A second file is held to a **higher confidence bar** (0.6) than the first |
| **D-063** | Employee numbering is **always asked**, never assumed |
| **D-064** | Demo files live **on disk**, not behind buttons in the app |
| **D-065** | **One place** decides what is still missing — column, second file and accepted fix are pooled |
| **D-066** | The default seed stays at **22 employees** |
| D-041–D-043 | Payroll User reads and writes nothing; HR and Payroll Managers are **siblings, not a ladder**; salary rules are Admin-writable only |
| D-044 / D-045 | One role per account; breadth of read decided by a **read** capability |
| D-050–D-056 | Session 08's reseed and approval-workflow decisions |
| D-033 / D-034 | March off-cycle stays `Computed`; the dashboard opens on the newest **paid** period |
| D-021 / D-023 | Employer contributions never move gross or net; pay prorates to the contract's own dates |
| D-011 / D-012 | SQLite, not Postgres; `claude/` is updated **only** at MEGATRON LAUNCH |
| D-010 / D-018 | No machine attribution in commits; no character name in subjects |
| D-040 | Git history is left as it is. Closed |

---

## 11. Known bugs and blockers — including what was already tried

* **B-036 — the demo script is badly out of date.** See §8. **Already tried:**
  nothing. Session 09 never reached it. This is not a failed attempt, it is
  simply undone, and it is the most valuable thing left.
* **B-038 (confirms B-029) — `main` is held by an abandoned worktree.**
  `.claude/worktrees/frontend-routing-setup-e9a159` holds `main` at a ref **41
  commits behind `origin/main`**. `git checkout main` fails here. **The working
  approach**, used cleanly this session: branch from `origin/main`, merge into
  that, `git push origin HEAD:main`. **Do not** try to repair the other
  worktree — it belongs to an abandoned session.
* **B-039 — `git merge --squash` picks the wrong base** when replaying onto a
  branch whose history was squashed. It conflicted in `urls.py` and `App.jsx`.
  **What works instead:** `git read-tree -u --reset <commit>` then commit, and
  **assert tree equality** afterwards. That assertion is how session 09 proved
  the four-branch reorganisation lost nothing.
* **B-040 — long text must go through a file, never a shell heredoc.** This bit
  **twice** in session 09 and once silently: a heredoc turned `\n` inside a
  Python string into a real newline, splitting three literals and leaving
  `seed.py` unparseable — and the first repair reported success while changing
  nothing, because the file was CRLF and the pattern was LF. **Write with the
  Write tool to the scratchpad, then `cat >>` or `git commit -F`.**
* **B-037 — the 240-row import is unwatched.** See §8.
* **B-034 — leave approval has no self-approval guard.** `timeoff/api.py::approve`
  checks only `can_approve_leave`. **Already checked:** not reachable in the demo
  — `sara@oxp.com` has zero own pending requests and `admin@oxp.com` has no
  employee record. Not fixed because it would change the seeded approval queue.
* **B-032 — two reads answer 400 for an account with no employee.**
  `/api/attendance/status/` and `/api/me/profile/`. **Already decided:** left
  alone four times, deliberately; both UIs handle it and the change touches a
  demo path.
* **B-033 — no frontend tests.** **Already tried:** nothing beyond the manual
  walk; no runner is installed. The instrumented route walk in §13 is the cheap
  substitute.
* **B-028 — one account, one live session.** Any login deletes that account's
  existing token. Running a harness signs out a browser on the same account.
  **This cost session 07 thirty minutes** because it looks exactly like an idle
  timeout.
* **B-030 — two sessions once ran in parallel.** Check before you write.

---

## 12. Your first three actions

**1. Boot and confirm the baseline is real.**

```bash
git fetch origin
git config user.name "<yours>" && git config user.email "<yours>"
cd project/backend
./.venv/Scripts/python.exe manage.py test        # expect 314 OK
./.venv/Scripts/python.exe manage.py seed --flush
```

If `manage.py test` fails on `ModuleNotFoundError: openpyxl`, your venv predates
session 09 — re-run `pip install -r requirements.txt`.

**2. Start both servers.**

```bash
./.venv/Scripts/python.exe manage.py runserver   # terminal 1
cd ../frontend && npm install && npm run dev     # terminal 2
```

**3. Do T-107. Read the demo script aloud against the screen.**

Open `claude/deliverables/demo-script.md`, sign in as `aarav@oxp.com` /
`demo1234`, and fix the words. Then add scenario C for the Import Studio.

**Commit the script.** It is the last graded deliverable that is wrong.

---

## 13. Traps — these cost real time

1. **Any login rotates that account's token** (B-028). If a browser session dies
   for no reason, ask what you just ran.
2. **Never print non-ASCII from a management command or script** (B-006). It
   killed a packing script once *after* it had edited a file in memory but
   before writing it — silent and partial.
3. **Heredocs mangle escapes, twice over** (B-020, B-040). Write to the
   scratchpad with the Write tool, then `cat >>` or `git commit -F`. Never put a
   long commit message in `-m`.
4. **Never add `--noreload` to `runserver`** (B-016).
5. **`worked_days > expected_days` is a real signal.** It has twice meant the
   seed generated attendance a contract does not allow.
6. **An account with no employee record is a real case** and has broken five
   screens. `admin@oxp.com` is that account — and it is now also the *only*
   account that can see the Workforce menu, so every new screen was written
   against it.
7. **A screen that inherits its scope from the server is a screen whose scope
   you cannot see.**
8. **To find frontend bugs cheaply**, inject a collector and walk every route:
   patch `console.error`, `window.onerror`, `unhandledrejection` and
   `window.fetch` into an array, then set `location.hash` around all routes and
   dump it. Do it **as each of the five roles**.
9. **The frontend calls `http://127.0.0.1:8000`, not its own origin.** A `fetch`
   to a relative `/api/...` path from the browser console 404s against Vite.
10. **Verify a new regression test fails against the old code.** Ninety seconds,
    and a test that passes either way is decoration.
11. **Harnesses dirty the demo; the seed is the reset.** `smoke_api.py` and
    `audit_permissions.py` both write. Always `seed --flush` before presenting.
12. **NEW — the browser cannot read local files.** To drive a file upload from
    the console, copy the file into `project/frontend/public/` temporarily,
    `fetch` it, build a `File`, and dispatch a `change` event at the input.
    **Delete it afterwards** — session 09 did.
13. **NEW — a React controlled input ignores a native `value` set.** Setting
    `input.value` from the console does nothing. Use the native setter from
    `HTMLInputElement.prototype` and dispatch `input`.
14. **NEW — regenerating `test-data` churns line endings.** `.gitattributes`
    now pins the CSV to LF. If you see a twelve-line diff on
    `05-northwind-acquisition.csv` with no content change, that is what it is.

---

## 14. Demo script status

`claude/deliverables/demo-script.md` — **figures verified (session 08),
mechanics walked (session 08), prose stale, and an entire feature area missing.**

| Scenario | Status |
|---|---|
| A — the payroll run end to end | Every figure confirmed on screen. **Menu and role prose not rewritten** |
| B — leave and the allocation gate | Confirmed: *Allocated 20.00 · Taken 2.00 · Remaining 18.00*, and the gate refuses with real wording |
| Criterion 4 — two distinct warnings | **Proven by walking the wizard.** `DUPLICATE` on creation, `AC_MISSING` ×2 after Compute |
| **C — the Import Studio** | **DOES NOT EXIST. Write it.** |

### Scenario C, ready to be written up

Sign in as `admin@oxp.com`. **Open `test-data/import/04-fieldforce-incomplete.xlsx`
in Excel first** and let the room see the mess — sixteen people, no email
column, no bank details, no employee codes, two with no joining date, three with
no salary.

Then **Workforce → Data Import** and drag that same file in.

1. It reads the file: 7 columns colour-coded, *"Read 7 headers. Mapped 7
   automatically. qwen2.5:7b answered in 4.0s."*
2. **Complete the data** lists what is missing. Work email is flagged blocking;
   Preview is disabled.
3. **Build from names** → resolves, ticks green, Preview unlocks.
4. **Fetch from a file** → open `04b-fieldforce-bank-details.xlsx` in Excel too,
   then drop it in. It finds the join itself: *"14 of the 16 values in 'Staff
   ID' also appear in 'Staff ID'"*, and names the two people finance never sent.
5. **Choose numbering** → `EMP/2021/0023…`, continuing from the 22 already
   issued rather than colliding.
6. **Preview** → before/after per cell; values from the second file tinted and
   captioned; five unimportable rows greyed **with reasons**.
7. **Import 11 employees** → 11 employees, 11 contracts, 2 new departments.

The line worth saying at step 4: *nobody told it which column to join on — it
worked that out by measuring which two columns share values.*

The line worth saying about the whole thing: *the model reads meaning; every
structural decision is arithmetic. Turn the GPU off and it still maps ten of
thirteen columns and says so.*

Two other files worth thirty seconds each: `03-northgate-legacy-export.xlsx`
(the salary is **annual** and only the distribution reveals it — watch it
propose ÷12 and show 1080000 → 90000.00) and `06-vantage-240-headcount.xlsx`
(240 people onboarded live).

**There is also still the thirty-second permission talking point** from session
07: sign in as `rahul@oxp.com`, open a payrun, show Compute and Validate are
*absent*; sign in as `aarav@oxp.com`, show them present. The line is *the person
who processes pay is not the person who decides it.*

---

## One last thing

The build is done and it is good: 314 tests, five green harnesses, a permission
model a judge will recognise as a real control, three months of payroll whose
movement you can explain line by line, and now a migration story that answers
the first question any real buyer asks.

Session 09's lesson is the same one session 08 recorded, and it earned it again:
**every harness was green before it started and green after it finished, and it
still found nine real defects — all nine by driving the product by hand.** Two
of them would have corrupted a customer's payroll silently.

So do not spend your session re-running harnesses. **Spend it finishing the demo
script**, out loud, in front of the screen, the way the judge will hear it.
