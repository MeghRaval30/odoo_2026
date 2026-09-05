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
| T-008 | Confirm hackathon start/end time with user | `TODO` | | blocks accurate scope gates |

## Phase 1 — Backend foundation

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-010 | Django project scaffold + DRF + Postgres config | `TODO` | | `project/backend/` |
| T-011 | Auth: custom User linked to Employee | `TODO` | | users are separate from, but linked to, employees |
| T-012 | Roles & permission classes (5 roles) | `TODO` | | see PRD §3 permission matrix |
| T-013 | Core models: Company, Department, JobPosition | `TODO` | | |
| T-014 | Employee model + serializers + viewset | `TODO` | | |
| T-015 | WorkingSchedule + ScheduleLine, derived weekly hours | `TODO` | | **graded rule #2** |
| T-016 | Contract model + period-overlap constraint | `TODO` | | **graded rule #1** |
| T-017 | Attendance model, worked-hours computation | `TODO` | | |
| T-018 | TimeOffType, Allocation, Request models | `TODO` | | |
| T-019 | Leave balance engine (allocation gating + consumption) | `TODO` | | **graded rule #3** |
| T-020 | SalaryStructure + SalaryRule models | `TODO` | | |
| T-021 | **Rule computation engine** (fixed / percentage / formula) | `TODO` | | **graded rule #4** — the heart of the build |
| T-022 | Payrun + Payslip + PayslipLine models | `TODO` | | |
| T-023 | Payrun state machine: Draft→Compute→Validate→Paid | `TODO` | | |
| T-024 | Payroll validation warnings | `TODO` | | **graded rule #5** — A/C missing, duplicate payslip |
| T-025 | Dashboard aggregation endpoints | `TODO` | | must aggregate ≥5 models |
| T-026 | Payslip PDF generation | `TODO` | | WeasyPrint |
| T-027 | Bulk payslip email from Payrun | `TODO` | | console backend is acceptable for demo |
| T-028 | Seed data command | `TODO` | | ~20 employees, 3 months of history |

## Phase 2 — Frontend

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-030 | React scaffold, routing, API client, auth flow | `TODO` | | |
| T-031 | App shell: top nav with the 6 required menus | `TODO` | | Time Off items **only** in its dropdown |
| T-032 | Login screen | `TODO` | | |
| T-033 | Employee Kanban + List + Form, smart buttons | `TODO` | | both views open the same form |
| T-034 | Contract list + form | `TODO` | | Running contract visually obvious |
| T-035 | Working Schedule list + form with day lines | `TODO` | | |
| T-036 | Attendance list + form | `TODO` | | |
| T-037 | Attendance check-in/out widget in top bar | `TODO` | | red/green, elapsed time |
| T-038 | Time Off: Requests, Allocations, Types | `TODO` | | |
| T-039 | Approve / Refuse flow | `TODO` | | |
| T-040 | Salary Structure + Salary Rule screens | `TODO` | | |
| T-041 | Payrun wizard (2 steps, no record until step 2) | `TODO` | | **specific behaviour called out in the spec** |
| T-042 | Payrun form + action bar | `TODO` | | Compute / Validate / Mark Paid / Send |
| T-043 | Payslip form with salary computation table | `TODO` | | |
| T-044 | Payroll Dashboard | `TODO` | | live data, filters must actually re-drive it |
| T-045 | User Management (admin only) | `TODO` | | |

## Phase 3 — Integration wins (D-002)

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-050 | Attendance → worked days + LOP on payslip | `TODO` | | |
| T-051 | Overtime hours → salary rule input | `TODO` | | |
| T-052 | Approved unpaid leave → payroll deduction | `TODO` | | |

## Phase 4 — Deliverables

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-060 | Demo script, 2 end-to-end scenarios | `TODO` | | `claude/deliverables/demo-script.md` |
| T-061 | Future roadmap writeup | `TODO` | | graded deliverable #3 |
| T-062 | README for judges | `TODO` | | |
| T-063 | Demo rehearsal | `TODO` | | last 2 hours, no code changes |

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
