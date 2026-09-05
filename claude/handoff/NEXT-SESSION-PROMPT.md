# NEXT SESSION — you are FRANKLIN, session 08

> Rewritten from scratch by Michael at MEGATRON LAUNCH, 2026-09-06 01:05 IST.
> Never append to this file. Rewrite it.

---

## 1. Identity and orientation

You are **Franklin**, the eighth session of a relay building PeoplePay360 for a
24-hour Odoo hackathon. Three Claude sessions work this project in rotation on
three teammates' separate accounts:

> **MICHAEL → FRANKLIN → TREVOR → (repeat)**

Michael just finished session 07. You have **no memory** of it. Every handoff is
a cold start in a brand-new chat, possibly on a different machine. **This
repository is the only channel between sessions.** Anything not written to a
file and pushed is gone.

### Before your first edit

```bash
git pull --rebase
git config user.name  "Robo9327study"
git config user.email "rajstudy9327@gmail.com"
git config user.name && git config user.email    # VERIFY. Do not assume.
```

Your identity row is in `claude/workflow/git-strategy.md` §1. Getting it wrong
is **not silently recoverable** — fixing misattributed commits needs a history
rewrite, which this relay forbids.

Then: work on a branch, merge with `--no-ff`, never force-push, never rewrite
history. `main` stays working at all times.

**Check whether another session is running before you write anything** (B-030).
Two sessions both numbered 06 ran in parallel once and it was only luck that
they touched different files.

---

## 2. The clock

```
Start:  2026-09-05 10:00 IST      End: 2026-09-06 10:00 IST
Michael closed session 07 at 2026-09-06 01:05 IST
Elapsed ~15h 05m   REMAINING ~8h 55m
```

**Run `date` yourself.** By the time you read this it will be less.

| Remaining | Phase |
|---|---|
| > 8h | BUILD |
| < 8h | **FREEZE — bugfix and polish only** |
| < 4h | POLISH — seed data, rehearsal, roadmap |
| < 2h | DEMO — rehearse only, touch nothing |

You are at or past the FREEZE boundary. **There is no feature left that the
graded deliverables need.** The board is complete apart from rehearsal. The
biggest risk left in this project is you breaking something that works.

---

## 3. The product, in about 500 words

**PeoplePay360** is an integrated HR and payroll operations platform for a
single Indian company. It is deliberately **not a CRUD app with a payroll table
bolted on**. The thing being graded is that HR data *drives* payroll through
rules a human can inspect.

An **Employee** has a **Contract** which carries a wage, a salary structure and
a working schedule. The contract is period-resolved: an employee may have many
contracts over time, and payroll for December must use the contract that covered
December, not the one running today. A **Working Schedule** defines the days and
hours of a working week, and its weekly hours are **derived from its lines**, not
typed in. **Attendance** records real check-in/check-out, from which worked days,
worked hours and overtime are computed. **Time Off** is requested against an
**Allocation** — a balance that must exist and be approved before leave can be
taken — and unpaid leave becomes a payroll deduction.

A **Payrun** covers a period and a set of employees. Computing it produces one
**Payslip** per employee, and each payslip is a sequence of **Payslip Lines**,
one per **Salary Rule** that fired. Rules run in sequence and later rules can
read earlier results by code, which is how `HRA = 40% of BASIC` and
`PF = 12% of BASIC` work without anybody hard-coding arithmetic. Before a payrun
can be validated, it is checked, and problems surface as **warnings** — a
missing bank account, a duplicate payslip, a negative net.

The locale is India: rupees, PF, ESIC, Professional Tax, LWF. Employer
contributions are computed and reported as cost-to-company but **never move the
employee's gross or net** (D-021).

The other half of the product is **who may do what**. Sessions 06 and 07 turned
this from a five-row matrix into a real separation of duties: HR owns people,
payroll owns the payrun, and only an Admin holds both. The top bar is built
**server-side** from the signed-in account's capabilities, so a role that cannot
use a menu does not see it — and the same table enforces the API, so hiding a
control is never mistaken for enforcing a rule.

The demo's headline evidence is three months of real payroll where
**December < January < February**, and each gap has a cause you can point at:
December is *lower* than January because two employees resolve to older, cheaper
contracts, and February is higher because of overtime. That is the sentence the
whole build exists to let someone say.

---

## 4. The five graded business rules

These are the product. Everything else is scaffolding around them.

