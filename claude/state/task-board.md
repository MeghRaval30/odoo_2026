# TASK BOARD

**This is the single source of truth for task status.** Do not duplicate status
into any other file. Update a task the moment it changes — not at the end of your
session.

**Statuses:** `TODO` · `IN PROGRESS` · `BLOCKED` · `DONE` · `CUT`
A task you started but did not finish is `IN PROGRESS`, never `DONE`.

---

## Phase 0 — Setup & Planning

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-001 | Read and digest problem statement PDF | `DONE` | Michael | |
| T-002 | Parse Excalidraw mockup, extract all fields | `DONE` | Michael | 3,459 text elements parsed |
| T-003 | Design relay context system | `DONE` | Michael | |
| T-004 | Scaffold `claude/` folder + `CLAUDE.md` | `DONE` | Michael | |
| T-005 | Write the PRD | `DONE` | Michael | `claude/context/prd.md` v1.0 |
| T-006 | Write the data model / schema | `DONE` | Michael | `claude/context/data-model.md` v1.0 |
| T-007 | `git init`, connect remote, first push | `DONE` | Michael | pushed; branching model live |
| T-008 | Confirm hackathon start/end time with user | `DONE` | Franklin | 10:00 IST 05 Sep -> 10:00 IST 06 Sep, confirmed by user |

## Phase 1 — Backend foundation

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-010 | Django project scaffold + DRF + Postgres config | `DONE` | Michael | Django 6.1 + DRF 3.18, SQLite (D-011) |
| T-011 | Auth: custom User linked to Employee | `DONE` | Michael | email-login User, OneToOne to Employee |
| T-012 | Roles & permission classes (5 roles) | `DONE` | Michael | 5 role classes, enforced server-side |
| T-013 | Core models: Company, Department, JobPosition | `DONE` | Michael | + WorkLocation, Holiday |
| T-014 | Employee model + serializers + viewset | `DONE` | Michael | list/detail serializers, smart-button annotations |
| T-015 | WorkingSchedule + ScheduleLine, derived weekly hours | `DONE` | Michael | **verified** 40h->41h on line edit |
| T-016 | Contract model + period-overlap constraint | `DONE` | Michael | **verified** Dec=expired, Feb=running contract |
| T-017 | Attendance model, worked-hours computation | `DONE` | Michael | derived worked_hours, one-open-session constraint |
| T-018 | TimeOffType, Allocation, Request models | `DONE` | Michael |  |
| T-019 | Leave balance engine (allocation gating + consumption) | `DONE` | Michael | **verified** gate blocks, balance derives, cancel restores |
| T-020 | SalaryStructure + SalaryRule models | `DONE` | Michael | 14 rules seeded on Regular structure |
| T-021 | **Rule computation engine** (fixed / percentage / formula) | `DONE` | Michael | **verified** sequenced, idempotent, sandboxed |
| T-022 | Payrun + Payslip + PayslipLine models | `DONE` | Michael | + PayslipWarning |
| T-023 | Payrun state machine: Draft→Compute→Validate→Paid | `DONE` | Michael | **verified** PAID is terminal and read-only |
| T-024 | Payroll validation warnings | `DONE` | Michael | **verified** A/C missing fires on 2 employees |
| T-025 | Dashboard aggregation endpoints | `DONE` | Michael | aggregates 6 models, filters re-drive data |
| T-026 | Payslip PDF generation | `DONE` | Michael | ReportLab (pure wheel, no GTK) |
| T-027 | Bulk payslip email from Payrun | `DONE` | Michael | console/locmem backend, PDF attached |
| T-028 | Seed data command | `DONE` | Michael | 22 employees, 3 months, 840 payslip lines |

## Phase 2 — Frontend

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-030 | React scaffold, routing, API client, auth flow | `DONE` | Franklin | hash router, auth gate, api client wired |
| T-031 | App shell: top nav with the 6 required menus | `DONE` | Franklin | six menus; Time Off items only in its dropdown |
| T-032 | Login screen | `DONE` | Franklin | + one-click chips for all five demo roles |
| T-033 | Employee Kanban + List + Form, smart buttons | `DONE` | Franklin | kanban + list share one form; 3 tabs; smart buttons |
| T-034 | Contract list + form | `DONE` | Franklin | RUNNING marked with a green rule; + Resolve-by-period probe |
| T-035 | Working Schedule list + form with day lines | `DONE` | Franklin | day lines; no weekly-hours input, it is derived |
| T-036 | Attendance list + form | `DONE` | Franklin | list + correction form; edits flagged is_manually_edited |
| T-037 | Attendance check-in/out widget in top bar | `DONE` | Franklin | top-bar widget; hides for accounts with no linked employee |
| T-038 | Time Off: Requests, Allocations, Types | `DONE` | Franklin | requests, allocations and types all built |
| T-039 | Approve / Refuse flow | `DONE` | Franklin | approve/refuse post to the server actions |
| T-040 | Salary Structure + Salary Rule screens | `DONE` | Franklin | structures list + rule form, value fields switch on computation |
| T-041 | Payrun wizard (2 steps, no record until step 2) | `DONE` | Franklin | step 1 creates nothing; step 2 searchable with 1-N/N counter |
| T-042 | Payrun form + action bar | `DONE` | Franklin | Compute/Validate/Mark Paid/Send + Export Register |
| T-043 | Payslip form with salary computation table | `DONE` | Franklin | sequence-ordered computation table + Print Payslip |
| T-044 | Payroll Dashboard | `DONE` | Franklin | 5 spec KPIs, 4 filters, all re-drive; + register report |
| T-045 | User Management (admin only) | `DONE` | Franklin | admin only; server refuses self-role-escalation |

