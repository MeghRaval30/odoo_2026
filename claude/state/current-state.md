# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:  2026-09-05   10:00 IST   ✅ CONFIRMED BY USER (session 02)
Hackathon end:    2026-09-06   10:00 IST   ✅ CONFIRMED BY USER (session 02)
Now:              2026-09-05   11:26 IST
Elapsed:          ~1h 26m  /  24h
REMAINING:        ~22h 34m
Phase:            BUILD
```

> **The clock was wrong in both directions and we have MORE time than the
> handoff claimed, not less.** Session 01 assumed a 09:00 start; the real start
> is 10:00 IST. Session 01 also recorded the handoff at "~13:15 IST" — which is
> ahead of the real wall-clock time when session 02 opened the repo (11:26 IST),
> so that timestamp cannot be right. It was inferred from file timestamps rather
> than read from a clock. **Do not trust narrative timestamps in the handoff
> docs; run `date` yourself.** B-001 is now closed.

### Scope gates — binding

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only. Touch nothing |

---

## WHERE WE ARE

**The backend is complete and verified. The frontend is scaffolded but renders
nothing.** That is the whole picture in one line.

Session 01 (Michael) ran roughly four hours: planning and context system for the
first hour, then the entire Django backend.

---

## ✅ WHAT WORKS — verified, with proof

Two harnesses prove this. Run them yourself before trusting this file:

```bash
cd project/backend
.venv/Scripts/python.exe verify_rules.py    #  28/28 pass — business rules
.venv/Scripts/python.exe smoke_api.py       #  51/51 pass — HTTP layer
```

**Data layer** — 7 Django apps, all migrations applied on SQLite.
Company, Department, JobPosition, WorkLocation, Holiday, User, Role, Employee,
WorkingSchedule, ScheduleLine, Contract, Attendance, TimeOffType, Allocation,
TimeOffRequest, SalaryStructure, SalaryRule, Payrun, Payslip, PayslipLine,
PayslipWarning.

**All five graded rules, proven:**

1. **Contract resolution** — December resolves the expired contract, February
   the running one, on the same employee. Overlap rejected.
2. **Derived weekly hours** — removing a 60-minute break moved 40h → 41h with
   no other edit.
3. **Allocation-gated leave** — request blocked without allocation, succeeds
   after approval, balance decrements, cancellation restores it.
4. **Sequenced rules** — 14 rules execute in order; Gross and Net derived, not
   stored; recompute idempotent; sandbox blocks `__import__`.
5. **Warnings before validation** — `A/C missing` fires for the two seeded
   employees with no bank account.

**Integration (D-002)** — attendance genuinely reaches payroll: overtime is paid
through a rule, unpaid leave produces LOP days that deduct.

**REST API** — token auth, five roles enforced server-side, two-step payrun
wizard (creates nothing at step 1), Compute/Validate/MarkPaid/SendPayslips,
payslip PDF via ReportLab, bulk email with PDF attached, dashboard aggregating
six models with filters that genuinely re-drive the numbers.

**Seed data** — 22 employees, 24 contracts, 859 attendance records, 3 payruns,
60 payslips, 840 payslip lines.

Evidence the numbers are real, not hardcoded:
- Dec ₹1,473,360 < Jan ₹1,482,320 — two employees resolve to older contracts
- Feb ₹1,563,028 > Jan — February overtime reached payroll
- Department filter: ₹1,563,028 → ₹503,998 for Engineering alone

---

## ❌ WHAT IS BROKEN

Nothing known. Both harnesses are green.

## 🚧 WHAT IS HALF-DONE

**The frontend.** `project/frontend/` has:
- Vite + React 19, `react-router-dom` and `recharts` installed
- `src/api.js` — complete and usable: token auth, error flattening, formatters
- `src/index.css` — complete dark design system matching the mockup

`src/App.jsx` is still the untouched Vite demo. **Nothing renders.** No routes,
no components, no screens.

## ⬜ NOT STARTED

Every frontend screen (T-030 … T-045). See the task board.

---

## ➡️ THE SINGLE NEXT ACTION

Start the backend, confirm it serves, then build `src/App.jsx` with routing and
the app shell:

```bash
cd project/backend && .venv/Scripts/python.exe manage.py runserver
# new terminal
cd project/frontend && npm run dev
```

Then work T-030 → T-031 → T-032 → T-044 in that order. The dashboard (T-044) is
worth reaching early — it is the single most visually convincing screen and the
API behind it already works.

---

## LOCKED-IN CONTEXT

See `claude/context/decisions.md`. Do not reopen.

| | |
|---|---|
| **Stack** | React + Django/DRF. **SQLite, not Postgres** *(D-011)* |
| **Scope** | Full spec + 3 integration connections *(D-002)* — all three built |
| **Locale** | India, ₹, PF/ESIC/PT/LWF, single company *(D-003)* |
| **Repo** | `https://github.com/MeghRaval30/odoo_2026` |
| **Git identity** | Each session commits as its own teammate *(D-009)* |
| **Commits** | No machine attribution *(D-010)* |
| **Context folder** | Updated **only** at MEGATRON LAUNCH *(D-012)* |

> ⚠️ **Franklin and Trevor:** your rows in the identity register
> (`claude/workflow/git-strategy.md` §1) are `TBC`. Fill them in, set your
> repo-local git config, and **verify before your first commit.**

---

## ⚠️ OPEN QUESTIONS FOR THE USER

1. ~~**Exact hackathon start and end time.**~~ **ANSWERED (session 02):**
   10:00 IST 2026-09-05 → 10:00 IST 2026-09-06. Clock block above corrected.
2. Commit `12a632f` carries a Claude co-author trailer (predates D-010). The
   fix requires a force-push, which the settings now deny. Only worth doing
   before anyone else clones — likely already too late, and harmless.
3. Is a deployed demo required, or does a local walkthrough suffice?
