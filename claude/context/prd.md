# PRD — PeoplePay360: HR & Payroll

**Version** 1.0 · **Author** Michael (session 01) · **Date** 2026-09-05
**Status** Approved for build

> **How to use this document.** §5 is the contract — every requirement there has
> an acceptance criterion, and "done" means the criterion passes. §4 is the
> business logic that makes this project non-trivial and is where the marks are.
> §9 is the scope boundary; if it is in "Out", do not build it.

---

## 1. Overview

### 1.1 What we are building

PeoplePay360 is an integrated HR and Payroll operations platform. It manages the
employee lifecycle from master data through time tracking to payroll calculation
and reporting, as a **single connected flow** rather than a set of independent
CRUD modules.

### 1.2 The problem

Basic HR tools keep employee details, attendance, leave and salary as separate
records that do not inform each other. The consequence is that payroll becomes a
manual reconciliation exercise: someone exports attendance, cross-references
leave, checks which contract was in force, and types numbers into a spreadsheet.

PeoplePay360 makes those relationships first-class, so that computing payroll is
a button rather than a project.

### 1.3 The core insight

The **Employee record is the hub**. Everything else either provides payroll
context (Contract, Working Schedule), captures day-to-day activity (Attendance,
Time Off), or defines computation (Salary Structure, Salary Rules). The Payrun is
where all of it converges.

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

### 1.4 Context and constraints

| | |
|---|---|
| **Event** | Odoo Hackathon 2026, 24 hours |
| **Team** | Three developers, relaying across three Claude sessions |
| **Stack** | React · Django + DRF · PostgreSQL *(D-001)* |
| **Locale** | India — ₹, PF / ESIC / PT / LWF *(D-003)* |
| **Companies** | Single seeded company; field present and filterable *(D-003)* |

---

## 2. Goals, non-goals, success criteria

### 2.1 Goals

- **G1** — A working end-to-end flow from employee master data to a paid,
  emailed payslip
- **G2** — Business logic that genuinely computes, with no hardcoded values
  anywhere in the payroll path
- **G3** — Role-based access enforced at the API, not merely hidden in the UI
- **G4** — A dashboard that aggregates live across at least five models and
  visibly responds to its filters
- **G5** — Seeded data rich enough to demo three months of payroll history

### 2.2 Non-goals

- Production-grade security hardening
- Multi-country or multi-currency payroll
- Mobile applications
- Real email delivery infrastructure (a console/SMTP-to-file backend is
  acceptable for the demo)
- Statutory filings and government report formats

### 2.3 Success criteria

The build is successful when all of the following are demonstrable **live**:

1. An employee with two historical contracts is paid using the one valid for the
   selected period — provably, not coincidentally
2. A leave request against an allocation-required type is **blocked** with no
   allocation, and **succeeds** once one is approved, with the balance visibly
   decreasing
3. A payslip's every line traces to a salary rule, in sequence, with Gross and Net
   derived rather than stored
4. A payrun surfaces at least two distinct warnings before validation
5. Changing the dashboard Period filter measurably changes every card and chart
6. Both demo scenarios in `claude/deliverables/demo-script.md` run start to finish
   without intervention

---

## 3. Users and permissions

### 3.1 Personas

| Persona | What they do here |
|---|---|
| **Employee** | Checks in and out, views their own attendance, requests leave, downloads payslips |
| **HR Manager** | Maintains employee, contract, schedule and attendance data; approves leave |
| **HR Payroll User** | Everything HR Manager does, plus runs payroll — but cannot change how salary is calculated |
| **HR Payroll Manager** | Owns payroll end to end, including salary structures and rules |
| **Admin** | Manages user accounts and role assignment; full system access |

### 3.2 Permission matrix

