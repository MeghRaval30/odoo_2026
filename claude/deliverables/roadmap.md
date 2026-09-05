# ROADMAP

**PeoplePay360 — HR & Payroll** · what this becomes production software

What exists today is a working vertical slice: seven Django apps, twenty-one
models, a DRF API behind five roles, a React front end of seventeen screens,
and a salary-rule engine in `project/backend/payroll/engine.py` that genuinely
computes — Gross and Net are read back from `PayslipLine` rows, never stored, and
recompute is idempotent because of `uniq_line_code_per_payslip`. Attendance and
leave reach the payslip for real (D-002): overtime is paid through a rule, unpaid
approved leave produces LOP days that deduct. 155 Django tests across five apps
pin the five graded rules and the role matrix.

This roadmap is written through one lens: **what would stop a real payroll team
from running February on this system and signing the ECR.** Every item below
names the file or model it touches, because the gap between "demo" and
"production HR software" is not a list of missing modules — it is a list of
places where the current code makes a simplifying assumption that a payroll
manager cannot live with. Items are grounded in the code as it stands on
2026-09-05, not in a generic feature survey.

---

## How to read this

| Horizon | Thesis | Rough size |
|---|---|---|
| **Now** (0–3 months) | Make one company's payroll *defensible* — correct under statute, correctable after a mistake, and provable after the fact | 9 items |
| **Next** (3–9 months) | Survive an auditor, a second company, and a second approver | 8 items |
| **Later** (9–18 months) | Become a platform other systems depend on | 6 items |

Each item states **what**, **why it matters**, and **what it touches** in the
current code.

---

# NOW — 0–3 months

The theme is that the payroll path is *correct for the happy case and silently
wrong for every edge case a real month contains.*

## N-1 · Statutory rules become a versioned rate table

**What.** Lift PF, ESIC, PT and LWF out of ordinary `SalaryRule` rows into a
first-class statutory layer with effective-dated rates, wage ceilings, state
dimensions and periodicity.

**Why it matters.** Today they are seeded as plain rules in
`core/management/commands/seed.py` (`_salary_structures`), and each one carries a
compliance bug that only shows up on a real roster:

- **PF** is `PERCENTAGE 12%` with `percentage_base="BASIC"`. There is no
  ₹15,000 wage ceiling, so a ₹110,000 wage deducts ₹6,600 a month where the
  ceiling-based figure is ₹1,800. Nothing in `SalaryRule` can express "12% of
  min(BASIC, 15000)" except by hand-writing it into a `formula` string.
- **ESIC** *does* respect its ₹21,000 gross ceiling — but as a magic number
  inside a formula string:
  `rules['GROSS'] * Decimal('0.0075') if rules['GROSS'] <= 21000 else Decimal('0')`.
  When the ceiling moves, someone edits that string on every structure of every
  company, and no record survives of what the old ceiling was.
- **PT** is `FIXED ₹200` with no state dimension at all. Professional Tax is a
  state slab; `core.WorkLocation` has only `name`, `company` and `active`, so
  the *data* needed to pick a slab is not captured anywhere.
- **LWF** is `FIXED ₹20` charged every month. In most states it is half-yearly.
  `SalaryRule` has `sequence`, `computation`, `amount`, `percentage`,
  `percentage_base`, `formula`, `condition` and `quantity` — none of which
  expresses "only in June and December".

**What it touches.** New `StatutoryRate` model (jurisdiction, code, effective
from/to, rate, ceiling, periodicity) in a new `statutory` app; a new
`SalaryRule.computation` choice that resolves against it; a `state` field on
`core.WorkLocation`; `payroll/engine.py::evaluate_rule` gains a branch;
`build_context` exposes the resolved rate so the payslip can show it.

## N-2 · Employer contributions and CTC

**What.** Make `SalaryRule.is_employer_cost` actually mean something, and seed
the employer side of PF (12%, split EPS 8.33 / EPF 3.67), ESIC (3.25%) and
gratuity accrual.

**Why it matters.** `is_employer_cost` exists on the model
(`payroll/models.py:89`), is serialized in `payroll/api.py`, and is a checkbox in
`frontend/src/screens/SalaryConfig.jsx:313` — **and the engine never reads it.**
`compute_payslip` adds every rule's amount into `ctx["categories"][rule.category]`
regardless. So an employer PF rule categorised `DEDUCTION` would reduce the
employee's net pay. The same is true of `appears_on_payslip`: it is stored,
exposed and editable, and no code consumes it. Until this is fixed, the system
cannot answer "what does this employee cost us", which is the number finance
actually asks for.

