# PROBLEM STATEMENT — PeoplePay360

Distilled from `claude/source/PeoplePay360 HR & Payroll.pdf`. The original is
authoritative; read it if anything here seems ambiguous.

**Mockup:** https://app.excalidraw.com/l/65VNwvy7c4X/17vHpCNFjex
(local copies: `claude/source/HRMS OXP - 24 hours.excalidraw` and `.png`)

---

## What it is

**PeoplePay360 — An Integrated Human Resource and Payroll Operations Platform.**
Odoo hackathon, 24 hours, any technology stack permitted.

## The stated problem

> "Many basic HR tools store employee details, attendance, leave, and salary data
> as separate records. Real HR and payroll teams need these records to work
> together."

This is the whole thesis. The statement goes on to enumerate exactly why:

- An employee may have **multiple contracts** over time, but payroll must use the
  contract that applies to the **payroll period**
- Working hours come from an **assigned schedule**
- Attendance contains **exceptions** that may need review
- Leave balances depend on **allocations and approved requests**
- Payroll must transform all of that into **understandable payslips** before
  payment

The goal is explicitly "to build an HR and Payroll platform that goes beyond
simple employee CRUD screens and becomes a connected operational flow."

## The architecture the statement describes

The **Employee record is the central hub**. Contracts and Working Schedules
provide payroll context. Attendance and Time Off capture day-to-day activity.
Salary Structures and Rules define computation. Payruns turn eligible employees
into validated payslips that can be printed as PDF and emailed.

## Key outcomes named in the PDF

| Outcome | What it means |
|---|---|
| **Unified HR flow** | Centralized employee records with seamless navigation to Contracts, Attendance and Time Off |
| **Contract management** | Keep history, but ensure payroll uses only the active, period-specific contract |
| **Operational tracking** | Flexible Working Schedules, attendance with exception handling, full Time Off (requests + allocations) |
| **Payroll processing** | Two-step payrun workflow — scope/period, then employee selection. Payslips with clear breakdowns and validation warnings |
| **Reporting** | A centralized Payroll Dashboard aggregating across Periods, Departments and Employee Types |

## Modules required

**A — HR backend (configuration and master data)**
A1 Employee master · A2 Contracts · A3 Working schedules · A4 Time Off types and
allocations · A5 Salary structures · A6 Salary rules · A7 Reporting and dashboard
configuration

**B — HR & payroll frontend (operational)**
B1 Navigation and employee views · B2 Employee form and related-record navigation
· B3 Attendance list and form · B4 Time Off requests · B5 Payrun creation wizard ·
B6 Payrun processing · B7 Payslip and salary computation · B8 Payslip PDF and
delivery · B9 Payroll dashboard

## Technical guidelines (verbatim intent)

- **Any** backend language, frontend framework and database
- Business rules — contract selection, schedule calculation, leave logic, payroll
  computation — must be implemented **in application logic, not hardcoded values**
- Salary Rules must **actively drive** payslip generation; configuration screens
  must be **fully functional and integrated, not static mockups**
- Payroll issues (duplicate entries, incomplete employee data) must surface to the
  user **before finalization**
- The dashboard must reflect **real-time, live data**, not static charts
- Payslip PDF generation and bulk email from the Payrun workflow are **required**

## Deliverables

1. **Functional platform**, populated with representative employee, contract,
   time, salary and payroll data
2. **Live demonstration** — a five-minute walkthrough of two end-to-end
   scenarios: employee-to-payslip, and leave-allocation-to-request
3. **Future roadmap** — a brief summary of what the team would prioritise next

## Why the statement says it matters

- Integrates HR and payroll into one cohesive end-to-end business flow
- Prioritises **real-world business logic** — period-based contract handling,
  leave allocation, ordered salary calculations — **over interface design**
- Encourages industry-standard architecture: role-based permissions, parent-child
  data relationships, historical payroll tracking
- Lets teams demonstrate technical versatility with their preferred stack

> The phrase "over surface-level UI design" appears twice in the PDF. Depth on the
> data relationships is what is being graded, not screen count.
