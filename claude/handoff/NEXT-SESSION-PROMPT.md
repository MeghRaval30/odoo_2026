# BRIEFING FOR THE NEXT SESSION

**Written by:** Franklin (session 05) · 2026-09-05, 21:40 IST
**You are:** TREVOR (session 06)
**Handoff tag:** `handoff-franklin-05`

Read this in full before touching anything. It replaces the boot sequence.

**Three warnings before you start.**

1. **Trust `current-state.md`, the task board and `git log` over any prose,
   including this document.** Session 03 was handed a two-session-stale briefing
   and nearly rebuilt a working application.
2. **The product works. Your job is to *finish* a commission, not to start
   one.** Roughly 70% of it is done and merged. The remaining 30% is a
   screen-by-screen pass over the older frontend screens, listed file by file in
   §8. Do not rebuild what is there.
3. **Two `runserver` processes were found on port 8000 this session, and the
   stale one answered first.** Before you debug anything that looks like "my
   change did not take effect", read B-021.

---

## §1 — Identity and orientation

You are **TREVOR**, third in the rotation `MICHAEL → FRANKLIN → TREVOR`. Three
teammates each hold a separate Claude account; when one runs low it packs
everything into this repository and the next account's session picks up. You
have no memory of session 05 and no way to read its transcript. **This
repository is the only channel.**

**Before your first commit**, set and verify your git identity:

```bash
git config user.name  "MeghRaval30"
git config user.email "meghraval306@gmail.com"
git config user.name && git config user.email     # VERIFY, do not assume
```

That is Trevor's row from `claude/workflow/git-strategy.md` §1. But **identity
follows the session, not the register** — check which account is actually
authenticated in your chat, and if it is not Trevor's, use the matching row and
say so. Session 02 was caught by exactly this.

GitHub attributes commits by **email**, not display name.

**Commit rules — both binding:**

- No Claude or machine attribution (D-010).
- **No character name in the subject** (D-018). Write `feat(ui): …`, not
  `feat(ui): … [trevor]`.

Work on branches, merge `--no-ff`, tag versions. **Never force-push, never
rewrite history** — `.claude/settings.json` denies both at tool level, deliberately.

---

## §2 — The clock