| Resource | Employee | HR Manager | Payroll User | Payroll Manager | Admin |
|---|---|---|---|---|---|
| Own employee record | R | RW | RW | RW | RW |
| All employee records | — | CRUD | CRUD | CRUD | CRUD |
| Contracts | R (own) | CRUD | CRUD | CRUD | CRUD |
| Working schedules | R | CRUD | CRUD | CRUD | CRUD |
| Attendance | CR (own) | CRUD | CRUD | CRUD | CRUD |
| Time off requests | CR (own) | CRUD + approve | CRUD + approve | CRUD + approve | CRUD |
| Allocations | R (own) | CRUD | CRUD | CRUD | CRUD |
| Time off types | — | CRUD | CRUD | CRUD | CRUD |
| Payruns | — | — | CRU | CRUD | CRUD |
| Payslips | R (own) | — | CRU | CRUD | CRUD |
| Salary structures | — | — | **R** | CRUD | CRUD |
| Salary rules | — | — | **R** | CRUD | CRUD |
| Dashboard | — | R | R | R | R |
| User management | — | — | — | — | CRUD |

**PRD-3.1** Permissions are enforced **server-side**. Hiding a button is not
enforcement.
*Acceptance:* an Employee-role token calling `GET /api/payruns/` receives 403.

**PRD-3.2** A user cannot modify their own roles.
*Acceptance:* a non-admin `PATCH` on their own user's `roles` field returns 403.

**PRD-3.3** User accounts are separate entities from Employee records, linked
one-to-one.
*Acceptance:* an Employee can exist with no user account; a user account requires
an employee link.

---

## 4. Business rules — the heart of the build

**This section is the product.** Everything in §5 is scaffolding around it.

### 4.1 Contract resolution *(graded rule #1)*

**PRD-4.1.1** An employee may have many contracts. Exactly one may be `Running`
for any given date.
*Acceptance:* attempting to save a second `Running` contract whose date range
overlaps an existing one returns a validation error naming the conflicting
contract.

**PRD-4.1.2** Payroll resolves the contract by **period**, not recency.
Resolution: the contract where `start_date <= period_end` and
(`end_date >= period_start` or `end_date IS NULL`).
*Acceptance:* an employee with a contract ending 31-Dec-2025 (₹78,000) and one
starting 01-Jan-2026 (₹85,000), payrun for Dec 2025, produces a payslip based on
₹78,000.

**PRD-4.1.3** An employee with no contract covering the period is excluded from
the payrun and raises a warning.
*Acceptance:* such an employee appears in the payrun's warning list, not in its
payslips.

### 4.2 Working schedule and expected hours *(graded rule #2)*

**PRD-4.2.1** A schedule is composed of day lines: day, start time, end time,
break duration.

**PRD-4.2.2** Weekly hours are **derived**, never stored as input.
`hours_per_week = Σ((end − start) − break)` across day lines.
*Acceptance:* adding a Saturday line of 09:00–13:00 with no break moves a
40-hour schedule to 44 hours with no other edit.

**PRD-4.2.3** `days_per_week` is derived as the count of day lines.

### 4.3 Leave allocation and consumption *(graded rule #3)*

**PRD-4.3.1** A Time Off Type carries `requires_allocation` (boolean), `unit`
(days/hours) and an approval setting.

**PRD-4.3.2** If `requires_allocation` is true, a request is rejected unless the
employee holds an **approved** allocation of that type, valid for the request
dates, with sufficient remaining balance.
*Acceptance:* the request is blocked with a message naming the missing or
insufficient allocation.

**PRD-4.3.3** Balance is derived, never stored:
`remaining = allocated − Σ(approved request durations against this allocation)`.
*Acceptance:* approving a 3-day request against a 20-day allocation shows
Allocated 20 / Taken 3 / Remaining 17 without any manual adjustment.

**PRD-4.3.4** An approved request records **which allocation** it consumed.
*Acceptance:* the request form displays the specific allocation by name.

**PRD-4.3.5** Cancelling or refusing a previously approved request restores the
balance.

**PRD-4.3.6** Types with `requires_allocation` false accept requests with no
allocation and no balance check.

### 4.4 Salary rule computation *(graded rule #4)*

**This is the highest-risk component. Nothing downstream demos without it.**

**PRD-4.4.1** A Salary Structure is an ordered collection of Salary Rules.

**PRD-4.4.2** A rule has: name, code, category
(`BASIC` / `ALLOWANCE` / `GROSS` / `DEDUCTION` / `NET`), sequence, and a
computation method.

**PRD-4.4.3** Three computation methods are supported:

