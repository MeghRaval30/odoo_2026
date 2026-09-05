# DATA MODEL

> **STATUS: ENTITY MAP ONLY (T-006).** The full field-level schema with types,
> constraints and indexes is the next planning task. Field lists per entity are
> already recorded in `claude/context/product-spec.md` §4 — this file turns them
> into a normalised schema.

---

## Entity relationship map

```
Company
  ├── Department ──── Employee (department)
  ├── JobPosition ─── Employee (job_position)
  └── WorkingSchedule
          └── ScheduleLine  (day, start, end, break)

User (auth) ──1:1── Employee
                      ├── manager ──> Employee (self-referential)
                      ├── Contract          (many, period-scoped)
                      │      ├── working_schedule ──> WorkingSchedule
                      │      └── salary_structure ──> SalaryStructure
                      ├── Attendance        (many)
                      ├── Allocation        (many)
                      │      └── time_off_type ──> TimeOffType
                      ├── TimeOffRequest    (many)
                      │      ├── time_off_type ──> TimeOffType
                      │      └── allocation_used ──> Allocation
                      └── Payslip           (many)

SalaryStructure
      └── SalaryRule  (many, ordered by sequence)

Payrun
  ├── salary_structure ──> SalaryStructure
  └── Payslip  (many)
          ├── employee ──> Employee
          ├── contract ──> Contract      (resolved at compute time)
          ├── PayslipLine  (many, one per rule)
          └── PayslipWarning (many)
```

## Entities

| Entity | Purpose | Key rule |
|---|---|---|
| `Company` | Legal entity | Single seeded (D-003) |
| `Department` | Org grouping | Dashboard aggregation dimension |
| `JobPosition` | Role title | |
| `Employee` | **The hub** | Self-referential manager FK |
| `User` | Auth account | Separate from, linked to, Employee (PRD-3.3) |
| `Role` | Permission set | Five roles per PRD §3.2 |
| `WorkingSchedule` | Named weekly pattern | `hours_per_week` **derived** (PRD-4.2.2) |
| `ScheduleLine` | One day of a schedule | day, start, end, break |
| `Contract` | Period-scoped employment terms | No overlapping `Running` (PRD-4.1.1) |
| `Attendance` | One check-in/out record | `worked_hours` derived |
| `TimeOffType` | Leave policy | `requires_allocation` gates requests |
| `Allocation` | Grants balance | `remaining` **derived** (PRD-4.3.3) |
| `TimeOffRequest` | Consumes balance | Records `allocation_used` |
| `SalaryStructure` | Ordered rule container | |
| `SalaryRule` | One computation | `sequence` determines order (PRD-4.4.4) |
| `Payrun` | A payroll batch | State machine per PRD §6 |
| `Payslip` | One employee's pay | Gross/Net read from lines |
| `PayslipLine` | One rule's result | rule, code, category, sequence, amount |
| `PayslipWarning` | Pre-validation flag | Five types per PRD-4.5.2 |

## Derived-not-stored

These must never be persisted as editable inputs — deriving them is graded:

- `WorkingSchedule.hours_per_week`, `days_per_week`
- `Allocation.taken`, `Allocation.remaining`
- `Attendance.worked_hours`
- `Payslip.gross`, `Payslip.net` (read from `PayslipLine`)
- `Payslip.worked_days`, `lop_days`, `overtime_hours` (from Attendance + leave)

## Conventions

- All money as `DECIMAL(12,2)` — never float (PRD-7.6)
- All timestamps timezone-aware, stored UTC
- Soft-delete via `active` boolean where the mockup shows an Active flag
- `created_at` / `updated_at` on every table