```
Hackathon start:   2026-09-05  10:00 IST    ✅ confirmed by the user
Hackathon end:     2026-09-06  10:00 IST    ✅ confirmed by the user
Franklin closed 05: 2026-09-05 21:40 IST
Elapsed at handoff: ~11h 40m / 24h        REMAINING: ~12h 20m
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

You have time, but not a lot, and the work in front of you is *breadth* — a
dozen small screens — rather than depth. Budget accordingly and commit often.

---

## §3 — The product, in ~500 words

**PeoplePay360 — an Integrated HR & Payroll Operations Platform.** Odoo
hackathon, 24 hours, any stack.

The problem statement's framing is everything. Basic HR tools store employee
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
representative data, a five-minute demo of two end-to-end scenarios, and a
future roadmap (694 lines).

**Detail:** `claude/context/problem-statement.md`, `claude/context/product-spec.md`
(every field, recovered from the mockup), `claude/context/prd.md` (numbered
requirements). Originals in `claude/source/`.

**A note on the sources.** Session 05 extracted all 1,187 text elements of the
excalidraw board and the full text of the PDF rather than working from memory,
and the role table in §4 below is quoted from PDF §3 verbatim. If you need to do
the same, the extraction is straightforward: the `.excalidraw` file is JSON with
an `elements` array; filter `type == "text"` and sort by `(y, x)`. The PDF needs
`pip install pypdf` in the venv.

---

## §4 — Roles: the authoritative table

This is **PDF §3, quoted**. It is the spine of everything session 05 built, and
it is what you should check any UI decision against.

| Role | The PDF's exact words |
|---|---|
| **Employee** | View own employee details, attendance records, and leave balances. Create attendance entries and Time Off Requests, **with no payroll or HR administration access** |
| **HR Manager** | Full CRUD access to Employees, Attendance, Contracts, Working Schedules, and Time Off modules. Approve or refuse Time Off Requests, **with no access to payroll features** |
| **HR Payroll User** | All HR Manager permissions **plus Create, Read, and Update** access to Payruns and Payslips. **Read-only** access to Salary Structures and Salary Rules |
| **HR Payroll Manager** | All HR Payroll User permissions with **full CRUD** access to Payruns, Payslips, Salary Structures, and Salary Rules |
| **Admin** | Full access to all modules and models. User management, role assignment, permission updates, and complete system administration |

And the mockup's **LOGIN / USER ACCESS NOTE**, also quoted:

> • In the ERP flow, user accounts are created by an Admin.
> • When creating a user, link the account to the relevant employee and assign
>   **one or more roles**.
> • Roles control which modules, records and actions become available after login.
> • **Users must not be able to assign or elevate their own roles.**

Note what follows from "one or more roles": permission is the **union** of the
roles held, never the highest single one.

### The five graded business rules — unchanged, all built and proven

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

Plus three integrations (D-002) — attendance drives worked days and LOP,
overtime is paid through a rule, unpaid leave deducts — and proration (D-023).

---

## §5 — Architecture as actually built

React 19 + Vite · Django 6.1 + DRF 3.18 · **SQLite** (D-011).

```
project/backend/
├── config/         settings.py, urls.py
├── core/           Company, Department, JobPosition, WorkLocation, Holiday
│   ├── formatting.py                    ← NEW: hours_minutes(), days_display()
│   ├── tests.py                         ← NEW: pins the seed's shape
│   └── management/commands/seed.py      ← --employees N lives here
├── accounts/       User, Role, permissions.py, api.py
│   ├── capabilities.py    ← NEW. THE permission table. Read this first
│   ├── security.py        ← NEW. NetworkPolicy, SecuritySetting, LoginAttempt, AuditLog
│   ├── security_session.py← NEW. Per-token activity, for idle timeout
│   ├── authentication.py  ← NEW. ExpiringTokenAuthentication
│   ├── selfservice.py     ← NEW. ProfileChangeRequest + the field split
│   ├── selfservice_api.py ← NEW. /api/me/*, approvals, security admin, audit
│   └── test_security.py   ← NEW. 31 tests, each named after an attack
├── employees/      WorkingSchedule, ScheduleLine, Employee, Contract
├── attendance/     Attendance + check-in widget endpoints
├── timeoff/        TimeOffType, Allocation, TimeOffRequest
├── payroll/        models, engine.py, pdf.py, mail.py, api.py
├── dashboard/
│   ├── api.py         payroll dashboard (now capability-gated)
│   └── role_views.py  ← NEW. /hr/, /me/, /admin/ dashboards
├── verify_rules.py · smoke_api.py · probe_forms.py

project/frontend/src/
├── api.js          auth.has(capability), refreshMe(), hoursMinutes()
├── index.css       ← REWRITTEN. Pure tokens, nothing hard-coded
├── themes.css      ← NEW. Six design languages
├── lib/theme.js    ← NEW. applyTheme / currentTheme / THEMES
├── components/Shell.jsx   ← REWRITTEN. Server-built nav, profile menu, theme picker
└── screens/        22 screens; five of them new this session
```

**Conventions that matter.** Money is `Decimal` everywhere. Derived values are
Python properties, never columns — `worked_hours`, `gross`, `net`, `remaining`
are all computed. Hiding a control in the UI is never enforcement; the
permission classes enforce.

### The capability matrix — how it works

`accounts/capabilities.py` declares capability constants
(`resource.action[.scope]`), a `BASELINE` every signed-in account holds
unconditionally, and `ROLE_CAPABILITIES` mapping each of the five roles to a
frozenset. `capabilities_for(role_codes)` returns the union.

- `User.capabilities` — cached frozenset · `User.can("payrun.delete")`
- `RequiresCapability(read=…, write=…, delete=…)` in `permissions.py` builds a
  DRF permission class straight from it. The separate `delete` argument is what
  distinguishes the Payroll User's "Create, Read, and Update" from the Payroll
  Manager's "full CRUD".
- `NAVIGATION` + `navigation_for(caps)` build the top bar.
- `dashboard_for(caps)` decides which home screen an account lands on.
- The four legacy booleans (`is_admin`, `can_manage_hr`, `can_run_payroll`,
  `can_configure_payroll`) are now *views* onto the matrix, not a second copy.

**If you need a new rule, add a capability there. Do not put a role check
anywhere else.**

### New API surface

```
GET   /api/auth/me/                    + capabilities, navigation, home_dashboard
POST  /api/auth/login/                 lockout, network check, audit
GET   /api/me/profile/                 own record, split editable/approval/read-only
PATCH /api/me/profile/update/          direct fields only; anything else is refused by name
POST  /api/me/profile/request/         raise an approval-gated change
POST  /api/me/password/                needs current password; ends other sessions
GET   /api/me/sessions/                where you are signed in
GET   /api/profile-change-requests/    scoped: HR sees all, others see their own
POST  .../{id}/approve|refuse|cancel/
GET   /api/dashboard/       payroll — now gated on dashboard.payroll
GET   /api/dashboard/hr/    workforce, no money on it at all
GET   /api/dashboard/me/    the employee's own screen
GET   /api/dashboard/admin/ accounts, sessions, posture, audit tail
GET/PATCH /api/security/settings/
CRUD  /api/security/networks/
GET   /api/audit/
POST  /api/users/{id}/reset-password/
GET   /api/users/capability-matrix/    the whole grid, for the Users screen
```

---

## §6 — Data model, the parts that matter

Unchanged from session 04 except for five new models, all in `accounts`:

| Model | Why it exists |
|---|---|
| `NetworkPolicy` | A CIDR sign-in may come from, optionally scoped to one Role |
| `SecuritySetting` | Singleton. Lockout, session lifetimes, enforcement switches |
| `LoginAttempt` | Every sign-in, successful or not. Drives lockout |
| `AuditLog` | Append-only. Money, access and identity actions only |
| `SessionActivity` | Per-token last-used, so a session can idle out |
| `ProfileChangeRequest` | One row per field an employee wants changed |
| `SessionActivity` and `AuditLog` are never edited through the API |

**The self-service split**, in `accounts/selfservice.py`:

- `DIRECT_FIELDS` — work phone, personal phone, personal email, address. Applied
  immediately, logged.
- `APPROVAL_FIELDS` — first name, last name, date of birth, gender, PAN, **bank
  account number, bank IFSC**. Raised as a request, decided by HR.
- `SENSITIVE_FIELDS` — the three bank/PAN ones. Flagged red on the review screen.
- `READ_ONLY_FIELDS` — department, position, manager, schedule, type, joining
  date, employee code, work email. Shown, never editable by the employee.

---

## §7 — What is DONE, and how to prove it

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py migrate           # 0003 and 0004 are new
./.venv/Scripts/python.exe manage.py test              # 216 tests
./.venv/Scripts/python.exe verify_rules.py             # 28/28
./.venv/Scripts/python.exe smoke_api.py                # 51/51
./.venv/Scripts/python.exe manage.py seed --flush      # smoke_api dirties the DB
./.venv/Scripts/python.exe manage.py runserver         # terminal 1 — NOT --noreload
./.venv/Scripts/python.exe probe_forms.py              # 26/26, terminal 2
cd ../frontend && npm run dev                          # terminal 3
```

Everything from sessions 01–04 still stands. **New and verified this session:**

| | Proof |
|---|---|
| `seed --employees N` | 250 seeds in 40 s. `core/tests.py` pins the default seed byte-for-byte |
| Payroll scale | Payrun of 20: 0.6 s. Of 233: 5.7 s. Linear at ~32 ms/payslip. PRD-7.2 wants <5 s for 20 ✅ |
| PRD criterion 4 at scale | March payrun on 250 raises `NO_CONTRACT` ×8 + `AC_MISSING` ×13 |
| Capability union | `accounts/test_security.py::test_holding_two_roles_grants_the_union_of_both` |
| HR Manager has no payroll | `test_an_hr_manager_has_no_payroll_capability_at_all`, and verified in a browser |
| Employee menu | Browser: exactly Dashboard · Attendance · Time Off · My Payslips |
| HR dashboard | Browser: headcount 22, 4 awaiting, coverage 100%, average day **8h 43m**, overtime **124h 38m carried by 22 employees**. No money |
| Network-restricted sign-in | `test_sign_in_is_refused_from_outside_the_permitted_network`, and the role-scoped and forwarded-header variants |
| Sessions expire | `SessionLifetimeTests` — absolute, idle, and leaving the network mid-session |
| Bank change needs approval | `test_a_bank_account_cannot_be_changed_directly` and the approval round-trip |
| Nobody self-approves | `test_nobody_approves_a_change_to_their_own_record` |
| Escalation guards | Cannot change own roles, deactivate self, or remove the last admin |
| Attendance anti-gaming | Own record only, today only, colleague's id refused, HR correction flagged |
| `npm run build` | Clean. 742 kB JS, 24 kB CSS |

---

## §8 — What is HALF-DONE — **this is your job**

The working tree is clean and everything is merged. What is unfinished is the
**commission**, not the code. Concretely:

### 8.1 The screen-by-screen pass (T-100 … T-105)

New screens speak the new design language. The pre-existing ones do not. In the
order I would do them:

| # | File | What to change |
|---|---|---|
| 1 | `screens/Login.jsx` | The mockup gives exact copy: heading **"Welcome back"**, sub **"Sign in to continue to your workspace"**, fields **"Work Email"** (placeholder `name@company.com`) and **"Password"**, button **"Sign In"**, and a **"Forgot password?"** link. Also add a line the mockup carries: *"Accounts are created by an administrator."* Decide what to do with the five demo-account buttons — they are useful in a demo and wrong in a product; consider keeping them behind a dev-only flag |
| 2 | `components/AttendanceWidget.jsx` | The mockup's popup shows `6h56`, not `6.93`. `/api/attendance/status/` already returns `elapsed_hm` and `total_today_hm` in exactly that form. It also returns `can_punch` and `punch_blocked_reason` — surface the reason when the network policy refuses a punch, or the button will look broken |
| 3 | `screens/Attendance.jsx` | Swap the `worked_hours` / `overtime_hours` columns for `worked_hm` / `overtime_hm`. The API serves both; the decimal stays for payroll |
| 4 | `screens/Dashboard.jsx` | The Attendance Overview tile still shows an overtime **count** — the exact thing the user called out. `/api/dashboard/` now returns `total_overtime_hm`, `overtime_employees` and `average_worked_hm`. Show "124h 38m carried by 22 employees", as the HR dashboard already does |
| 5 | `screens/Users.jsx` | Pre-dates the matrix. It needs: multi-role checkboxes (an account may hold several), the account-status switch, the **Reset password** action (`POST /api/users/{id}/reset-password/`), and ideally the capability grid from `GET /api/users/capability-matrix/` so an admin can see what a role actually grants. The mockup's User Management screen has columns **User · Employee · Work Email · Role · Status**, a search box, and a **Role Filter** |
| 6 | every other screen | Action buttons are still gated on the four legacy booleans. Move them to `auth.has("payrun.delete")` and friends. The server already enforces correctly — this is the UI catching up so buttons that would 403 are not shown |

### 8.2 Four themes have never been rendered (T-106)

Only **Ledger** and **Console** were opened. **Atrium, Blueprint, Marigold and
Graphite are unproven.** Open each one, on a list screen and a dashboard, and
check: contrast in both light and dark, the topbar against `--topbar-fg`, badge
legibility, and that Blueprint's `--radius: 0` and 2px borders do not break the
table layout. Do not tell the user six themes work until you have seen six.

Theme is switched from the avatar menu, top right.

### 8.3 The four new screens have never been clicked (T-099)

`Profile.jsx`, `Security.jsx` (and its `AuditLog` export), `MyPayslips.jsx`,
`AdminDashboard.jsx` all build and the Admin dashboard's *data* was confirmed by
API. Nobody has driven them. Walk each one, especially:

- Profile → Personal details → change a phone number → save
- Profile → request a bank-account change → sign in as HR → approve it
- Profile → Password & sessions → change a password → confirm you stay signed in
  (the endpoint rotates your token deliberately and the screen stores it)
- Security → add a network policy → try to switch enforcement on from an
  address it does not cover (the server should refuse and say why)

### 8.4 The demo script is stale (T-107)

`claude/deliverables/demo-script.md` describes the old menu and mentions no
roles, no themes and no profile menu. It was rehearsed and stamped in session
04, and **the RBAC work invalidates parts of it**. Once the screens are done,
re-walk it and update. The new material is a genuinely strong addition to the
demo — signing in as an employee and showing that the payroll menu is *absent*
is a stronger claim than any chart.

---

## §9 — What is NOT STARTED, in priority order

1. **T-100 to T-105** — the screen pass above. This is the commission.
2. **T-090** — PRD criterion 4 on the demo seed. **Needs the user**, see §11.
3. Tests for the new dashboards beyond their capability gate, and for the four
   new screens.
4. `verify_rules.py` and `smoke_api.py` touch no new endpoint. Adding the
   capability checks to `smoke_api.py` would be cheap and valuable.
5. **T-075** frontend tests. Still lowest priority for a 24-hour build.

---

## §10 — Decisions — do not relitigate

Full text with rationale in `claude/context/decisions.md`.

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
| **D-025** | **Roles are capabilities; an account holds the union of its roles** |
| **D-026** | **Where the user's examples contradict the sources, the sources win — but say so** |
| **D-027** | **Six themes, chosen per browser not per account** |
| **D-028** | **Unusable menus are absent, and the menu is built server-side** |
| **D-029** | **Four dashboards behind four endpoints, not hidden cards** |
| **D-030** | **Self-service split by blast radius; bank details need approval** |
| **D-031** | **Sessions expire; the network is re-checked on every request** |
| **D-032** | **Decimal in the data, hours and minutes on screen** |

D-012 governs your rhythm: **commit code as you go, but leave `claude/` alone**
until the user says MEGATRON LAUNCH — except `claude/PROGRESS.md`, which the
user asked to be updated with every commit, and `task-board.md`, which is the
single home for task status.

---

## §11 — Two things that need the user, not you

### 11.1 The user's examples versus the PDF (D-026)

The user gave two examples that contradict PDF §3. Both were resolved in favour
of the PDF, because the same message said to follow the sources strictly — but
they were written down rather than buried, and **if you get the chance, ask**:

1. *"hr manager … cant create a new attendance record"* — the PDF gives HR
   Manager full CRUD on Attendance. Resolved for the PDF, split by intent: an
   employee's own check-in is a **punch** (own record, today only,
   network-gated); an HR Manager's is a **correction** (any record, any date,
   flagged and audited). Both readings are arguably satisfied.
2. *"payroll amanger can see only employee details and holidays"* — the PDF gives
   the Payroll Manager everything the Payroll User has plus full payroll
   configuration. Resolved for the PDF.

### 11.2 PRD criterion 4 on the demo seed (T-090)

Criterion 4 wants "at least two distinct warnings before validation". **Met on
`--employees 250`. Not met on the 22-person demo seed**, where only `AC_MISSING`
fires ×2.

Session 05 investigated properly and **deliberately left it**, because every fix
damages the rehearsed demo:

- `NO_CONTRACT`, `NEGATIVE_NET`, `NO_STRUCTURE` are **ERROR** severity and block
  Validate. Seeding one breaks demo steps A8/A9.
- `DUPLICATE` is warning-severity and is the problem statement's *own named
  example* — but it needs a pre-existing payslip for March 2026, and
  `dashboard/api.py:49` defaults the dashboard period to the newest payrun by
  `period_start`. Seeding a March payrun makes the dashboard open on March with
  one payslip, wrecking demo step C1.

Options, in preference order:

1. **Demo on `--employees 250`.** Both codes fire naturally and it also
   showcases the scale work. Cost: every figure in `demo-script.md` changes and
   must be re-measured.
2. **Seed a March off-cycle payrun and change the dashboard's default period to
   the newest *PAID* payrun** rather than the newest one. That is arguably a
   better default anyway.
3. **Leave it and say so.** One criterion of six; the engine demonstrably
   supports all six warning codes.

**Ask the user. Do not pick silently.**

### 11.3 Still unresolved from session 04 — "remove your commits"

Every commit is authored by one of the three teammates. Exactly one (`12a632f`,
the root scaffold commit) carries a Claude co-author trailer, and that trailer is
why `claude` appears in GitHub's contributor list. Removing it means rewriting
~120 commits and force-pushing, which would break the other teammates' clones.
Force-push and `filter-branch` are denied in `.claude/settings.json` by design.
**Ask before touching history.**

---

## §12 — Your first three actions

**1. Orient and set identity.**

```bash
git pull --rebase
date                                   # recompute the clock yourself
git config user.name "MeghRaval30" && git config user.email "meghraval306@gmail.com"
git config user.name && git config user.email
```

**2. Prove it still works — ten minutes, do not skip.**

```bash
cd project/backend
netstat -ano | grep ":8000.*LISTENING"     # MUST be empty or exactly one pid — B-021
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py test 2>&1 | tail -20
./.venv/Scripts/python.exe verify_rules.py
./.venv/Scripts/python.exe manage.py seed --flush
```

Then start both servers and sign in at `http://localhost:5173` as
`admin@oxp.com` / `demo1234`. Check the avatar menu top right: you should see
the role badges, the profile links and the six theme swatches.

**3. Start T-101.** Branch `feat/ui-screen-pass`. Open
`project/frontend/src/screens/Login.jsx` and bring it to the mockup's copy —
it is the smallest change, the most visible, and it is quoted verbatim in the
mockup so there is nothing to decide.

Then work down the table in §8.1 in order.

---

## §13 — Traps that cost time

Full list in `claude/state/blockers.md`. These are the ones that will bite you.

1. **Two servers on one port** (B-021). A stale `runserver` from an earlier
   session answered before the new one and served pre-fix code. The symptom is
   indistinguishable from "my edit did not apply". `netstat -ano | grep ":8000"`
   **before** debugging anything of that shape. Related: never use
   `runserver --noreload` (B-016).
2. **Bash heredocs silently append nothing** (B-023, and B-020 before it).
   Confirmed twice more this session. A `cat >> file << 'EOF'` block containing
   triple quotes, backticks or an apostrophe fails with `unexpected EOF` and
   **changes nothing while looking like it worked**. Use the Write/Edit tools for
   any multi-line change; if you must append to an append-only document, Write
   the section to the scratchpad and `cat` that file in.
3. **Browser refs go stale after `resize_window`** (B-022) and `form_input` does
   **not** reach React's controlled state. Both cost time this session. The
   reliable way to drive the app as a given role is `javascript_tool`:

   ```js
   const r = await fetch('http://127.0.0.1:8000/api/auth/login/', {
     method:'POST', headers:{'Content-Type':'application/json'},
     body: JSON.stringify({email:'sara@oxp.com', password:'demo1234'})});
   const d = await r.json();
   localStorage.setItem('pp360_token', d.token);
   localStorage.setItem('pp360_user', JSON.stringify(d.user));
   location.hash = '#/dashboard'; setTimeout(() => location.reload(), 50);
   ```

   To force a theme, also `localStorage.setItem('pp360_theme', 'blueprint')`.
4. **Date windows anchored to `today` are empty** (B-025). Seeded data ends March
   2026; the machine clock reads September. Anything that windows on "this
   month" shows zeroes. `dashboard/api.py::_filters` and the employee dashboard
   both fall back to real data — copy that pattern in any new panel.
5. **`bulk_create` skips `save()`** (B-024), so `EMP/…` and `CON/…` references
   must be minted by hand. `seed.py::_sequencer()` does it.
6. **The console is cp1252** (B-006) — never print `₹` from a management command.
   It aborted a seed once, *after* data had been written.
7. **A harness that counts bytes proves nothing** (B-017). `smoke_api.py` once
   asserted a PDF was `application/pdf` and >1,500 bytes and stayed green while
   every money figure on it rendered wrong.
8. **`pdftotext` misreads subset fonts** (B-018) — check the ToUnicode CMap for
   `<01> <20B9>` instead. And the Browser pane will not render a PDF (B-019); it
   triggers a download.

---

## §14 — Demo status

`claude/deliverables/demo-script.md` was rehearsed and stamped in session 04 and
**is now partly stale** — it describes the old menu and knows nothing about
roles, themes or the profile menu. Scenario A (employee → payslip) and Scenario B
(allocation → request) still run: none of session 05's work touched the payroll
engine, the seed's demo roster or any of the flows those scenarios walk.

The seeded records the script depends on are **unchanged and pinned by
`core/tests.py`**: John Dsouza `EMP/2025/0003` with two contracts, Aarav Mehta's
raise, Anita Oliver and Meera Iyer with no bank account, Priya Sharma's 20/0/20
allocation, Audrey Peterson's 20/3/17, and December ₹14,73,360 · January
₹14,82,320 · February ₹15,58,667.87.

**When you finish the screens, re-walk the script and update it.** And consider
adding a short third beat: sign in as `john@oxp.com` and show that the Payroll
menu is *absent*, not greyed out. "Here is the same application, and this person
cannot reach payroll at all" is a stronger claim about role-based access than
any screenshot of a permissions table.

---

## Closing note

The hard thinking is done and written down. What is left is a dozen small,
well-specified screen edits, four themes to look at, and one question to put to
the user. Work down §8.1 in order, commit after each screen, keep
`claude/PROGRESS.md` updated as the user asked, and you will finish this
comfortably.

Good luck, Trevor.