| Method | Behaviour |
|---|---|
| **Fixed amount** | A constant |
| **Percentage of wage** | `contract.wage × percent / 100` |
| **Formula** | A safely-evaluated expression |

**PRD-4.4.4** Rules execute in ascending `sequence`. Each rule's result is
available to every later rule.
*Acceptance:* a rule at sequence 60 computing `categories['BASIC'] +
categories['ALLOWANCE']` yields the correct Gross given rules at sequences 1–50.

**PRD-4.4.5** The formula evaluation context exposes at minimum:
`contract` (wage, schedule), `employee`, `payslip` (period, worked days, LOP
days), `categories` (running totals by category), `rules` (results by rule code).

**PRD-4.4.6** Formula evaluation is sandboxed — no imports, no attribute access
to dunder members, no file or network access.
*Acceptance:* a rule containing `__import__('os')` fails safely with a rule-level
error rather than executing.

**PRD-4.4.7** A rule that raises is recorded as a payslip-level error and does
**not** abort the whole payrun.

**PRD-4.4.8** Every payslip line persists: rule, code, category, sequence,
computed amount. The payslip's Gross and Net are read from lines, not stored
independently.

### 4.5 Payroll validation warnings *(graded rule #5)*

**PRD-4.5.1** Warnings are computed at Compute time and displayed **before**
Validate is available.

**PRD-4.5.2** The minimum warning set:

| Warning | Condition |
|---|---|
| `A/C missing` | Employee has no bank account on file |
| `Duplicate payslip` | Another payslip exists for this employee and period |
| `No contract` | No contract covers the payrun period |
| `Negative net` | Computed net salary is below zero |
| `No structure` | Contract has no salary structure assigned |

**PRD-4.5.3** Warnings are visible at both payrun level (aggregate count) and
payslip level (badge).
*Acceptance:* a payrun with two flagged employees shows "2 warnings" and each
affected payslip row carries its own badge.

**PRD-4.5.4** Warnings do not block Validate — they inform the operator. Only
hard errors block.

### 4.6 Integration connections *(D-002 — beyond the required spec)*

**PRD-4.6.1** Worked days on a payslip are derived from Attendance within the
period, not assumed.

**PRD-4.6.2** Approved **unpaid** leave in the period produces LOP days, exposed
to the formula context as `payslip.lop_days` so a deduction rule can consume it.

**PRD-4.6.3** Overtime hours from Attendance are exposed as
`payslip.overtime_hours` for an overtime earnings rule.
*Acceptance:* adding attendance with overtime and recomputing changes the
payslip's net.

---

## 5. Functional requirements

### 5.1 Authentication and users

- **PRD-5.1.1** Email + password login returning a token
- **PRD-5.1.2** Admin-only user management: list with role filter and search
- **PRD-5.1.3** Create/edit user requires an employee link and work email
- **PRD-5.1.4** Session persists across refresh

### 5.2 Employees

- **PRD-5.2.1** Kanban view (default) and List view, **both opening the same
  form**
- **PRD-5.2.2** Form shows identity, role, department, manager, work location,
  working schedule, company, status
- **PRD-5.2.3** Form tabs: Work Information · Private Information · HR Settings
- **PRD-5.2.4** Smart buttons with live counts for Contracts, Attendance, Time
  Off, Allocations
- **PRD-5.2.5** A smart button opens the related list **pre-filtered to this
  employee**
  *Acceptance:* clicking `Attendance 14` shows exactly 14 records, all for that
  employee

### 5.3 Contracts

- **PRD-5.3.1** List showing reference, employee, start, end, wage, status, with
  `Running` visually distinct
- **PRD-5.3.2** Form capturing employee, department, job position, dates, wage,
  working schedule, salary structure
- **PRD-5.3.3** Overlap validation per PRD-4.1.1

### 5.4 Working schedules

- **PRD-5.4.1** List showing name, calendar type, days/week, hours/week, company,
  status
- **PRD-5.4.2** Form with editable day lines and `+ Add Day`
- **PRD-5.4.3** Total weekly hours displayed and derived live as lines change

### 5.5 Attendance

