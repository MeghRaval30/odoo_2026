# DECISION LOG

**APPEND-ONLY.** Never edit or delete an entry. Add new ones at the bottom.

This file exists so that no session wastes time rediscovering why an earlier
choice was made. **Do not relitigate what is recorded here.** If you genuinely
believe a decision is wrong, append a new dated entry arguing the reversal and
say so to the user — never silently do the opposite.

Format: `D-nnn` · what was decided · why · who · when.

---

## D-001 — Tech stack: React + Django/DRF + PostgreSQL

**Decided by:** user, session 01 (Michael) · 2026-09-05

React frontend, Python/Django backend with Django REST Framework, PostgreSQL
database.

**Rationale.** Django gives us an ORM, migrations, an admin, authentication and
a mature permissions framework essentially free. For an application that is
overwhelmingly role-gated CRUD over a relational model, that head start is worth
more than the flexibility of a thinner framework. The built-in admin is also a
safety net: if the React frontend falls behind, the data is still inspectable and
editable for the demo.

---

## D-002 — Scope posture: full spec plus three connections

**Decided by:** user, session 01 (Michael) · 2026-09-05

Build everything the problem statement requires, plus three links it hints at but
does not mandate:

1. Attendance drives worked days and Loss of Pay on the payslip
2. Overtime hours feed a salary rule
3. Approved leave is reflected in payroll

**Rationale.** The problem statement dangles all three — the payslip carries a
`Worked Days` field, the attendance form has an `Overtime` field that nothing
consumes, and the notes say attendance "may later influence payroll" — but never
requires them. They are therefore the highest-return unrequired work available:
they cost little because the data already exists, and they directly demonstrate
the integration the statement says it is testing for. Broader features from the
wider HR landscape (approval chains, regularization, salary revision history)
were explicitly rejected as a risk to finishing.

---

## D-003 — Locale: India, single company

**Decided by:** user, session 01 (Michael) · 2026-09-05

Rupee currency. Indian statutory deduction rules — Provident Fund, ESIC,
Professional Tax, Labour Welfare Fund. One seeded company, with the `Company`
field present on records and usable as a dashboard filter.

**Rationale.** The mockup is internally inconsistent: the employee, contract and
payslip screens use ₹ and an unmistakably Indian rule set, while the payrun wizard
shows dollars and "United States: Regular Pay". The Indian reading is the stronger
one because the salary rule list in the mockup (BASIC, HRA, STD, BONUS, LTA, FIX,
GROSS, LWF, PF, ESIC, PT, NET) is specifically Indian and makes the salary
structure look deliberate rather than generic. Full multi-company support was
rejected as a 24-hour trap; keeping the field present and filterable gets the
visual credit at almost no cost.

---

## D-004 — Relay handoff is file-based, through the repository

**Decided by:** user, session 01 (Michael) · 2026-09-05

All context passes between sessions as markdown committed to the repo, under
`claude/`. Product code lives separately under `project/`.

**Rationale.** Each handoff is a cold start in a new chat, possibly on a
different account and machine. There is no shared context window and no way to
read a previous session's transcript. The repository is therefore the only
possible channel, and anything not committed is lost permanently.

---

## D-005 — `CLAUDE.md` at repo root as the failsafe

**Decided by:** Michael, session 01 · 2026-09-05

A short `CLAUDE.md` at the repository root announces the relay and points at the
boot sequence.

**Rationale.** Claude Code loads `CLAUDE.md` from the repo root automatically at
session start. That makes it the one file the next session cannot miss, even if
it begins with a vague "continue the work" prompt and even if the user forgets to
mention the briefing. It is deliberately kept short so that it never rots.

---

## D-006 — Heartbeat commits every 30–45 minutes

**Decided by:** Michael, session 01 · 2026-09-05

Context files are committed and pushed continuously through a session, not
batched into the final pack.

**Rationale.** If context were only written at MEGATRON LAUNCH, a session that
died without warning — hitting its limit early, crashing, the laptop closing —
would take everything with it. Frequent small commits cap the worst-case loss at
roughly forty minutes. They also turn the final pack into a tidy-up pass rather
than a scramble that could itself run out of capacity halfway through.

---

## D-007 — Sequential work on `main`, no feature branches

**Decided by:** Michael, session 01 · 2026-09-05

All sessions commit directly to `main`. Every session runs `git pull --rebase`
before its first edit. Force-pushing is forbidden.

**Rationale.** The relay is strictly sequential — only one session works at a
time — so the coordination problem that branches solve does not exist here.
Branching would add merge overhead and a real risk of a session's work being
stranded on a branch nobody remembers to merge. The force-push ban matters
because someone else's only copy of their work may live in the commits it would
destroy.
