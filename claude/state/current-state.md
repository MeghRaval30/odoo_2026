# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:  2026-09-05   10:00 IST   ✅ CONFIRMED BY USER (session 02)
Hackathon end:    2026-09-06   10:00 IST   ✅ CONFIRMED BY USER
Now:              2026-09-05   13:00 IST
Elapsed:          ~3h  /  24h
REMAINING:        ~21h
Phase:            BUILD
```

### Scope gates — binding

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only. Touch nothing |

> **Do not trust narrative timestamps in handoff prose — run `date` yourself.**
> Session 01 assumed a 09:00 start and recorded its handoff at "13:15 IST",
> which was ahead of the real wall clock when session 02 opened the repo.

---

## WHERE WE ARE

**Backend complete and verified. Frontend complete and verified. Both demo
scenarios are clickable end to end.** That is the whole picture in one line.

Sessions 01 (Michael) and 02 (Franklin) are done. Session 03 (Trevor) has been
running in parallel on a separate file set since roughly 12:30 and is mid-flight.

The remaining work is deliverables and polish, not features.

---

## ✅ WHAT WORKS — verified, with the command or click-path that proves it

### Backend — three harnesses, all green

```bash
cd project/backend
./.venv/Scripts/python.exe verify_rules.py   # 28/28 — business rules
./.venv/Scripts/python.exe smoke_api.py      # 51/51 — HTTP layer
./.venv/Scripts/python.exe probe_forms.py    # 24/24 — every UI create + update payload
```

`probe_forms.py` is new in session 02. It posts the **exact body each frontend
form builds**, rather than an idealised one. That distinction found four bugs the
other two harnesses were structurally blind to, because they construct their own
correct payloads.

Plus Trevor's Django test suite on `test/backend-suite` (unmerged, see below):

```bash
./.venv/Scripts/python.exe manage.py test   # 75 tests, employees + timeoff + payroll
```

### Frontend — every top-bar entry reaches a real screen

Run it:

```bash
cd project/backend  && ./.venv/Scripts/python.exe manage.py runserver
cd project/frontend && npm run dev          # http://localhost:5173
```

Sign in `admin@oxp.com` / `demo1234`. The login screen has one-click chips for
all five roles.

| Screen | Route | Verified by |
|---|---|---|
| Payroll Dashboard | `#/dashboard` | Filters re-drive every card; charts render |
| Employees | `#/employees` | Kanban + list toggle, both open the same form, 3 tabs, smart buttons |
| Contracts | `#/contracts` | List + form + **Resolve by period** probe |
| Working Schedules | `#/schedules` | List + day-line form, derived weekly hours |
| Attendance | `#/attendance` | List + correction form; check-in widget in the top bar |
| Time Off | `#/timeoff` | Requests, approve/refuse, balance shown on the form |
| Allocations | `#/allocations` | List, approve/refuse, Allocated/Taken/Remaining |
| Time Off Types | `#/timeoff-types` | List + form |
| Payruns | `#/payroll` | List + two-step wizard + action bar |
| Payslips | `#/payslips` | List + detail with sequence-ordered computation + PDF |
| Payroll Register | `#/reports` | On-screen register + CSV export |
| Salary Structures / Rules | `#/salary-structures`, `#/salary-rules` | Lists + rule form |
| Holidays | `#/holidays` | List + form (new in session 02) |
| Departments / Positions / Locations | `#/departments` etc. | Lists + forms |
| User Management | `#/users` | Admin only, role assignment |

### Demo path proven live in a browser, not just by tests

Payrun wizard step 1 creates nothing → step 2 previews 20 employees with the
contract resolved **for that period** → Create Payrun → Compute → two
`Bank account missing` warnings appear **before** Validate → Validate unlocks →
Mark Paid. Payslip PDF returns a valid `%PDF-1.4`. Send Payslips returns
`20 sent, 0 skipped`. Check-in flips the widget green. Signing in as the Employee
removes the Payroll menu because the API refuses it.

### The five graded rules

All five built, proven by `verify_rules.py` and by Trevor's 75 tests. Rule #1 is
now also directly demonstrable in the UI: **Contracts → Resolve by period**.
December 2025 puts Aarav Mehta on his 01 Jul 2025 contract at ₹78,000; March 2026
puts him on the Jan 2026 one at ₹85,000 — same employee, resolved by period
rather than by recency.

### Seed evidence — the numbers are live, not hardcoded