**What it touches.** `payroll/engine.py::compute_payslip` (skip employer-cost
rules from `categories` accumulation, accumulate them into a parallel
`employer_categories`); `Payslip` gains a derived `ctc` alongside `gross`/`net`;
`payroll/pdf.py` gains an employer-contribution block; `payroll/api.py`
`PayslipDetailSerializer` exposes it.

## N-3 · Proration for mid-period joiners, leavers and structure changes

**What.** Intersect the payroll period with the contract's own date range and
prorate every wage-derived rule accordingly.

**Why it matters.** `gather_period_facts` computes `expected_days` across the
*whole* period from the working schedule and never looks at
`contract.start_date` / `contract.end_date`. `evaluate_rule` for `PERCENTAGE`
returns `base * pct / 100` where `base` is the full `contract.wage`. So an
employee who joins on 20 February is paid a full February BASIC. Nobody would
sign that payroll. This is the single most common real-world payroll case that
the current engine gets confidently wrong.

**What it touches.** `payroll/engine.py::gather_period_facts` (clamp the day
window to the contract), `build_context` (expose a `proration_factor`),
`evaluate_rule` (apply it to `PERCENTAGE`, and expose it to `FORMULA`);
`employees/models.py::Employee.contract_for_period` already returns the right
contract, so the resolution half is done.

## N-4 · Off-cycle, bonus and correction runs

**What.** A `run_type` on `Payrun` (`REGULAR` / `OFF_CYCLE` / `ARREAR` /
`SETTLEMENT`) and a payslip identity that permits more than one slip per period.

**Why it matters.** This is currently blocked by a database constraint, not
merely unbuilt. `Payslip` carries
`UniqueConstraint(fields=["employee", "period_start", "period_end"])` — the
duplicate-payslip guard for graded rule #5 — which structurally forbids a second
February payslip for the same person. `create_payrun_payslips` skips such an
employee and files a `DUPLICATE` warning. That constraint is correct for regular
runs and wrong for every other kind, so lifting it means replacing "one slip per
period" with "one *regular* slip per period" and keeping the duplicate warning
scoped to regular runs.

A related limitation: `compute_payrun` unconditionally assigns
`payslip.salary_structure = payrun.salary_structure` to every slip in the run, so
interns and full-timers cannot share a payrun even though their contracts each
name their own structure.

**What it touches.** `payroll/models.py` (`Payrun.run_type`, revised
`Payslip` constraint), `payroll/engine.py::create_payrun_payslips` and
`compute_payrun` (honour `contract.salary_structure` when the run does not pin
one), `frontend/src/screens/Payruns.jsx` wizard step 1.

## N-5 · An immutable audit log, and closing the recompute hole

**What.** An append-only `AuditEntry` (actor, model, object id, field, old value,
new value, timestamp, reason) written on every write to `Contract`, `SalaryRule`,
`Payslip`, `PayslipLine` and `Payrun` state transitions — plus server-side
enforcement of the payrun state machine.

**Why it matters.** Three concrete gaps:

1. **`TimeStampedModel` gives `created_at` / `updated_at` and nothing else.**
   The only who-changed-what in the entire system is
   `Attendance.is_manually_edited` + `edited_by`, set in
   `attendance/api.py::perform_update` — one boolean and the *last* editor, not a
   history. `PayslipWarning` records payroll *problems* and is deliberately
   regenerated on every compute (`compute_payslip` starts with
   `payslip.warnings.all().delete()`), so it is explicitly not a log.
2. **A contract's `wage` can be edited in place with no trace.** Because
   `contract_for_period` resolves by date range, editing a wage silently changes
   what a *past* period would recompute to. There is no way to answer "what wage
   was in force when we paid December".
3. **The state machine is enforced in the model and not on the wire.**
   `Payrun.can_compute` returns true only for `DRAFT`/`COMPUTED` and is
   serialized to the front end — but `PayrunViewSet.compute` calls
   `engine.compute_payrun` without checking it, and the engine guards only
   `is_locked` (`state == PAID`). A `VALIDATED` payrun can therefore be
   recomputed through the API, silently rewriting its lines and dropping it back
   to `COMPUTED`. The UI hides the button; the API does not refuse the call —
   the same failure mode PRD-3.1 names for permissions, applied to state.

Cheap and worth doing alongside: **every `admin.py` in the project is an empty
stub.** `/admin/` is mounted in `config/urls.py:51` and zero models are
registered, so the inspect-and-repair fallback that D-001 chose Django partly
*for* does not currently exist.

**What it touches.** New `core.AuditEntry` + a mixin or `pre_save` signal;
`payroll/api.py` `compute`/`validate`/`mark_paid` actions gain guard clauses;
`Payrun` gains `validated_by` / `paid_by` FKs (it has `created_by` and the
timestamps `validated_at` / `paid_at`, but no record of *who* signed off);
`*/admin.py` registrations.