## Phase 3 — Integration wins (D-002)

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-050 | Attendance → worked days + LOP on payslip | `DONE` | Michael | worked_days + LOP land on payslip |
| T-051 | Overtime hours → salary rule input | `DONE` | Michael | OT rule pays 1.5x derived hourly rate |
| T-052 | Approved unpaid leave → payroll deduction | `DONE` | Michael | unpaid leave -> LOP deduction |

## Phase 4 — Deliverables

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-060 | Demo script, 2 end-to-end scenarios | `DONE` | Trevor | written and committed; **not rehearsed** — see T-063 |
| T-061 | Future roadmap writeup | `DONE` | Trevor | 694 lines, grounded in the current code |
| T-062 | README for judges | `DONE` | Franklin | run-and-verify guide, demo accounts, seed evidence |
| T-063 | **Demo rehearsal + correct the script in place** | `DONE` | Michael | **top priority.** Scenario B was written against a form that could not submit until T-079; B5's balance claim is suspect |

## Phase 5 — Quality (added session 02/03)

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-070 | Form-payload probe harness | `DONE` | Franklin | `probe_forms.py`; extended to **26/26** by T-080 |
| T-071 | Django test suite: employees, timeoff, payroll | `DONE` | Trevor | merged into `main` |
| T-072 | Django test suite: attendance | `DONE` | Trevor | 420 lines, committed and green |
| T-073 | Django test suite: accounts / role matrix | `DONE` | Trevor | 830 lines, five-role matrix, both allowed and denied sides |
| T-074 | Merge `test/backend-suite` into main | `DONE` | Trevor | `--no-ff` at `7688be1`; suite now 158/158 |
| T-075 | Frontend tests | `TODO` | | none exist; lowest priority — the browser pass and `probe_forms.py` cover the same ground more cheaply |

## Phase 6 — Bug fixes found in session 03

Three of these were *documented as failing tests* by session 03's first half,
which asserted the broken behaviour on purpose. Closing them meant reversing
those assertions, not deleting them — each is now a regression guard.

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-076 | Contract scope test caught up to Franklin's fix | `DONE` | Trevor | the merge made it fail *by succeeding*; leak was already closed in `e894840` |
| T-077 | Employee could not raise their own time-off request | `DONE` | Trevor | carve-out substitutes the employee **before** validation, not in `perform_create` — the allocation gate reads that field |
| T-078 | Payroll User could delete payruns | `DONE` | Trevor | delete is the whole difference between the two payroll rows of the spec matrix |
| T-079 | **Time Off request form could never submit, for anyone** | `DONE` | Trevor | `half_day` sent as a boolean to a `FIRST`/`SECOND` choice field, with no control rendered at all. 400 since the screen was written |
| T-080 | Probe now covers the time-off request form | `DONE` | Trevor | the one uncovered create form was the broken one. 24/24 → 26/26 |
| T-081 | Browser pass over the payrun flow | `DONE` | Trevor | wizard → compute → validate → mark paid → payslip detail, driven by hand |

---

## ~~Critical path~~ — closed

~~`T-010 → T-013 → T-014 → T-016 → T-020 → T-021 → T-022 → T-023 → T-024`~~

**Struck out: the whole chain is DONE and verified.** T-021, the salary rule
engine, was the highest-risk item in the project and has been green since session
01. There is no longer a build-blocking dependency anywhere on this board.

## ~~Suggested three-way split~~ — closed

**Struck out: every stream is finished.** Streams A, B and C all completed across
sessions 01–03. The split was a plan for building; nothing is left to build.

## Priorities for the time actually remaining (~20h at 13:40)

Everything below is optional except the first line.

| Order | What | Why |
|---|---|---|
| 1 | **T-063 — rehearse the demo and fix the script in place** | The only item with real risk left. Scenario B has never been walked, and it is the half of the demo built on the form that was broken until T-079 |
| 2 | Re-ask open question 3 — is a deployed demo required? | Asked twice, never answered. Cheap now, expensive at hour 22 |
| 3 | Polish only if the rehearsal surfaces something | Do not open new work on a green board |
| 4 | T-075 frontend tests | Genuinely lowest value for a 24h build; listed for completeness |

**The board is effectively complete.** The failure mode from here is not running
out of time — it is breaking something that already works. Prefer rehearsal over
refactoring.

## Phase 5 — Session 04: audit, rehearsal and correctness

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-080 | Re-audit PDF + mockup for missing features | `DONE` | Michael | all 16 modules present; nothing missing |
| T-081 | Fix stale refusal on the time-off request form | `DONE` | Michael | found by rehearsal; blocked Scenario B3 |
| T-082 | Label dashboard Remaining column scope | `DONE` | Michael | period-scoped vs all-period figures read as arithmetic |
| T-083 | Honour `is_employer_cost` / `appears_on_payslip` | `DONE` | Michael | were dead config; employer PF reduced net pay |
| T-084 | Embed a rupee-capable payslip PDF font | `DONE` | Michael | Helvetica has no U+20B9; every figure was wrong |
| T-085 | Draw PDF table cells in the embedded font | `DONE` | Michael | FONTNAME was header-only, body fell back to Helvetica |
| T-086 | Prorate mid-period joiners and leavers | `DONE` | Michael | 20 Feb joiner was paid a full month |
| T-087 | Seed attendance across Dec–Mar, skip holidays | `DONE` | Michael | Dec/Jan payslips read 0 worked days |
| T-088 | Full browser QA of all 18 routes and both flows | `DONE` | Michael | zero failed requests; state machine verified |
| T-089 | **Build a 200–300 employee dataset** | `TODO` | | **user-requested, deferred to now.** Keep demo employees intact; use `bulk_create`; measure payrun timing |
| T-090 | Close PRD criterion 4 (two distinct warnings) | `TODO` | | only `AC_MISSING` fires; fold into T-089 |
