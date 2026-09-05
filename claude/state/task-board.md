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
| T-060 | Demo script, 2 end-to-end scenarios | `IN PROGRESS` | Trevor | in flight, NOT committed. Closing move must route Reports -> Payroll Dashboard |
| T-061 | Future roadmap writeup | `IN PROGRESS` | Trevor | in flight, NOT committed. graded deliverable #3 |
| T-062 | README for judges | `DONE` | Franklin | run-and-verify guide, demo accounts, seed evidence |
| T-063 | Demo rehearsal | `TODO` | | last 2 hours, no code changes |

## Phase 5 — Quality (added session 02/03)

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-070 | Form-payload probe harness | `DONE` | Franklin | `probe_forms.py`, 24/24 create + update |
| T-071 | Django test suite: employees, timeoff, payroll | `DONE` | Trevor | 75 tests, on `test/backend-suite`, UNMERGED |
| T-072 | Django test suite: attendance | `IN PROGRESS` | Trevor | ~421 lines written, not verified, not committed |
| T-073 | Django test suite: accounts / role matrix | `TODO` | Trevor | still a 3-line stub |
| T-074 | Merge `test/backend-suite` into main | `TODO` | Trevor | `--no-ff`, after handoff is confirmed |
| T-075 | Frontend tests | `TODO` | | none exist; lowest priority |

---

## Critical path

```
T-010 → T-013 → T-014 → T-016 → T-020 → T-021 → T-022 → T-023 → T-024
                                            ↑
                                    the whole build hangs here
```

**T-021, the salary rule computation engine, is the single highest-risk item.**
Nothing downstream of it can be demonstrated until it works. If time runs short,
cut frontend polish — never cut T-021.

## Suggested three-way split

| Stream | Tasks |
|---|---|
| **A — HR master data** | T-013 … T-017, T-033 … T-037 |
| **B — Leave & payroll engine** | T-018 … T-024, T-050 … T-052 |
| **C — Frontend shell, payroll UI, dashboard** | T-030 … T-032, T-040 … T-045 |

Stream B is the critical path. If one person is stronger than the others, put
them on B.