## N-6 · Attendance regularisation, and the stuck-session trap

**What.** An employee-raised regularisation request for a missed or wrong punch,
approved by the manager, that writes a corrected `Attendance` row with the reason
attached.

**Why it matters.** Two failures compound today:

- `gather_period_facts` filters attendance with `check_out__isnull=False`. A
  forgotten punch-out means that day **silently disappears from `worked_days`**,
  with no warning raised and no employee-facing route to fix it.
  `AttendanceViewSet.SELF_SERVICE_ACTIONS` is `{status, check_in, check_out,
  create}` — an employee may *add* a record but not edit one, so closing a stale
  session needs an HR update (flagged `is_manually_edited`).
- `Attendance` carries
  `UniqueConstraint(fields=["employee"], condition=Q(check_out__isnull=True))`.
  That stale session then blocks the employee's *next* check-in entirely:
  `check_in_employee` finds it and returns it with `created=False`. A missed
  punch-out on Friday leaves the widget wrong all of Monday until HR intervenes.

Two smaller correctness gaps in the same area: `worked_days` counts distinct
dates of any non-`ABSENT` session, so a `HALF_DAY` counts as a full day; and
`Attendance.overtime_hours` is a plain editable field with default 0 that nothing
derives — the seeded `OT` rule multiplies it by the hourly rate, so overtime pay
depends on somebody typing the number in.

**What it touches.** New `AttendanceRegularisation` model in `attendance/`;
`attendance/api.py` (a self-service action alongside `check_in`/`check_out`);
`payroll/engine.py::gather_period_facts` (half-day weighting, and surface
open sessions as a payslip warning rather than dropping the day); a derived
`overtime_hours` from `worked_hours` against the schedule.

## N-7 · Move PDF rendering and payslip email off the request thread

**What.** A job queue (Celery or RQ + Redis) for payslip PDF generation and
bulk email, with per-payslip delivery status and retry.

**Why it matters.** `PayrunViewSet.send_payslips` calls
`payroll/mail.py::send_payrun_payslips` **inline in the HTTP request**. That
function loops every payslip in the run, calls `build_payslip_pdf` (ReportLab,
synchronous) and `message.send(fail_silently=False)` for each, and wraps the
whole thing in `except Exception: skipped += 1`. So a run of 22 is fine; a run of
500 is a gateway timeout, and a failure is invisible beyond a count — nobody can
say *which* employee did not get their payslip, or resend to just them.

The PDF path has a second problem: `PayslipViewSet.pdf` renders synchronously
from live data and never persists the result. "Resend March's payslip" re-renders
from the current rules, so if a rule was edited since, the reissued PDF will not
match the one the employee received. A payslip PDF should be generated once,
stored, hashed and served — that is what makes it a document rather than a view.

**What it touches.** `requirements.txt` (celery, redis), a `payroll/tasks.py`,
`payroll/mail.py` and `payroll/api.py` `send_payslips` become an enqueue;
new `PayslipDocument` model (file, sha256, generated_at) so reissue is a
download, not a re-render.

## N-8 · Close the remaining test gaps, and put it in CI

**What.** Tests for the payroll HTTP surface, the dashboard, PDF and email; a
front-end test runner; a GitHub Actions workflow; the script harnesses ported off
the dev database.

**Why it matters.** 155 tests across 2,233 lines is real coverage, and it is
honest about what it pins. The remaining map:

| Area | State |
|---|---|
| `payroll/tests.py` — 36 tests | Rule sequencing and later-rule visibility; reordering; inactive rules; a failing rule not aborting the run; derived Gross/Net; recompute idempotence incl. payrun-level warning survival; formula sandbox rejections; all five warnings; the state machine; wizard step 1 creating nothing |
| `accounts/tests.py` — 50 tests | The full role matrix at model *and* HTTP level (`APITestCase`): every cell of PRD §3.2, self-role-elevation refused, payroll read/write splits, login and token issue |
| `attendance/tests.py` — 30 tests | Derived worked/elapsed hours, the one-open-session constraint, the widget endpoints, ownership narrowing, HR correction attribution |
| `employees/tests.py` — 21 tests | Contract resolution by period incl. `EXPIRED` contracts and `DRAFT`/`CANCELLED` exclusion; overlap rejection; derived weekly hours incl. split shifts, break removal, holiday exclusion; code generation; manager-cycle guard |
| `timeoff/tests.py` — 18 tests | The allocation gate (none / unapproved / wrong dates / insufficient balance / ungated type); balance derivation and restore-on-cancel; duration across holidays and half-days |
| `core` · `dashboard` | **Untouched 3-line Django stubs.** Zero tests — and the dashboard is the hardest-scored screen |
| Payroll over HTTP | **Zero.** The `compute` / `validate` / `mark_paid` / `send_payslips` actions and the two-step wizard are exercised only by `smoke_api.py`, not by a `TestCase` |
| `payroll/pdf.py`, `payroll/mail.py`, `seed.py` | **Zero** |
| Front end — 5,565 lines across 25 files | **No test runner at all.** `package.json` scripts are `dev`/`build`/`lint`/`preview`; the only quality gate is oxlint |
| CI | **None.** No `.github/` directory; nothing runs on push |
| Load | **None.** PRD-7.2 (a 20-employee run under 5s) and PRD-7.3 (dashboard under 2s) are unmeasured |

