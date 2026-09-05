# PeoplePay360 — HR & Payroll

An integrated Human Resource and Payroll Operations Platform.
Built for the **Odoo Hackathon 2026** (24 hours).

---

## The problem

Most basic HR tools store employee details, attendance, leave and salary as
*separate* records. Real HR and payroll teams need those records to work
together — an employee has multiple contracts over time but payroll must use the
one valid for the period; working hours come from an assigned schedule; leave
balances depend on allocations and approved requests; and all of it has to
resolve into a correct, explainable payslip.

PeoplePay360 is built as a **connected operational flow**, not a set of CRUD
screens.

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

## Stack

React · Django + Django REST Framework · PostgreSQL

## Repository layout

| Path | Contents |
|---|---|
| `project/` | The application — backend and frontend |
| `claude/` | Project context, specification, PRD, task board and handoff notes |
| `claude/source/` | The original problem statement PDF and mockups |
| `CLAUDE.md` | Boot instructions for AI sessions working on this repo |

## Getting started

See [`claude/state/runbook.md`](claude/state/runbook.md) for setup, run, seed and
test instructions.

## Documentation

| Document | |
|---|---|
| [Problem statement](claude/context/problem-statement.md) | What was asked for |
| [Product spec](claude/context/product-spec.md) | Field-level detail for every screen |
| [PRD](claude/context/prd.md) | Requirements and acceptance criteria |
| [Data model](claude/context/data-model.md) | Entities, relationships, constraints |
| [Demo script](claude/deliverables/demo-script.md) | The five-minute walkthrough |
| [Roadmap](claude/deliverables/roadmap.md) | What we would build next |

## Team

Three developers, working in relay across the 24 hours. Development is
AI-assisted; the working protocol is documented in
[`claude/workflow/relay-protocol.md`](claude/workflow/relay-protocol.md).