| # | Rule | Acceptance |
|---|---|---|
| 1 | **Period-based contract resolution** | An employee with two contracts gets December's pay from December's contract. `john@oxp.com` has ₹1,03,000 for December and ₹1,10,000 for January — `core/tests.py` pins both |
| 2 | **Derived weekly hours** | A schedule's hours per week come from its lines, never typed. "40 Hours / Week" derives 40.00h over 5 days; "Part-time 20h" derives 20.00h over 4 |
| 3 | **Allocation-gated leave** | A leave request without an approved allocation covering it is refused. The gate runs in the serializer's `validate()`, against the *requester's own* balance |
| 4 | **Sequenced salary rules** | Rules run in `sequence` order and later rules read earlier results by code. `verify_rules.py` proves all 28 checks |
| 5 | **Pre-finalization warnings** | A payrun with a blocking error cannot be validated or paid. Proven end to end: a negative net raises `NEGATIVE_NET` at ERROR severity, `can_validate` goes false, and `validate_payrun` refuses |

**PRD success criterion 4** — that two *distinct* warning codes fire during the
demo — is met by design: the seed leaves a March off-cycle payslip in `Computed`
so the March payrun the operator creates finds a `DUPLICATE` alongside two
`AC_MISSING` (D-033). **Do not mark that March run paid.**

**Three D-002 integrations** must remain visible: attendance → worked days/LOP,
overtime → a salary rule, unpaid leave → a deduction.

---

## 5. Architecture as actually built

```
project/
  backend/        Django 6.1.1 + DRF 3.18, SQLite (D-011)
    accounts/     identity, roles, THE CAPABILITY MATRIX, security, audit
    employees/    Employee, Contract, WorkingSchedule, ScheduleLine, reference data
    attendance/   Attendance + the check-in widget's endpoints
    timeoff/      TimeOffType, Allocation, TimeOffRequest
    payroll/      SalaryStructure, SalaryRule, Payrun, Payslip, engine.py, pdf.py
    dashboard/    the four role dashboards
    core/         Holiday, formatting, the seed command
  frontend/       React 19 + Vite, no router library (hash routing in lib/router.js)
```

### The one file that matters most

**`project/backend/accounts/capabilities.py`** is the single home of "who may do
what". It holds the capability vocabulary, the five role sets, the navigation
manifest, and which dashboard each role lands on. Permission classes, the menu
and the frontend all read this one table.

The model properties (`user.is_admin`, `can_manage_hr`, `can_run_payroll`,
`can_configure_payroll`) are **views onto that table**, not separate rules. So
there is exactly one place a role is defined.

**Every viewset now uses `RequiresCapability(read=…, write=…, delete=…)`.** The
older model-flag classes (`CanManageHR`, `CanRunPayroll`, `CanConfigurePayroll`)
still exist in `permissions.py` but are **no longer wired to anything** except
`CanReadOwnPayslips`. Do not reattach them; they cannot express a read/write
split.

### Conventions that are enforced, not just preferred

* **Server-side enforcement, always.** PRD-3.1: hiding a button is not
  enforcement. The inverse is also banned — never offer a control the server
  will refuse.
* **Breadth of read is decided by a read capability** (D-045). Never gate a
  queryset's scope on a write flag.
* **`claude/context/ui-design-language.md` is binding** for any frontend work.
  Palette, density, one action colour, hairlines not shadows, tabular numerals,
  and copy rules that keep the UI from reading as machine-generated. Read it
  before you touch a screen.
* Money is `Decimal`, quantised to 2dp on every line. The derived payslip totals
  carry SQLite's extra precision in memory but DRF quantises before the wire —
  this is fine, do not "fix" it.

---

## 6. Data model, the parts that matter

* **Employee → Contract** is one-to-many. `employee.contract_for_period(start,
  end)` is the resolver for graded rule #1. It deliberately includes `EXPIRED`
  contracts: lifecycle state is not period coverage. A December payrun must find
  a contract that ended in January.
* **Contract → WorkingSchedule → ScheduleLine.** `ScheduleLine` carries
  `day_of_week` (0=Mon), `start_time`, `end_time`, `break_minutes`, and its
  `hours` property is what graded rule #2 derives from. **The seed now reads
  these lines to generate attendance** (D-047).
* **Payslip totals are derived properties, not columns.** `basic`, `allowances`,
  `deductions`, `gross`, `net`, `employer_cost`, `ctc` are all computed from
  `lines`, excluding `is_employer_cost` rows from the employee-side totals.
* **`Payslip` has a unique constraint** on (employee, period_start, period_end)
  — the duplicate guard behind PRD-4.5.2.
* **User ↔ Employee is one-to-one and optional in both directions.** An employee
  can exist with no account; **an account can exist with no employee**, and
  `admin@oxp.com` is exactly that. That case has bitten three screens now — see
  traps.
* **User ↔ Role is many-to-many but capped at one** (D-044). The union logic
  stays because the matrix must be right for any set it is handed.

---

## 7. What is DONE — and how to prove each

Run these; do not take my word for it.