`accounts/permissions.py::IsOwnerOrHR` is defined and **never referenced** —
ownership is enforced by `get_queryset` filtering instead, which is a weaker
guarantee (it narrows lists; it does not gate object access) and is exactly how
the contract leak in N-9 got through.

The script harnesses need converting, not deleting. `verify_rules.py` and
`smoke_api.py` both call `django.setup()` against the **development database**;
the README documents that `smoke_api.py` "leaves an `April 2026 (smoke)` payrun
behind" and tells you to re-seed before demoing. `probe_forms.py` posts against a
live server on `127.0.0.1:8000`. They are excellent as demo-day proof and unusable
as CI: a test that mutates the demo database cannot run on every push.

**What it touches.** `payroll/tests.py` gains an `APITestCase` class for the
action bar and wizard; new `dashboard/tests.py` asserting each filter re-drives
each KPI; `vitest` + `@testing-library/react` in `frontend/package.json`; a
`.github/workflows/ci.yml` running `manage.py test`, `npm run lint` and the
front-end suite; `verify_rules.py`'s scenarios ported into fixtures so the dev
database stops being a test fixture.

## N-9 · Authentication and authorization hardening

**What.** Close the contract read leak, then token expiry and rotation, a real
password policy, login throttling, forced password change, and secure-by-default
settings.

**Why it matters — the leak first.** PRD §3.2 gives an Employee `R (own)` on
contracts. `ContractViewSet` in `employees/api.py` sets a flat
`queryset = Contract.objects.select_related(...)` with **no `get_queryset`
ownership narrowing** and `filterset_fields` that do not even include the
employee's own company. The result is that any authenticated employee can list
every contract in the system and read colleagues' wages — the write half of the
cell holds (`CanManageHR` refuses the PATCH), so this is a read leak, and it is
now pinned by
`accounts/tests.py::test_an_employee_can_read_every_contract_including_wages`.
Salary is the single most sensitive field in an HR system; this is the one item
on this roadmap that should ship before anything else. The fix is the same
`get_queryset` narrowing `EmployeeViewSet`, `AttendanceViewSet` and
`TimeOffRequestViewSet` already do — and applying `IsOwnerOrHR`, which exists and
is unused, at the object level so detail routes are gated and not merely lists.

**And the auth layer.** In `accounts/api.py` and `config/settings.py`:

- `login_view` does `Token.objects.get_or_create(user=user)` — DRF's default
  token, **one per user, never rotated, no expiry**. `logout_view` deletes it,
  which signs the user out of every device at once.
- `REST_FRAMEWORK` declares no `DEFAULT_THROTTLE_CLASSES` and `login_view` is
  `AllowAny`: password guessing is unlimited.
- `AUTH_PASSWORD_VALIDATORS` contains exactly one validator —
  `MinimumLengthValidator` at `min_length: 6`. No common-password check, no
  numeric check, no similarity check.
- `UserSerializer.create` defaults a new user's password to `"demo1234"` when the
  admin does not supply one, and nothing forces a change on first login.
- `SECRET_KEY` defaults to `"dev-only-insecure-key-change-in-production"` and
  `DEBUG` defaults to `True`. Both are env-overridable, but the *default* is
  insecure, and there are no `SECURE_*` / HSTS / secure-cookie settings.

No MFA and no password reset — both were called optional by the spec and are
correctly absent, but a payroll system holding bank accounts and PAN numbers
needs at least TOTP for the Payroll Manager and Admin roles.

**What it touches.** `employees/api.py::ContractViewSet.get_queryset` and
`accounts/permissions.py::IsOwnerOrHR` for the leak; `config/settings.py`
(throttle rates, the full validator set, `SECURE_*`); `accounts/api.py` (token
TTL and rotation, or a swap to JWT with refresh); `accounts/models.py`
(`password_changed_at`, `mfa_secret`).

---

# NEXT — 3–9 months