- **PRD-5.5.1** Global list and per-employee filtered list
- **PRD-5.5.2** List columns: employee, check in, check out, worked hours, status
- **PRD-5.5.3** Worked hours computed from check in/out
- **PRD-5.5.4** Manual correction permitted for HR roles only, flagged as
  manually edited
- **PRD-5.5.5** Top-bar widget: red when checked out, green when checked in;
  popup shows Check In or Check Out as appropriate, with live elapsed time
  *Acceptance:* checking in turns the indicator green and the popup switches to
  Check Out with a running timer

### 5.6 Time off

- **PRD-5.6.1** Requests, Allocations and Types are reachable **only** from the
  `Time Off ▼` dropdown
- **PRD-5.6.2** Request list: employee, type, dates, duration, status
- **PRD-5.6.3** Request form with Approve / Refuse
- **PRD-5.6.4** Allocation list exposing Allocated / Taken / Remaining
- **PRD-5.6.5** Type form: name, unit, requires allocation, approval, colour,
  active

### 5.7 Payroll configuration

- **PRD-5.7.1** Structure list: name, rule count, employee count, active
- **PRD-5.7.2** Structure form listing its rules **in sequence order**
- **PRD-5.7.3** Rule list: name, code, category, structure, sequence
- **PRD-5.7.4** Rule form with computation method and a method-appropriate value
  input

### 5.8 Payrun

- **PRD-5.8.1** `NEW` opens a wizard and **creates nothing**
- **PRD-5.8.2** Step 1 captures employee type, salary structure, period.
  `Continue` advances without persisting
  *Acceptance:* completing step 1 then closing the wizard leaves zero new payruns
- **PRD-5.8.3** Step 2 lists eligible employees with checkboxes and search
- **PRD-5.8.4** `Create Payrun` persists the payrun containing **only checked
  employees**
- **PRD-5.8.5** Payrun form action bar: Compute · Validate · Mark Paid · Send
  Payslips
- **PRD-5.8.6** State machine per §6; invalid transitions rejected
- **PRD-5.8.7** Paid payruns are read-only and retained as history

### 5.9 Payslip

- **PRD-5.9.1** Accessible from the parent payrun or a dedicated list
- **PRD-5.9.2** Header: employee, structure, payrun, period, status, worked days
- **PRD-5.9.3** Salary Computation table: rule, code, category, amount, in
  sequence
- **PRD-5.9.4** `Print Payslip` generates a PDF
- **PRD-5.9.5** Bulk `Send Payslips` from the payrun emails each employee their
  own PDF

### 5.10 Dashboard

- **PRD-5.10.1** Filters: Period, Department, Employee Type, Company — all
  functional
- **PRD-5.10.2** Five KPI cards: Total Net Salary Paid (with month-over-month
  delta), Payslips Generated (paid/pending split), Avg Salary per Employee,
  Approved Time Off Days, Attendance Health
- **PRD-5.10.3** Salary Cost by Department (bar)
- **PRD-5.10.4** Monthly Net Salary Trend (line, historical)
- **PRD-5.10.5** Payslip Status & Payroll Alerts, listing live warnings
- **PRD-5.10.6** Attendance Overview, Time Off Overview, Department Overview
- **PRD-5.10.7** Every figure is computed from live records; no constants
  *Acceptance:* creating a payslip and refreshing changes the KPI values
- **PRD-5.10.8** Aggregates span at least five models: Employee, Contract,
  Payslip, Attendance, TimeOff

---

## 6. Payrun state machine

```
   DRAFT ──compute──> COMPUTED ──validate──> VALIDATED ──mark paid──> PAID
     ↑                    │                                             │
     └────recompute───────┘                                        (terminal,
                                                                   read-only)
```

| Transition | Guard | Effect |
|---|---|---|
| `→ DRAFT` | payrun created | payslip shells created for selected employees |
| `DRAFT → COMPUTED` | ≥1 employee | rules execute; lines and warnings written |
| `COMPUTED → COMPUTED` | — | **idempotent** recompute; lines replaced, never appended |
| `COMPUTED → VALIDATED` | no hard errors | payslips locked |
| `VALIDATED → PAID` | — | payment date stamped |
| `PAID → *` | **forbidden** | historical record |