| Area | Proof |
|---|---|
| Backend suite | `manage.py test` → **231 tests OK** |
| The five graded rules | `verify_rules.py` → **28/28** |
| The permission model | `audit_permissions.py` → every cell, 16 refusals, 6 preserved reads, read breadth, rank identity, row scoping |
| HTTP layer | `smoke_api.py` → **53/53** |
| Every UI create/update payload | `probe_forms.py` → **26/26** (needs a live server) |
| Frontend build | `npm run build` → clean, ~750 kB JS |
| 22 routes as Admin and as Employee | walked in a browser, **0 console errors** |
| Robustness | 2,499 fuzzed requests, 0 crashes, 0 anonymous leaks |
| Payslip coherence | 61 payslips × 12 invariants |
| Engine edges | no contract, zero wage, ₹99,99,999 wage, mid-period join and leave |
| Idempotency | recompute changes nothing; a paid payrun refuses recomputation |
| PDF | 12 payslips render real PDFs (~77 kB) with the rupee glyph |

The 22 screens are complete. The seed is idempotent and reproducible
(`random.seed(360)`).

---

## 8. What is HALF-DONE

### The demo script — corrected on paper, unrehearsed in the browser

**This is the whole job.** `claude/deliverables/demo-script.md` has a
**"Session 07 corrections"** section appended at the end and three inline figure
fixes, but nobody has walked it against the current UI. Since it was last
rehearsed:

* the permission model was rebuilt (D-041 to D-044)
* the menus changed for three of five roles
* **Reports → Payroll Dashboard** is a new entry
* the New User dialog uses radios, not checkboxes
* the wordmark is larger

The corrections section also gives you a **thirty-second talking point** worth
using: sign in as `rahul@oxp.com`, open a payrun, show Compute and Validate are
*absent*; sign in as `aarav@oxp.com`, show them present. The line is *the person
who processes pay is not the person who decides it.*

### T-111 — Ledger's primary button is 3.05:1

White on Claude orange fails WCAG AA at 13px. One token (`--on-primary`, or a
darker `--primary`) closes it. **It needs the user's decision**, because Ledger
is the shipped signature look and is fixed by `ui-design-language.md` §2.

---

## 9. NOT STARTED, in priority order

1. **T-107 / T-112 — rehearse the demo.** Everything else is optional.
2. **T-111** — the contrast token. Ask the user.
3. **T-089 — the 300–10,000 employee dataset.** The seed already accepts
   `--employees N` and generates above the fixed 22-person roster, so this is
   running that flag and checking the dashboard and payrun survive the row
   count. Deferred twice by the user. Only after rehearsal.
4. **T-126** — `/api/attendance/status/` and `/api/me/profile/` answering 400
   for an account with no employee (B-032). Cosmetic.
5. **T-127** — a frontend test runner (B-033). Real, but a FREEZE-phase
   decision, not a default.

### Dead — do not resurrect without the user asking

**The AI features.** The user asked for AI to manage a large dataset, chose
local **Ollama** models, then asked for **Ollama to be uninstalled**, which was
done. No code references it. The only remaining route is the Anthropic API,
which sends salary data off the machine — the exact thing local models were
chosen to avoid.

---

## 10. Decisions already made — do not relitigate

Full rationale for each is in `claude/context/decisions.md`. The ones most
likely to be second-guessed:

| ID | Decision |
|---|---|
| **D-041** | The HR Payroll User reads payroll and writes **nothing** |
| **D-042** | HR Manager and Payroll Manager are **siblings, not a ladder**; only Admin holds both |
| **D-043** | Salary rules are readable by payroll, **writable only by the Admin** |
| **D-044** | An account holds **exactly one role** |
| **D-045** | Breadth of read is decided by a **read** capability, never a write flag |
| **D-046** | `seed --flush` resets security settings; harnesses clean up after themselves |
| **D-047** | Seeded attendance follows each contract's **working schedule** |
| **D-048** | A screen whose subject is "mine" **states** its scope rather than inheriting it |
| **D-049** | The wordmark's prominence is size, weight and a hairline — **no colour spent** |
| D-033 | March off-cycle payslip stays `Computed` so criterion 4 fires |
| D-034 | The dashboard opens on the newest **paid** period |
| D-021 | Employer contributions never move gross or net |
| D-023 | Pay is prorated to the contract's own dates |
| D-011 | SQLite, not PostgreSQL — neither Postgres nor Docker is installed |
| D-012 | `claude/` is updated **only** at MEGATRON LAUNCH |
| D-010 / D-018 | No machine attribution in commits; no character name in subjects |
| D-040 | Git history is left as it is — the user was asked and decided. Closed |

**D-041 to D-043 are deliberately narrower than PRD 3.2.** That is recorded, it
is the strongest thing in the build, and `audit_permissions.py` documents the
departure in its own header. Do not "fix" it back toward the matrix.

---

## 11. Known bugs and blockers — including what was already tried

