# PROGRESS — the RBAC + UI overhaul

Running log for the work the user commissioned on **2026-09-05 at 20:45 IST**.
Newest entry at the **bottom**. One short entry per commit. Append only.

> This file is a diary of *this* stretch of work. Task status still lives only in
> `claude/state/task-board.md`, and the clock in `claude/state/current-state.md`.

---

## The commission, in the user's words

Redo the UI completely against the excalidraw mockup. Build 4–6 full design
languages, not just palettes. Rework account types from the sources: what each
role may do, what each role *sees*, and what its dashboard looks like. Add a
profile menu with self-service settings, including changes that need approval.
Fix the attendance figures — overtime as a count is useless, and decimal hours
are the wrong unit. Add real security: network-restricted login and hardening
against gaming the system. Let a user change their own password.

---

## What the sources actually say

Two documents govern this, and where the user's examples and the sources
disagree the sources win — the user asked for that explicitly.

**`PeoplePay360 HR & Payroll.pdf` §3 — User Roles.** Five roles, quoted:

| Role | The PDF's words |
|---|---|
| **Employee** | View own employee details, attendance records, and leave balances. Create attendance entries and Time Off Requests, with **no payroll or HR administration access** |
| **HR Manager** | Full CRUD on Employees, Attendance, Contracts, Working Schedules and Time Off. Approve or refuse Time Off Requests, **with no access to payroll features** |
| **HR Payroll User** | All HR Manager permissions **plus Create, Read and Update** on Payruns and Payslips. **Read-only** on Salary Structures and Salary Rules |
| **HR Payroll Manager** | All HR Payroll User permissions with **full CRUD** on Payruns, Payslips, Salary Structures and Salary Rules |
| **Admin** | Full access to all modules. User management, role assignment, permission updates, system administration |

**The mockup's LOGIN / USER ACCESS NOTE.** Accounts are created by an Admin.
A user is linked to an employee and assigned **one or more roles** — so yes, one
account can hold several roles; the effective permission set is their union.
Roles control which modules, records and actions appear after login. **Users must
not be able to assign or elevate their own roles.**

**Two places the user's examples and the PDF disagree**, flagged rather than
silently resolved:

1. The user said an HR Manager *cannot* create an attendance record. The PDF
   gives HR Manager full CRUD on Attendance. Resolved in favour of the PDF, but
   split by intent: an employee's own check-in is a *punch*, an HR Manager's is a
   *correction* — a different action, on a different screen, flagged
   `is_manually_edited` and written to the audit log.
2. The user said a Payroll Manager sees only employee details and holidays. The
   PDF gives the Payroll Manager everything an HR Payroll User has plus full
   payroll configuration. Resolved in favour of the PDF.

---

## Plan

| # | Step | State |
|---|---|---|
| 1 | Capability matrix, `/api/me` manifest, server-side enforcement | planned |
| 2 | Self-service: own password, own profile, approval-gated field changes | planned |
| 3 | Security: network-restricted login, lockout, audit log, anti-gaming | planned |
| 4 | Attendance as hours and minutes, everywhere it is shown | planned |
| 5 | Design system: 6 complete themes — colour, type, shape, density | planned |
| 6 | Role-aware navigation and the profile menu | planned |
| 7 | A distinct dashboard per role | planned |
| 8 | Screen-by-screen pass against the mockup | planned |

---

## Log

### 20:45 — picked up, sources read end to end
Extracted all 1,187 text elements from the excalidraw board and the full text of
the problem-statement PDF; both are now transcribed in the scratchpad and the
role table above is quoted from the PDF rather than remembered. Branch
`feat/rbac-ui-overhaul` cut from `main`.

Before the pivot this session finished the previously-queued work: `seed
--employees N` (T-089) and its tests, merged and pushed. A 250-person roster
seeds in 40s and a 233-employee payrun computes in 5.7s; that run raises
`NO_CONTRACT` and `AC_MISSING` together, which closes PRD success criterion 4.