The theme is that several capabilities are *present as fields* and absent as
behaviour. Turning them on is mostly plumbing, and the plumbing is substantial.

## X-1 · Multi-company as a real boundary

**What.** Make `company` a tenancy boundary the server enforces, not a filter the
client passes.

**Why it matters.** D-003 deliberately chose one seeded company with the field
present and filterable, which was the right 24-hour call — but the shape of the
gap should be stated precisely:

- The FK exists on `Company`-owning masters: `Department`, `JobPosition`,
  `WorkLocation`, `Holiday`, `WorkingSchedule`, `Employee`, `SalaryStructure`,
  `Payrun`. It does **not** exist on `Contract`, `Attendance`, `TimeOffType`,
  `Allocation`, `TimeOffRequest` or `Payslip` — those inherit company
  transitively through `employee`, so filtering them is a join, and `TimeOffType`
  is effectively global across all companies.
- **`accounts.User` has no company field at all** — only `employee` and `roles`.
  There is therefore no server-side tenant scope: every `get_queryset` in
  `employees/api.py`, `timeoff/api.py`, `attendance/api.py` and `payroll/api.py`
  filters by *employee ownership* or by an explicit `?company=` query param, and
  never by the requesting user's company. An HR Manager at company A can list
  company B's employees by omitting the filter.
- The front end assumes one company everywhere: `useDefaultCompany()` in
  `frontend/src/components/ui.jsx` fetches `/api/companies/` and injects
  `rows(payload)[0]?.id` — *the first company* — into every create payload;
  `Employees.jsx:111` does the same; `Payruns.jsx:86` falls back to a hardcoded
  `company: 1`.
- `Company.timezone` and `WorkingSchedule.timezone` are both stored and **never
  read**. `settings.TIME_ZONE` is a single global `"Asia/Kolkata"`, and
  `Attendance.date` uses `timezone.localtime()`, so a second company in another
  zone would have its check-ins bucketed into IST days.

**What it touches.** `accounts.User.company` (or a `UserCompanyAccess` M2M for
group HR); a `CompanyScopedQuerySet` mixin applied to every viewset's
`get_queryset`; `company` FKs added to `TimeOffType` and `Payslip`; a company
switcher in `Shell.jsx` replacing `useDefaultCompany`; timezone resolution moved
from `settings.TIME_ZONE` to the employee's company.

## X-2 · Multi-currency

**What.** Payroll in a currency other than INR, with rate capture at period close
and reporting in a group currency.

**Why it matters.** `Company.currency` exists with `default="INR"` and, like
`timezone`, **nothing reads it**. `payroll/pdf.py` hardcodes `RUPEE = "₹"`;
`payroll/mail.py` writes `INR {payslip.gross:,.2f}` into the body;
`config/settings.py` defines module-level `CURRENCY_SYMBOL` / `CURRENCY_CODE`
constants. The dashboard's `_net_total` sums `PayslipLine.amount` across whatever
payslips the filter returns, with no currency dimension — the moment a second
currency exists, that number is meaningless. Multi-currency is therefore not a
formatting change; it is a rate table, a per-payslip currency stamp, and a
decision about what a group-level KPI means.

**What it touches.** `Payslip.currency` + `fx_rate` stamped at compute time; an
`ExchangeRate` model; `payroll/pdf.py` and `payroll/mail.py` take formatting from
the payslip, not from settings; `dashboard/api.py` aggregates get a currency
group-by or a conversion step.

## X-3 · Approval chains, delegation and escalation

**What.** Configurable multi-step approval with delegation when an approver is
away and time-based escalation.

**Why it matters.** Leave approval today is one step and one field.
`TimeOffRequest` has a single `approver` FK and a single `approved_at`;
`TimeOffRequest.approve()` sets state, approver and timestamp and is terminal.
More pointedly:

- `TimeOffType.approval` offers `NONE` / `MANAGER` / `OFFICER` — and **nothing
  reads it**. `TimeOffRequestViewSet.approve` checks only
  `request.user.can_approve_leave`, which `accounts/models.py` defines as *any*
  HR role. So a type configured "By Manager" can be approved by any HR user, and
  a type configured "No Validation" still requires an approval click.
- `Employee.manager` exists and is used for the `my_team` filter, but approval
  never consults it — an HR Manager from another department can approve.
- `Allocation.approve` / `refuse` in `timeoff/api.py` are bare state flips that
  record nothing: `Allocation` has no `approver` field at all, unlike
  `TimeOffRequest`. The record of who granted 20 days of leave does not exist.
- `Contract` has no approval step, and payroll's approvals are timestamps without
  actors (see N-5).