* **B-031 — the demo script's February figure moved.** ₹15,58,667.87 →
  **₹15,58,320.41**, because attendance now follows each contract's schedule.
  Corrected in three places in this pack. December (₹14,73,360) and January
  (₹14,82,320) are **unchanged**, so the headline evidence is intact. *Trust the
  tile on screen over any document.*
* **B-032 — two reads answer 400 for an account with no employee.**
  `/api/attendance/status/` and `/api/me/profile/`. **Already decided:** left
  alone twice, deliberately, because both UIs handle it correctly and the change
  touches a demo path. Nothing else in the API returns an unexpected 4xx — 2,499
  fuzzed requests confirmed that.
* **B-033 — no frontend tests.** Both bugs found in session 07 were frontend and
  both were found by hand. **Already tried:** nothing beyond the manual walk; no
  test runner is installed.
* **B-028 — one account, one live session.** Any login deletes that account's
  existing token (`accounts/api.py:186`). Running a harness signs out a browser
  on the same account. **This cost session 07 about thirty minutes** and a
  background poller to diagnose, because it looks exactly like an idle timeout
  and is not one. Two people cannot demo from the same account simultaneously.
* **B-029 — `main` is held by an abandoned worktree** on at least one machine.
  If you cannot check `main` out, work against `origin/main` and push with
  `git push origin HEAD:main`.
* **B-030 — two sessions once ran in parallel.** Check before you write.

---

## 12. Your first three actions

**1. Boot and confirm the baseline is real.**

```bash
git pull --rebase
git config user.name "Robo9327study" && git config user.email "rajstudy9327@gmail.com"
cd project/backend
./.venv/Scripts/python.exe manage.py test        # expect 231 OK
./.venv/Scripts/python.exe manage.py seed --flush
```

**2. Start both servers and rehearse.**

```bash
./.venv/Scripts/python.exe manage.py runserver   # terminal 1
cd ../frontend && npm run dev                    # terminal 2
```

Sign in as `aarav@oxp.com` / `demo1234` and walk demo scenario A, A1 → A10,
**writing down the number actually on screen at every step**. Read the
"Session 07 corrections" section at the bottom of the demo script *first*.

**3. Fix the script to match what you saw**, then commit it. Trust the screen
over the document, every time.

Only after that should you consider T-111 or T-089.

---

## 13. Traps — these cost real time

1. **Any login rotates that account's token.** See B-028. If a browser session
   dies for no reason, ask what you just ran.
2. **Never print non-ASCII from a management command or script** (B-006). It
   killed a packing script tonight *after* it had already edited one file in
   memory but before writing it — so the damage is silent and partial.
3. **Heredocs mangle escapes** (B-020). `\n` inside `python - <<'PYEOF'` became
   a literal newline and produced an unterminated string. Write the script to
   the scratchpad with the Write tool and run it.
4. **Never add `--noreload` to `runserver`** (B-016). Session 04 lost minutes to
   a server holding pre-fix code.
5. **`worked_days > expected_days` is a real signal.** It has twice meant the
   seed generated attendance a contract does not allow — first holidays, then
   working schedules. There is now a test for it.
6. **An account with no employee record is a real case**, and it has broken
   three screens. `admin@oxp.com` is that account. Check it whenever you touch a
   personal screen.
7. **A screen that inherits its scope from the server is a screen whose scope
   you cannot see.** `MyPayslips` showed three of five roles the entire
   company's payslips for exactly this reason.
8. **To find frontend bugs cheaply**, inject a collector and walk every route:
   patch `console.error` and `window.fetch` to push `{route, message}` into an
   array, then set `location.hash` around all 22 routes and dump it. Both of
   session 07's bugs fell out of this in minutes.

---

## 14. Demo script status

`claude/deliverables/demo-script.md` — **rehearsed at session 05, stamped, and
now stale in its UI details but correct in its figures.**

| Scenario | Status |
|---|---|
| A — the payroll run end to end | Figures corrected; **menus and role behaviour not re-walked** |
| B — leave and the allocation gate | Believed intact; the "Taken two, Remaining eighteen" reading was proven correct in session 04 |
| Criterion 4 — two distinct warnings | Proven **by test and by direct engine run**, not by walking the wizard. That is T-112 |

The March off-cycle payrun exists so the March run the operator creates finds a
`DUPLICATE` next to two `AC_MISSING`. **Leave it in `Computed`.** Paying it would
make a one-payslip run the dashboard's default view (D-034).

---

## One last thing

The build is done and it is good. 231 tests, five green harnesses, a permission
model that a judge will recognise as a real control, and three months of payroll
whose month-over-month movement you can explain line by line.

What it does not yet have is somebody who has *said it out loud* against the
current screens. That is worth more right now than any feature you could add.
Go rehearse.