**PRD-6.1** Recompute is idempotent.
*Acceptance:* computing three times yields identical payslip totals and no
duplicate lines.

---

## 7. Non-functional requirements

- **PRD-7.1** Seed data: ≥20 employees across ≥4 departments, ≥3 months of
  payroll history, ≥2 employees with multiple contracts, ≥1 with no bank account
  (to trigger a warning on cue), attendance and leave across the period
- **PRD-7.2** A payrun of 20 employees computes in under 5 seconds
- **PRD-7.3** Dashboard loads in under 2 seconds on seeded data
- **PRD-7.4** PDF generation is server-side and produces a branded, readable
  payslip
- **PRD-7.5** Email uses a console or file backend; no real delivery required
- **PRD-7.6** All monetary values use `Decimal`, never float
- **PRD-7.7** All API list endpoints paginate

---

## 8. Build phases

| Phase | Contents | Gate |
|---|---|---|
| **0 — Foundation** | Django + DRF + Postgres, auth, roles, core models | Migrations run, admin reachable |
| **1 — Master data** | Employee, Contract, Schedule, Attendance + APIs | Contract resolution passes its test |
| **2 — Leave** | Types, Allocations, Requests, balance engine | Allocation gating passes its test |
| **3 — Payroll engine** | Structures, Rules, computation, Payrun, Payslip | A payslip computes end to end |
| **4 — Frontend** | Shell, all screens | Both demo scenarios clickable |
| **5 — Output** | PDF, email, dashboard | Dashboard filters re-drive data |
| **6 — Polish** | Seed data, demo rehearsal, roadmap | Demo runs twice cleanly |

**Phase 3 is the critical path.** If time runs short, cut frontend polish. Never
cut the rule engine.

---

## 9. Scope boundary

### In scope
Everything in §5, plus the §4.6 integration connections.

### Out of scope — do not build these

Recruitment/ATS · Onboarding and offboarding workflows · Performance management ·
Learning management · Benefits enrollment · Expense claims · Loans and advances ·
Shift rostering and swaps · Attendance regularization workflow · Multi-level
approval chains · Salary revision workflow · Income tax computation and
declarations · Statutory filing formats · Bank transfer file export ·
Multi-currency · Multi-country · Mobile apps · SSO · Password reset ·
Effective-dated records beyond contracts · Audit trail beyond Django defaults

These belong in `claude/deliverables/roadmap.md`, which is a graded deliverable —
listing them there converts every cut into evidence of judgement.

---

## 10. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Rule engine takes longer than expected | Nothing downstream demos | Build it in phase 3, before any frontend polish; test with a fixture, not the UI |
| Formula sandboxing rabbit-hole | Hours lost on a non-graded detail | Use a restricted-eval allowlist; timebox to 45 minutes; fall back to fixed + percentage only |
| Dashboard reads as hardcoded | Fails an explicit requirement | Build it last, on real seeded data; never stub it with constants |
| Relay context loss | A session's work is stranded | Heartbeat commits every 30–45 min; MEGATRON checklist |
| Seed data too thin to show anything | Demo falls flat | Treat T-028 as a real task, not an afterthought; ≥3 months of history |
| Scope creep from the feature survey | Nothing finishes | §9 is binding; the survey feeds the roadmap, not the build |

---

## 11. Open questions

1. **Exact hackathon start and end time** — the clock in
   `claude/state/current-state.md` is assumed. Every scope gate depends on it.
2. Is a hosted/deployed demo required, or does a local walkthrough suffice?
3. Is there a judging rubric available, or only the PDF's stated deliverables?

---

## Appendix — traceability

| Graded rule | PRD requirements | Tasks |
|---|---|---|
| 1 — Contract resolution | PRD-4.1.1 – 4.1.3 | T-016 |
| 2 — Derived weekly hours | PRD-4.2.1 – 4.2.3 | T-015 |
| 3 — Allocation-gated leave | PRD-4.3.1 – 4.3.6 | T-018, T-019 |
| 4 — Sequenced rules | PRD-4.4.1 – 4.4.8 | T-020, T-021 |
| 5 — Pre-finalization warnings | PRD-4.5.1 – 4.5.4 | T-024 |