**What it touches.** New `ApprovalChain` / `ApprovalStep` / `ApprovalAction`
models in a shared app; `TimeOffRequest.approve` becomes a step transition;
`TimeOffType.approval` finally drives routing; `Delegation` (user, delegate,
from, to) consulted by the permission check; escalation needs the job queue from
N-7.

## X-4 · Statutory filings and payment outputs

**What.** PF ECR text file, ESI return, PT challan, Form 24Q quarterly, Form 16
annual, and a NEFT/NACH bank transfer file.

**Why it matters.** `payroll/pdf.py` produces exactly one artifact — the
individual payslip — and it is the only document the system emits. Everything a
payroll team actually *files* is absent, and each filing needs data the schema
does not yet capture: ECR needs UAN and PF member id (neither exists on
`Employee`, which has `bank_account_number`, `bank_ifsc` and `pan_number` only);
Form 24Q needs TDS per employee per quarter (see X-5); the bank file needs a
company account and a value date. This is the item that most separates "computes
a payslip" from "runs payroll", and it is deliberately sequenced after N-1
because a filing built on unversioned rates is a filing you cannot re-derive.

**What it touches.** `Employee` gains `uan`, `pf_member_id`, `esic_number`;
new `payroll/filings/` module with one generator per format;
`PayrunViewSet` gains export actions; the generated files need the
`PayslipDocument` storage from N-7.

## X-5 · Income tax, declarations and TDS

**What.** Annual tax projection with old/new regime selection, an employee
investment-declaration portal, proof approval, and monthly TDS as a salary rule.

**Why it matters.** There is no TDS rule anywhere — not in the seeded `REGULAR`
structure, not in `INTERN`. `Payslip.net` is therefore gross minus statutory
deductions only, which for anyone above the threshold is not their take-home
pay. Tax is also the one calculation that is genuinely *annual* and projected
back onto months, which the current per-period engine has no concept of:
`compute_payslip` builds its context from one period's facts and knows nothing
about the year to date.

**What it touches.** `build_context` gains year-to-date aggregates (a real change
— it currently derives everything from a single period); new `TaxDeclaration`,
`InvestmentProof`, `TaxRegime` models; a `TDS` rule using the statutory layer
from N-1; a self-service declaration screen.

## X-6 · Shift rostering, and schedules that survive midnight

**What.** Date-specific shift assignment, rotation patterns, swap requests,
coverage alerts — and a `ScheduleLine` that can represent a night shift.

**Why it matters.** `WorkingSchedule` + `ScheduleLine` describe one repeating
week: `day_of_week` 0–6, `start_time`, `end_time`, `break_minutes`. There is no
date dimension, so "Ravi works nights this fortnight" is unrepresentable.

More concretely, `ScheduleLine` carries
`CheckConstraint(condition=Q(end_time__gt=F("start_time")))`, which forbids a
line that crosses midnight. The consequence is visible in the seed data: the
schedule named **"Night Shift" is seeded as 22:00–23:59 with a 30-minute break**
(`seed.py:117`), because 22:00–06:00 cannot be stored. Its derived
`hours_per_week` is **7.40 hours** — the derivation is correct, the data it
derives from cannot express the thing it is named after. Any product that claims
shift support has to fix this at the model layer, not the UI.

**What it touches.** `ScheduleLine` gains `crosses_midnight` (or an explicit
`end_day_offset`) and the check constraint is rewritten; new `ShiftAssignment`
(employee, date, schedule) consulted by
`WorkingSchedule.expected_working_days` and by
`payroll/engine.py::gather_period_facts`; `Attendance.date` bucketing must follow
the shift, not the calendar day.

## X-7 · Full and final settlement, and leave encashment

**What.** An exit workflow producing a settlement payslip: final salary, leave
encashment, notice pay or recovery, gratuity, and asset/clearance holds.

**Why it matters.** `Contract.state` has `EXPIRED` and `CANCELLED`, and nothing
triggers on either. `Allocation` derives `taken` and `remaining` correctly but
has no encashment path — a leaver's unused balance simply stops being queried.
Settlement is also structurally blocked by the same `Payslip` uniqueness
constraint discussed in N-4, so this item depends on that one.

**What it touches.** New `Separation` model (employee, last working day, reason,
notice period); a `SETTLEMENT` run type from N-4; encashment as a salary rule
reading `Allocation.remaining`; a gratuity accrual rule using `date_of_joining`.

## X-8 · PostgreSQL, and what it buys back

**What.** Run production on PostgreSQL, with connection pooling and the
constraints SQLite cannot express.

**Why it matters.** D-011 chose SQLite deliberately and correctly — no install
friction, the demo runs on whichever laptop is in the room — and the code already
routes through `dj_database_url`, so the switch is an environment variable. Two
things need doing beyond flipping it:

