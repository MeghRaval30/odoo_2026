# PeoplePay360

Integrated HR & Payroll Operations Platform. Odoo hackathon, 24 hours.

Employee records, contracts, working schedules, attendance and time off feed a
sequenced salary-rule engine that produces payslips, PDFs and a live payroll
dashboard. The point is the connections between those records, not the CRUD
screens around them.

---

## Run it

Two terminals. Backend first.

```bash
cd project/backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py seed --flush
./.venv/Scripts/python.exe manage.py runserver
```

```bash
cd project/frontend
npm install
npm run dev
```

Open http://localhost:5173. Sign in as `admin@oxp.com` / `demo1234`.

On Linux or macOS use `.venv/bin/python` in place of `./.venv/Scripts/python.exe`.

### Verify it works

Four of the five need nothing but the virtualenv:

```bash
cd project/backend
./.venv/Scripts/python.exe verify_rules.py        # 28/28 — business rules
./.venv/Scripts/python.exe smoke_api.py           # 51/51 — HTTP layer
./.venv/Scripts/python.exe audit_permissions.py   # every cell matches PRD 3.2
./.venv/Scripts/python.exe manage.py seed --flush # smoke_api dirties the DB
./.venv/Scripts/python.exe manage.py test         # 173/173 — Django suite, 7 apps
```

The fifth drives real HTTP, so it needs the server running in another terminal:

```bash
./.venv/Scripts/python.exe manage.py runserver    # terminal 1
./.venv/Scripts/python.exe probe_forms.py         # terminal 2 — 26/26
```

Without a server it fails with a `WinError 10061` traceback. That is a missing
server, not a broken harness.

`probe_forms.py` posts the exact body each frontend form builds, rather than an
idealised one. That distinction matters: it caught four create bugs the other
harnesses could not see, because they construct their own correct payloads — and
a fifth once its coverage was completed, on the one create form it had been
missing. It deletes everything it creates.

`audit_permissions.py` walks every role against the PRD 3.2 permission matrix and
reports each cell as OK, LEAK or BLOCK. It exits non-zero if any cell disagrees.

`smoke_api.py` writes to the development database and leaves an
`April 2026 (smoke)` payrun behind. Re-run `seed --flush` before demoing.
`manage.py test` and `audit_permissions.py` do not have this problem — they use
Django's test client against a throwaway database.

---

## Demo accounts

All use the password `demo1234`. The login screen has one-click chips for each.

| Email | Role | Sees |
|---|---|---|
| `admin@oxp.com` | Admin | Everything, plus user management |
| `aarav@oxp.com` | Payroll Manager | Payroll, structures and rules |
| `sara@oxp.com` | HR Manager | HR data, leave approval |
| `rahul@oxp.com` | Payroll User | Payroll, structures read-only |
| `john@oxp.com` | Employee | Own records and the check-in widget |

Roles are enforced server-side. Signing in as the Employee removes the Payroll
menu because the API refuses those endpoints, not because the UI hides them.

---

## The five graded business rules

1. **Period-based contract resolution.** Payroll resolves the contract covering
   the payrun period, not the newest one. Expired contracts still govern the
   period they covered. Two `RUNNING` contracts may not overlap.
2. **Derived weekly hours.** Computed from the schedule's day lines. There is no
   weekly-hours input anywhere in the UI.
3. **Allocation-gated leave.** A type marked *requires allocation* refuses
   requests that no approved allocation covers.
   `Remaining = Allocated − Taken`, both derived.
4. **Sequenced salary rules.** Rules execute in `sequence` order, each result
   visible to later rules. Gross and Net are read from the payslip lines, never
   stored.
5. **Pre-finalization warnings.** Missing bank account, duplicate payslip, no
   contract, negative net and no structure all surface before Validate.

Plus three integrations: attendance drives worked days and Loss of Pay, overtime
is paid through a rule, and unpaid leave deducts.

### The seed proves the numbers are live

| Period | Net | Why it matters |
|---|---|---|
| Dec 2025 | ₹14,73,360 | Lower than January — two employees resolve to older, cheaper contracts |
| Jan 2026 | ₹14,82,320 | |
| Feb 2026 | ₹15,58,668 | Higher — February overtime reached payroll |

Filtering the dashboard to Engineering alone drops February to ₹5,03,589.
Changing Period or Department re-drives every card on the screen.

---

## Stack

React 19 + Vite, Django 6.1 + DRF 3.18, SQLite.

SQLite rather than PostgreSQL is a deliberate decision — neither Postgres nor
Docker is installed on the build machine. `DATABASE_URL` switches engines.

```
project/backend/
  config/      settings, urls, pagination
  core/        Company, Department, JobPosition, WorkLocation, Holiday
  accounts/    User, Role, permission classes
  employees/   WorkingSchedule, ScheduleLine, Employee, Contract
  attendance/  Attendance + check-in widget endpoints
  timeoff/     TimeOffType, Allocation, TimeOffRequest
  payroll/     models, engine, pdf, mail, api
  dashboard/   aggregation only, no models

project/frontend/src/
  api.js       client, token auth, error flattening, formatters
  index.css    design system
  lib/         hash router
  components/  shell, attendance widget, shared primitives
  screens/     one file per screen
```

Money is `Decimal` everywhere. Derived values are Python properties, not
columns — schedule hours, attendance worked hours, allocation balance, payslip
gross/net/worked days/LOP/overtime, and the employee smart-button counts.

---

## Repository layout

`project/` is the product. `claude/` is the build's working memory — the
problem statement, spec, PRD, data model, decisions, task board and the handoff
briefings that carry context between sessions. `claude/source/` holds the
untouched originals.

The UI design language is binding and lives in
`claude/context/ui-design-language.md`.