| Payrun | Net | Why it matters |
|---|---|---|
| Dec 2025 | ₹14,73,360 | Lower than Jan — two employees resolve to older, cheaper contracts |
| Jan 2026 | ₹14,82,320 | |
| Feb 2026 | ₹15,63,028 | Higher — February overtime reached payroll |

Feb filtered to Engineering alone: ₹5,03,998.

Counts: 22 employees, 24 contracts, 859 attendance, 11 leave requests, 3 payruns,
60 payslips, 840 lines, 6 warnings.

---

## ❌ WHAT IS BROKEN

**Nothing known.** All three harnesses green, frontend builds clean, browser
console clean apart from one expected 400 (the attendance widget probing an
account with no linked employee, which then hides itself).

---

## 🚧 WHAT IS HALF-DONE

**All of it is Trevor's, and it is in flight right now — do not mark it done.**

| Work | Where | State |
|---|---|---|
| `project/backend/attendance/tests.py` | Trevor's working tree | Written (~421 lines), **not verified green, not committed** |
| `project/backend/accounts/tests.py` | Trevor's working tree | **Not written** — still a 3-line stub |
| `claude/deliverables/demo-script.md` | repo | **Not rewritten** — still the 68-line outline with no click paths |
| `claude/deliverables/roadmap.md` | repo | **Not rewritten** — still 64 lines |

Branch `test/backend-suite` is **pushed and deliberately unmerged**. It carries 75
passing tests across employees, timeoff and payroll. **Do not delete it and do
not force over it.** Trevor merges it `--no-ff` after the handoff is confirmed.

Franklin verified there is **no merge conflict**: the files on that branch and
the files changed on `main` since `ed09eca` are completely disjoint.

---

## ⬜ NOT STARTED

- T-060 demo script, T-061 roadmap — Trevor is on both, in flight
- No frontend tests of any kind
- No DRF-layer tests for employees / timeoff / payroll — `smoke_api.py` still
  owns that ground and Trevor deliberately did not duplicate it

---

## ➡️ THE SINGLE NEXT ACTION

Trevor: finish and verify `attendance/tests.py`, then write `accounts/tests.py`,
commit one per app, run `manage.py test` green, then merge `test/backend-suite`
into `main` with `--no-ff`.

Then rewrite `claude/deliverables/demo-script.md` **against a running app**, not
against source. The closing move must read:

> Reports → **Payroll Dashboard** → change Period from February 2026 to
> December 2025 → Total Net Paid re-drives ₹15,63,028 → ₹14,73,360 → set
> Department to Engineering → ₹5,03,998.

The "Reports → Payroll Dashboard" hop is required because Reports became a
dropdown in session 02. A script that says "click Reports and the dashboard
appears" is wrong on stage.

---

## LOCKED-IN CONTEXT

See `claude/context/decisions.md`. Do not reopen.

| | |
|---|---|
| **Stack** | React 19 + Vite, Django 6.1 + DRF 3.18. **SQLite, not Postgres** *(D-011)* |
| **Scope** | Full spec + 3 integration connections *(D-002)* — all three built |
| **Locale** | India, ₹, PF/ESIC/PT/LWF, single company *(D-003)* |
| **UI** | Anthropic warm palette, serif/sans pairing. **Binding:** `claude/context/ui-design-language.md` *(D-013)* |
| **Repo** | `https://github.com/MeghRaval30/odoo_2026` |
| **Git identity** | Each session commits as its own teammate *(D-009)* |
| **Commits** | No machine attribution *(D-010)*; one logical unit per commit *(§4a)* |
| **Context folder** | Updated **only** at MEGATRON LAUNCH *(D-012)* |

Identity register in `claude/workflow/git-strategy.md` §1 is now **complete for
all three characters** — Franklin filled in Trevor's row during this pack.

---

## ⚠️ OPEN QUESTIONS FOR THE USER

1. ~~Exact hackathon start and end time.~~ **ANSWERED:** 10:00 IST 05 Sep →
   10:00 IST 06 Sep.
2. Commit `12a632f` carries a Claude co-author trailer from before D-010. Fixing
   it needs a force-push, which is denied at settings level. Harmless; leave it.
3. **Still open — ask.** Is a deployed demo required, or does a local walkthrough
   suffice? It changes what the roadmap and demo script should assume. Trevor
   asked for this explicitly and the user has not answered.