- **The overlap constraint that was traded away.** D-011 notes the gist `EXCLUDE`
  constraint for overlapping `RUNNING` contracts cannot exist on SQLite, and that
  `Contract.clean()` carries it instead. That is true and tested
  (`ContractOverlapTests`), but `clean()` only runs on save paths that call it —
  `Contract.objects.bulk_create` and `.update()` bypass it entirely.
- **The migration was never written.** `config/settings.py` computes
  `USING_POSTGRES` and its docstring says the "Postgres-only constraints in
  `employees/migrations` activate automatically" — but `USING_POSTGRES` is
  referenced nowhere else in the codebase, and `employees/migrations/` contains
  only `0001_initial` and `0002_initial`, neither of which mentions
  `BtreeGistExtension` or an `EXCLUDE` constraint. The hook is named but not
  built.

**What it touches.** A new guarded migration in `employees/migrations/` adding
`BtreeGistExtension` and the daterange `EXCLUDE`; `USING_POSTGRES` gains its
first real consumer; `conn_max_age` is already set to 600 in settings, so pooling
is a deployment concern (pgbouncer) rather than a code one.

---

# LATER — 9–18 months

## L-1 · Effective-dated records throughout

`Contract` is period-scoped and resolved by date — `contract_for_period` is
genuinely the right shape. Nothing else is. Departments, job positions, salary
structures, rules and employee master data are all "current value only", so the
system can say what an employee's department *is* and not what it was in March.
Making every master record effective-dated turns "recompute March" from a wrong
answer into a correct one. It touches essentially every model and serializer,
which is why it sits here and not in Now.

## L-2 · Salary revision workflow with retroactive effect

An increment today means editing `Contract.wage` in place, or creating a new
contract and leaning on the overlap guard. Neither records who approved what, and
neither can push the difference into a closed period. Needs N-5 (audit), N-4
(arrear runs) and L-1 (effective dating) first.

## L-3 · Employee self-service as a product, not a filtered view

Today an employee gets a narrowed HR app: `get_queryset` filters to
`employee_id`, and `AttendanceViewSet.SELF_SERVICE_ACTIONS` opens
`status`/`check_in`/`check_out`/`create`. Notably `TimeOffRequestViewSet` uses
`CanManageHR` for writes, so **an employee cannot create their own leave request
through the API** — only read it, as
`accounts/tests.py::test_an_employee_cannot_create_their_own_time_off_request`
now pins. A real self-service surface (apply, view
balance, download payslips, raise a regularisation, update personal details for
approval) is a distinct app with its own permission model, and it is what makes
the system usable by the other 95% of the headcount.

## L-4 · Device and location-aware attendance

Biometric/RFID ingestion, geofenced mobile punches, IP allowlisting.
`AttendanceViewSet.check_in` accepts a bare POST with no body — no coordinates,
no device id, no IP — and `Attendance` has no field to hold any of it. A
data-capture change first, a policy engine second (radius rules per
`WorkLocation`, which also gains the `state` field from N-1).

## L-5 · General ledger posting

Payroll's output stops at the payslip; finance needs journal entries — salary
expense by department, statutory liabilities by head, net pay as a bank clearing
entry. The department dimension exists and `dashboard/api.py` already aggregates
salary cost by it, so the data is there. What is missing is a chart-of-accounts
mapping per salary rule and a posting run on payrun validation.

## L-6 · A reporting layer separate from the operational database

`dashboard/api.py` computes every KPI and panel live and uncached against the
transactional tables — right for a demo and one company, wrong at 10,000
employees with three years of history. The endgame is a nightly-materialised
reporting schema with the dashboard reading from it, plus a self-serve report
builder so HR stops asking engineering for CSVs.

---

# Deliberately out of scope for 24 hours

Each of these was a conscious trade, and each was the right call for the time
budget. Listing them is not an apology — a roadmap that cannot name its own
compromises has not understood them.

**Multi-company (D-003).** The `company` FK is on the masters and the dashboard
filter works, so the *shape* of multi-tenancy is visible at zero runtime cost.
Enforcing it means a tenant scope on `accounts.User` and a scoping mixin on every
viewset — hours of plumbing that demonstrate nothing new when the demo has one
company. X-1 states the bill exactly.

**PostgreSQL (D-011).** Neither Postgres nor Docker was installed on the build
machine. Zero install friction across three teammates and an unknown demo laptop
beat engine parity for 24 hours. The cost was one database-level constraint,
enforced instead in `Contract.clean()` and covered by five tests.

**Background jobs.** Celery and Redis means a broker, a worker and a second thing
that can break at 3am on demo night. For 22 employees, inline PDF and email
complete in well under a second. N-7 says where that stops being true.

