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

---

## D-008 — REVERSES D-007. Feature branches, merges and version tags are required.

**Decided by:** user, session 01 (Michael) · 2026-09-05

D-007 said all sessions commit directly to `main` with no branching. **That is
now overruled.** Work happens on `feat/` `fix/` `exp/` `docs/` `chore/` branches,
merges into `main` are always `--no-ff`, and meaningful milestones are tagged.

**Rationale.** D-007 reasoned that branches were unnecessary because the relay is
strictly sequential, so there is no coordination problem for branches to solve.
That reasoning was technically sound but missed the actual requirement: the user
wants the repository history to *look like* real collaborative development,
showing experimental branches, versions and merges. The requirement is
presentational, not technical, so it is worth the extra ceremony regardless of
whether branches are needed for coordination.

Abandoned experimental branches are **kept, not deleted** — they are evidence of
genuine engineering exploration, and they stop a later session repeating a failed
attempt.

Full model in `claude/workflow/git-strategy.md`.

---

## D-009 — Each session commits under its own teammate's GitHub account

**Decided by:** user, session 01 (Michael) · 2026-09-05

Git identity follows the session, not the machine. Whichever teammate's GitHub
account is authenticated in the current Claude Code chat is the account that
commits from that chat. Every session sets repo-local `user.name` and
`user.email` at boot and **verifies** them before its first commit.

**Rationale.** All three teammates need to appear as commit authors. A repository
where every commit is authored by one person does not reflect that three people
built it, and for a hackathon submission that misrepresents the team's
contribution.

This is not silently recoverable: commits attributed to the wrong person can only
be fixed by rewriting history, which the relay protocol forbids because it can
destroy another session's only copy of their work. Hence verification before the
first commit rather than a check afterwards.

The identity register lives in `claude/workflow/git-strategy.md` §1. Michael's
row is confirmed; **Franklin and Trevor must fill in their own rows on first
run.**

---

## D-010 — No Claude attribution in commit messages

**Decided by:** user, session 01 (Michael) · 2026-09-05

Commits must not carry `Co-Authored-By: Claude ...` or any other machine
attribution trailer. Each commit is authored by the teammate whose session it is,
and nothing else. The `claude/` folder itself **is** committed — it is the relay's
only channel — but the commits that carry it are the teammate's.

**Rationale.** This follows directly from D-009. The three teammates commit under
their own GitHub accounts specifically so the repository shows three people
building the project together. A machine co-author trailer on every commit
visibly contradicts that, and for a hackathon submission it changes how the
team's contribution reads.

This overrides the default habit of appending such a trailer. Settled — do not
reintroduce it.

**Note:** commit `12a632f` (the initial scaffold) was made before this decision
and does contain the trailer. It was left as-is rather than amended, because
rewriting pushed history is forbidden under D-008. Every commit from this point
forward is clean.


---

## D-011 — SQLite for development and demo, PostgreSQL kept reachable

**Decided by:** Michael, session 01 · 2026-09-05

The backend runs on SQLite by default. `DATABASE_URL` switches it to
PostgreSQL without a code change.

**Rationale.** D-001 named PostgreSQL, but neither PostgreSQL nor Docker is
installed on the build machine, and installing either costs time we do not have
and creates a dependency every teammate would have to repeat before they could
run anything. Zero install friction matters more than engine parity for a
24-hour build whose demo must run on whichever laptop is in the room.

The cost: the gist `EXCLUDE` constraint designed for contract overlap cannot be
created on SQLite. That rule is instead enforced in `Contract.clean()`, which
runs on every save path and is exercised by `verify_rules.py`. On PostgreSQL the
database constraint can be layered back on top as belt and braces.

Nothing else in the schema depends on PostgreSQL.

---

## D-012 — The context folder is updated only at MEGATRON LAUNCH

**Decided by:** user, session 01 (Michael) · 2026-09-05

Files under `claude/` are refreshed when the trigger phrase is given, not
continuously through the session.

**Rationale.** The user briefly asked for rolling context updates and then
reversed it: session capacity should go into building, not bookkeeping. This
partially overrides the heartbeat discipline in D-006 — **product code is still
committed as work progresses**, which is what protects the actual deliverable.
The accepted tradeoff is that context notes go stale between packs, so a session
that dies without warning loses its notes rather than its code.

Do not reintroduce rolling context updates unless the user asks.

---

## D-013 — The UI design language is binding, and it is Anthropic's palette

**Decided by:** user, session 02 (Franklin) · 2026-09-05

Recorded in `claude/context/ui-design-language.md`. That file is binding for any
frontend work and `CLAUDE.md` boot step 5a points at it.

Warm light theme: bone and sand grounds, **Claude orange as the only action
colour**, dusty rose across roughly a quarter of the surface area (KPI grounds,
table headers, row hovers, hairlines), brown rather than grey for text. Type is
a classical pairing — Source Serif 4 for what is read, Inter for what is
operated.

**Rationale.** The first frontend pass was rejected outright as looking
machine-generated, twice. The user's diagnosis was specific and correct: a dark
palette lifted from the mockup, decorative colour, and — the bigger problem —
instructional copy that explained fields and reassured the user rather than
labelling things. §5 of the design doc is a copy rule, and it matters as much as
the palette.

The mockup's **layout and field placement stay binding**; only its colours are
discarded. Product spec §7 explicitly leaves the UI to the participant as long
as behaviour and data relationships stay clear.

Three palettes were tried in order: the mockup's dark theme (rejected), a
Zoho/Razorpay blue light theme (rejected as generic), and this one. The middle
attempt is preserved on `exp/design-language-spike`.

---

## D-014 — A third harness that posts the frontend's own payloads

**Decided by:** Franklin, session 02 · 2026-09-05

`project/backend/probe_forms.py` joins `verify_rules.py` and `smoke_api.py`. It
posts **the exact body each React form builds**, then patches and deletes what it
created. 24/24 across create and update.

**Rationale.** `smoke_api.py` constructs its own correct payloads, so it is
structurally incapable of finding a bug where the *frontend* sends the wrong
shape. Four real bugs were invisible to it and fell out of this harness
immediately: four create forms omitting a required `company` FK, `structure_type`
sent as `""` against a field that is not `blank=True`, and `percentage_base` sent
as `null` against a field that is `blank=True` but not `null=True`.

The general lesson is worth keeping: a harness that builds its own inputs tests
the server, not the product.

---

## D-015 — Trevor started in parallel, before the handoff, under a file-ownership split

**Decided by:** user, session 02 · 2026-09-05

Session 03 was started while session 02 was still live, working on a disjoint set
of files, with an explicit ownership list and an instruction not to merge into
`main` until the user confirms the handoff.

**Rationale.** Capacity was available on the third account and there was
genuinely separable work — the project had two proof harnesses but no test suite.
The split was drawn so the two sessions could not collide: Trevor took new
`tests.py` files and the deliverables, Franklin kept the whole frontend, the API
layer and `claude/state/`.

It worked — Trevor confirmed zero overlapping paths — but it only worked because
the ownership list was written down first. **Do not start a parallel session
without one.**
