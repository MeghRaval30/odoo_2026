# PRODUCT SPEC — field-level detail

Recovered from `claude/source/HRMS OXP - 24 hours.excalidraw` (3,459 text
elements parsed programmatically) and cross-checked against the PDF.

**This is the reference for what every screen contains.** Check here before
re-parsing the mockup.

---

## 1. The five graded business rules

These are where the marks are.

1. **Period-based contract selection.** An employee has multiple contracts over
   time; payroll must select the one valid for the payrun's period, not the most
   recent. No employee may hold two `Running` contracts covering the same period.
2. **Derived weekly hours.** Total weekly hours are computed from the schedule's
   day lines, never entered by hand.
3. **Allocation-gated leave.** If a Time Off Type is marked *Requires
   Allocation*, an employee cannot submit a request without an approved
   allocation. Approved requests consume that allocation.
   `Remaining = Allocated − Taken`.
4. **Sequenced salary rules.** Rules execute in `sequence` order so later rules
   reference earlier results. Gross depends on Basic + Allowances; Net depends on
   Gross − Deductions. Rules must genuinely drive the payslip.
5. **Pre-finalization warnings.** Problems surface *before* validation. Named
   examples: missing bank account (`A/C missing`), duplicate payslip.

---

## 2. Roles and permissions

| Role | HR data (Employees, Attendance, Contracts, Schedules, Time Off) | Approve leave | Payruns & Payslips | Structures & Rules | Admin |
|---|---|---|---|---|---|
| **Employee** | Own records only; may create own attendance + time-off requests | — | ✕ | ✕ | ✕ |
| **HR Manager** | Full CRUD | ✓ | ✕ | ✕ | ✕ |
| **HR Payroll User** | Full CRUD | ✓ | Create / Read / Update | **Read-only** | ✕ |
| **HR Payroll Manager** | Full CRUD | ✓ | Full CRUD | Full CRUD | ✕ |
| **Admin** | Full | ✓ | Full | Full | User management, role assignment |

Rules stated in the mockup: user accounts are **separate from** employee records
but **linked** to one; accounts are created by an Admin; roles control which
modules, records and actions appear after login; **users must not be able to
assign or elevate their own roles**. Password reset, invitations and SSO are
explicitly optional enhancements.

---

## 3. Navigation

**Top bar:** `Employees ▼` · `Contracts ▼` · `Attendance` · `Time Off ▼` ·
`Payroll` · `Reports`

- **Time Off ▼** → Requests · Allocations · Time Off Types.
  The mockup is emphatic: *"Do not add separate page buttons for them."*
- **Payroll** → Dashboard · Payruns · Payslips · Structures · Rules
- **Employees ▼** → Employees · Contracts · Departments · Working Schedules
- The attendance check-in widget (⏱) sits in the top bar globally — red when
  checked out, green when checked in.

---

## 4. Entities and fields

### Employee — Kanban (default) + List + Form
Name, avatar/initials, work email, phone, job position, department, manager, work
location, working schedule, company, status (Active).
Form tabs: **Work Information · Private Information · HR Settings**.
Smart buttons with live counts: `Contracts 2` · `Attendance 14` · `Time Off 3` ·
`Allocations 2` — each opens the related list **pre-filtered to this employee**.
Both Kanban and List must open the *same* form.

### Contract — List + Form
Reference (`CON/2026/0042`), employee, department, job position, start date, end
date, wage/month, working schedule, salary structure, structure type
(*Employee Salary*), status **Running / Expired**.
History retained; the Running contract must be visually obvious.

### Working Schedule — List + Form
List: schedule name, calendar type (Fixed / Variable), days/week, hours/week,
company, timezone, status.
Form: weekly lines of **Day · Start Time · End Time · Break · Hours**, with
`+ Add Day` and a **derived Total Weekly Hours**.
Seeded examples: 40 Hours/Week, Night Shift, Retail Weekend, Flexible Hybrid
(37.5h), Part-time 20h.

### Attendance — List + Form
Employee, department, manager, check-in datetime, check-out datetime, worked
hours, overtime hours, status (**Present / Absent / Overtime**), notes.
*"System-generated from check in/out or manually corrected by an authorized user."*
Widget popup: **Check In** if no open session, **Check Out** if already in, live
elapsed time (`6h56`), today's total.

### Time Off Type — List + Form
Type name, unit (**Days / Hours**), requires allocation (**Yes / No**), approval
(Manager / Officer / None), payroll work-entry mapping (*Leave Work Entry*),
display colour, active flag, description.
Seeded: Paid Time Off (Days, allocation Required, Manager approval), Sick Leave
(allocation No), Comp Off (Hours, Officer approval).

### Allocation — List + Form
Employee, time off type, **Allocated / Taken / Remaining**, validity window
(*2026 Annual Balance*), status (Approved / To Approve), description.
*Approved allocation is what creates available balance.*

### Time Off Request — List + Form
Employee, type, start, end, duration, status (**To Approve / Approved /
Refused**), reason, approver, **Allocation Used**.
Actions: **Approve** / **Refuse**. Filters: search, *My Team*.

