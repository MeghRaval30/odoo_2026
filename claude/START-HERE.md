# START HERE

You are a Claude session picking up a relay. This file gets you from zero to
productive. Read it top to bottom — it should take about five minutes.

---

## 1. Who you are

Three teammates each hold a Claude Pro account. Because one account runs out of
session capacity long before a 24-hour hackathon ends, the project is built as a
**relay**: one session works until its account is nearly spent, packs everything
it knows into this repo, and hands off to the next account's fresh session.

The three sessions are code-named, in order:

| # | Name | Notes |
|---|---|---|
| 1 | **MICHAEL** | Opened the project. Scaffolded this system. |
| 2 | **FRANKLIN** | Second in the rotation. |
| 3 | **TREVOR** | Third in the rotation. |

After Trevor it cycles back to Michael. Check
`claude/workflow/session-log.md` to see who ran last and therefore who you are.
If it is ambiguous, ask the user — it is the one question always worth asking.

**You have no memory of previous sessions.** Do not pretend otherwise. Do not
guess at prior reasoning. Everything you are permitted to assume is written
down in this folder; if it is not written down, it did not happen.

---

## 2. What we are building

**PeoplePay360 — an Integrated HR & Payroll Operations Platform.** It is an
Odoo hackathon problem statement, 24 hours, any tech stack permitted.

The single most important thing to understand: **this is deliberately not a CRUD
app.** The problem statement explicitly calls out that basic HR tools fail
because employee details, attendance, leave and salary sit as separate records.
The entire point of the build is that they must *work together*.

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

Read `claude/context/problem-statement.md` and
`claude/context/product-spec.md` for the full picture. The untouched originals
are in `claude/source/`.

---

## 3. Read order

Read these in sequence. Do not skip ahead — later files assume the earlier ones.

| Order | File | Why |
|---|---|---|
| 1 | `claude/state/current-state.md` | **The clock.** How much time is left, what phase you are in, what works, what is broken. This governs every scope decision you make. |
| 2 | `claude/state/task-board.md` | The single source of truth for task status. Pick your work from here. |
| 3 | `claude/state/blockers.md` | Open problems, **including what has already been tried and failed.** Read this before debugging anything. |
| 4 | `claude/context/decisions.md` | Settled choices with rationale. Do not relitigate these. |
| 5 | `claude/context/prd.md` | The product requirements. What "done" means. |
| 6 | `claude/context/data-model.md` | Entities, fields, relationships, constraints. |
| 7 | `claude/state/runbook.md` | How to install, run, seed and test. Get the app running before you write code. |
| 8 | `claude/workflow/git-strategy.md` | **Identity and branching. Read before your first commit.** |
| 9 | `claude/deliverables/demo-script.md` | The 5-minute walkthrough. Anything not in here is optional. |

If a full briefing from the previous session exists, read
`claude/handoff/NEXT-SESSION-PROMPT.md` instead of items 1–8 — it is written to
replace them, and it will tell you which of the above still need reading.

---

## 4. The five business rules that are actually graded

Memorise these. They are where the marks are, and they are what separates this
from twenty pretty CRUD screens.

1. **Period-based contract selection.** An employee has multiple contracts over
   time. Payroll must select the contract valid for the *payrun's period*, not
   simply the most recent one. No employee may hold two `Running` contracts
   covering the same period.
2. **Derived weekly hours.** Total weekly hours are *computed* from the working
   schedule's day lines. Never typed in by hand.
3. **Allocation-gated leave.** If a Time Off Type is marked *Requires
   Allocation*, an employee cannot submit a request without an approved
   allocation. Approved requests then consume that specific allocation.
   `Remaining = Allocated − Taken`.
4. **Sequenced salary rules.** Rules execute in `sequence` order so later rules
   can reference earlier results (Gross depends on Basic + Allowances; Net
   depends on Gross − Deductions). Rules must genuinely drive the payslip —
   hardcoded numbers are called out in the problem statement as a failure.
5. **Pre-finalization warnings.** Payroll problems must surface *before*
   validation. The named examples are a missing bank account (`A/C missing`) and
   a duplicate payslip.

---

## 5. How to work

**Every 30–45 minutes**, and after any meaningful decision:

```bash
# update claude/state/current-state.md and claude/state/task-board.md, then
git add -A && git commit -m "chore(claude): heartbeat — <what changed>" && git push
```

This is not optional. If your session dies without warning — hits its limit
early, crashes, laptop closes — the heartbeat is the only thing standing between
the team and hours of lost work.

Also, as you go:
- Append each of the user's prompts, verbatim, to `claude/handoff/prompt-history.md`
- Append any real decision, with its rationale, to `claude/context/decisions.md`
- Update `claude/state/task-board.md` the moment a task changes status

---

## 6. When you hear "MEGATRON LAUNCH"

Stop everything. Open `claude/workflow/megatron-checklist.md` and execute it end
to end. Full detail is in `claude/workflow/relay-protocol.md`.

---

## 7. Ground rules

- **Respect the scope gates.** They are in `current-state.md`. Under 8 hours
  remaining means feature freeze, no matter how good the idea.
- **Do not relitigate decisions.** If `decisions.md` settled it, it is settled.
  If you genuinely think a decision is wrong, append a new dated entry arguing
  the reversal — do not silently do the opposite.
- **Read `blockers.md` before debugging.** Someone may have already burned an
  hour on exactly what you are about to try.
- **The user is not a tooling expert.** He has asked Claude to do the heavy
  lifting end to end. Where a step truly needs a human — a browser login, for
  instance — open it on his screen, ask for the one action, then take back over.
- **Decide from the spec.** The PDF and mockups in `claude/source/` are the
  source of truth. Derive answers from them rather than stalling to ask; state
  your assumption and keep moving.