**A real audit trail.** `TimeStampedModel` plus `PayslipWarning` plus
`Attendance.is_manually_edited` covers what a demo can show. A field-level log is
cross-cutting — every model, every write path — and started at hour 18 it would
have destabilised a working payroll engine for something nobody clicks in a
five-minute demo.

**Statutory depth.** Wage ceilings, state PT slabs and LWF periodicity are
invisible in a demo: a judge sees "PF ₹6,600" and "PF ₹1,800" as equally
plausible. The graded rules asked for *sequenced rules that genuinely drive the
payslip*, and that is where the hours went. The seeded ESIC formula does carry
its real ₹21,000 ceiling — the cheapest available signal that the rule set is not
decorative.

**Approval chains and regularisation.** Both explicitly out of scope in PRD §9,
both pure workflow — high build cost, no new integration to show. One approval
step exercises the same state machine a chain would.

**Income tax.** Days of work, invisible on a payslip except as one more deduction
line, and dependent on annual context the engine does not carry.

**Frontend tests and CI.** The backend ended up with a real Django suite — 155
tests, including HTTP-level coverage of the whole role matrix. The front end got
none, and nothing runs automatically. Against a fixed clock the early strategy
was three executable harnesses — `verify_rules.py`, `smoke_api.py`,
`probe_forms.py` — that prove the graded rules and the HTTP layer in seconds and
print PASS/FAIL; `probe_forms.py` posts the exact payload each UI form builds and
caught four create bugs the other two could not see. Better spent than a Vitest
harness on the night, and not sustainable past this weekend — which is N-8.

**What was *not* deferred, and deliberately so.** The three D-002 integrations —
attendance driving worked days, unpaid leave driving LOP, overtime driving an
earnings rule — were not required by the problem statement. They were built
because the data already existed and they are the difference between a set of
CRUD modules and a payroll system. That trade is the inverse of every entry
above: cheap to build, expensive to fake.

---

# What would break first at scale

Ordered by how soon it bites, not by severity.

1. **Payslip list pages, at roughly 50 rows.** `PayslipListSerializer` exposes
   `basic`, `gross` and `net` as read-only fields sourced from model properties,
   and each property runs its own `lines.filter(category=...).aggregate()`.
   Worse, `gross` and `net` fall back to *two further property calls* each when
   the category row is absent. At `PAGE_SIZE = 50` that is well over 150 aggregate
   queries for one page. `PayrunSerializer.total_net` / `total_gross` are worse
   still — they iterate `self.payslips.all()` in Python and hit those same
   properties per slip. Fix: annotate the queryset with conditional sums.

2. **Two payrolls computed at the same time.** `Payslip.save()` generates its
   number by scanning `filter(number__startswith=prefix).order_by("-number").first()`
   and incrementing — a read-then-write with no lock. `Employee.save()` and
   `Contract.save()` do the same for `EMP/` and `CON/` references. Two concurrent
   runs produce the same number and one insert dies on the unique constraint.
   Fix: a database sequence per prefix, or `select_for_update` on a counter row.

3. **Any payrun large enough to hold a write lock.** `compute_payrun` is
   `@transaction.atomic` around the entire run, and `compute_payslip` is
   atomic inside it. On SQLite that is a database-wide write lock for the
   duration of the run; every other writer blocks. Fix: per-payslip transactions
   with a run-level status, which also makes partial recompute possible.

4. **`send_payslips` on a real headcount.** Inline ReportLab rendering plus
   `message.send()` per employee inside the request (N-7). At a few hundred
   employees this is a gateway timeout, and the bare `except Exception` means the
   failure surfaces only as a count.

5. **The dashboard, as history accumulates.** `dashboard_view` computes every KPI
   and panel live and uncached; `_net_total` and `_gross_total` filter
   `PayslipLine` by `payslip__in=<queryset>` — a subquery over an unbounded
   payslip set. Three years of history turns PRD-7.3's sub-2-second target into a
   table scan.

6. **`gather_period_facts`, per employee, per compute.** It pulls every
   attendance session for the period into Python to count distinct dates and sum
   overtime, and issues its own `Holiday` query per employee. Both are
   aggregatable in SQL; both are per-payslip today.

7. **Payslip numbering past 9,999 slips in a month.** `PAY/YYYY/MM/NNNN` is
   zero-padded to four digits and the next number is found by *string* ordering,
   so the ten-thousandth slip in a period sorts wrong and collides.

None of these is a design error — every one is the correct shape for a
22-employee demo, and every one has a known, bounded fix. That is the honest
summary of the whole system: the model is right, the constraints are right, the
engine is right, and the operational envelope around them is sized for one room
and one day.