### Salary Structure — List + Form
Structure name, rule count, employee count, active.
Seeded: Regular Salary (12 rules / 42 employees), Intern Salary (8 / 6),
Contractor (6 / 9).

### Salary Rule — List + Form
Rule name, **code**, **category** (Basic · Allowance · Gross · Deduction · Net),
salary structure, **sequence**, **computation method**, value, quantity.
Computation methods in the mockup: **Fixed Amount · Percentage of Wage · Python
Code** (example expression: `result = categories['BASIC']`).

The reference rule set — use this verbatim for seed data:

| Seq | Rule | Code | Category | Computation |
|---|---|---|---|---|
| 1 | Basic Salary | BASIC | Basic | % of Wage — 50% |
| 10 | House Rent Allowance | HRA | Allowance | |
| 20 | Standard Allowance | STD | Allowance | |
| 30 | Performance Bonus | BONUS | Allowance | |
| 40 | Leave Travel Allowance | LTA | Allowance | |
| 50 | Fixed Allowance | FIX | Allowance | |
| 60 | **Gross Salary** | GROSS | Gross | |
| 70 | LWF Fund | LWF | Deduction | |
| 80 | Provident Fund | PF | Deduction | |
| 90 | ESIC | ESIC | Deduction | |
| 100 | Professional Tax | PT | Deduction | |
| 110 | **Net Salary** | NET | Net | |

### Payrun — List + Form
Name (*February 2026*), period, salary structure, employee count, status
(**Draft → Done/Validated → Paid**), warning count.
Action bar: **COMPUTE · VALIDATE · MARK PAID · SEND PAYSLIPS**.
Body: *Payslips in this Payrun* with per-row Basic / Gross / Net / Status /
Warning.

### Payslip — List + Form
Employee, structure, pay run, period, status, **worked days**, Basic / Gross /
Net, and a **Salary Computation** table of `Rule · Code · Category · Amount`.
Action: **PRINT PAYSLIP** → PDF. Warning badges: *A/C missing*, *Duplicate*.

Worked example from the mockup:
`Basic ₹50,000 → HRA ₹20,000 → STD ₹10,000 → Gross ₹80,000 → PF −₹3,000 → PT −₹2,000 → Net ₹75,000`

### User Account — admin only
Employee* (link), Work Email*, Role(s), Status. List: User · Employee · Role ·
Status, with role filter and search.

---

## 5. The Payrun wizard — a specifically called-out behaviour

`NEW` must **not** create a record. It opens a two-step wizard:

1. **Step 1 — New Pay Run:** Employee Types, Pay Structure, Period.
   **`Continue` does not create the Payrun.**
2. **Step 2 — Select Employee Records:** searchable checkbox list showing
   Employee · Working Hours · Start Date · Wage · Review status, paginated
   (`1–22 / 22`). `Back` / `Create Payrun`.
3. **`Create Payrun`** creates the batch with **only the checked employees** and
   opens the Payrun form.

Then: Compute → review warnings → Validate → Mark Paid → Print PDF / Send
Payslips. Finalized runs remain as immutable history.

---

## 6. Payroll Dashboard

Explicitly the hardest scored piece. The mockup says *"Participants should not
populate it from a single model"* and the PDF requires live data, not static
charts.

**Filters (must actually re-drive the data):** Period · Department · Employee
Type · Company

**KPI cards:**
- Total Net Salary Paid — ₹18.4L, *+8.5% vs previous month*
- Payslips Generated — 148, *142 paid, 6 pending*
- Avg Salary / Employee — ₹12,432, *based on current payrun*
- Approved Time Off Days — 34, *across selected period*
- Attendance Health — 94%, *present / reviewed records*

**Panels, with their declared source models:**

| Panel | Source |
|---|---|
| Salary Cost by Department (bar) | Payslips + Employee Department |
| Monthly Net Salary Trend (line) | historical Payslips / Payruns |
| Payslip Status & Payroll Alerts | Payrun + Payslip validation |
| Attendance Overview | Attendance |
| Time Off Overview | Time Off Requests + Allocations |
| Department Overview | Employee + Contract + Payslip totals |

Sample alerts: `• 2 employees missing bank account` · `• 1 duplicate payslip warning`
Attendance Overview detail: Present / Late / Absent / Overtime, missing
check-outs: 5, manual edits: 7, coverage: 94%.
Time Off Overview columns: Type · Approved Days · Pending · Remaining Balance.
Department Overview columns: Department · Headcount · Monthly Salary.

---

## 7. Explicitly left open to interpretation

The mockup says these are the participant's call:

- Exact leave policy validations and edge cases
- Shift handling, flexible time, break rules on schedules
- The internals of the calculation engine, as long as rules genuinely drive
  payslips
- Whether attendance and leave feed worked days and Loss of Pay onto the payslip
  (**we decided yes** — see D-002)
- Overtime → payroll linkage (**we decided yes** — see D-002)
- Password reset, invitations, SSO — optional enhancements
- The UI itself: *"participants can change the UI as long as the behaviour and
  data relationships are clear"*
