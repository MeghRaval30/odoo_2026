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

---

## D-016 — Time-off ownership is substituted *before* validation, not in `perform_create`

**Decided by:** Trevor, session 03 · 2026-09-05

`AttendanceViewSet` implements employee self-service by forcing the employee in
`perform_create` (`serializer.save(employee_id=user.employee_id)`).
`TimeOffRequestViewSet` deliberately does **not** copy that pattern. It overrides
`create()` and substitutes the employee into the payload before
`is_valid()` runs.

**Rationale.** `TimeOffRequestSerializer.validate()` runs the allocation gate —
graded rule #3 — against the employee **in the payload**, and resolves
`allocation_used` from that employee's approved allocations. If the employee were
overridden afterwards, an account could post a colleague's id, clear the gate on
the colleague's balance, and have the row saved under its own name still pointing
at the colleague's allocation. That defeats the gate *and* corrupts the
colleague's derived `remaining`, because `taken`/`remaining` are computed over
approved requests referencing the allocation.

The attendance pattern is safe only because nothing in attendance validation
depends on who the employee is. The difference is real, not stylistic.
`accounts/tests.py::test_the_allocation_gate_runs_against_the_requester_not_the_payload`
fails under the `perform_create` approach — it exists to keep this decision
from being "simplified" back.

---

## D-017 — Payrun DELETE is gated on `can_configure_payroll`, not a new property

**Decided by:** Trevor, session 03 · 2026-09-05

`CanRunPayroll` now checks `DELETE` separately, against `can_configure_payroll`.

**Rationale.** The spec's role matrix gives the HR Payroll User
"Create / Read / Update" and the HR Payroll Manager "Full CRUD" — delete is the
entire difference between the two rows, and collapsing every unsafe method into
one `can_run_payroll` check erased it. `can_configure_payroll` is named for
salary structures and rules, but it resolves to exactly the set required here:
Payroll Manager or Admin. Adding a near-duplicate `is_payroll_manager` property
would give the model two names for one predicate. The permission class docstring
says why the name reads oddly, since the name alone does not.

---

## D-018 — Commit subjects carry no character name

**Decided by:** user, session 03 · 2026-09-05

Commits are authored under each teammate's own git identity (D-009) and the
subject line carries **no** `[michael]` / `[franklin]` / `[trevor]` tag. This
supersedes the tagging convention used in sessions 01 and 02.

**Rationale.** The user asked for it directly: *"keep commiting what u do from
megh raval 30, dont write the charcater names in commit names pls."* The author
field already records who did the work, and it is the field GitHub attributes by.
The tag was duplicating that into prose where it read as noise.

Existing tagged commits are left alone — rewriting them needs a force-push, which
is forbidden here.

---

## D-019 — A test that documents an open bug is reversed when fixed, never deleted

**Decided by:** Trevor, session 03 · 2026-09-05

Session 03's first half wrote tests that asserted **broken** behaviour on
purpose, each under a `# PRODUCT BUG:` comment naming the fix. When those bugs
were closed, the tests were rewritten to assert the correct behaviour and kept,
with the comment rewritten to explain what the guard is for.

**Rationale.** Three of these existed and all three are now closed. Deleting them
would have thrown away both the discovery and the protection — these are exactly
the regressions most likely to reappear, because each was a plausible-looking
omission rather than a typo. Reversing the assertion costs three lines and leaves
a test that says *why* it exists.

It also produces a useful signal in a relay: the contract-leak test failed **by
succeeding** when session 03's branch met Franklin's fix on `main`. A red test
was how the two sessions discovered they had converged on the same bug.

---

## D-020 — Every frontend create form must be covered by `probe_forms.py`

**Decided by:** Trevor, session 03 · 2026-09-05

`probe_forms.py` covered twelve create forms. The one it did not cover — the New
Time Off Request form — had been returning 400 to every submission since the
screen was written, and no harness noticed.

**Rationale.** The probe's value is entirely in mirroring the payload the UI
actually builds; a form outside it is a form nobody is checking. The rule is now:
if a screen POSTs to an endpoint, that endpoint has a probe case. The only
permitted exception is the payrun wizard's two endpoints, which `smoke_api.py`
drives end to end as part of the state-machine run.

Concretely: uncovered surface is worse than untested surface, because a green
harness on an incomplete list reads as proof.


---

## D-021 — Employer contributions are separated from employee pay

**Decided by:** Michael, session 04 · 2026-09-05

`SalaryRule.is_employer_cost` now genuinely keeps a rule out of the employee's
gross and net, accumulating instead into a parallel bucket exposed as
`Payslip.employer_cost` and `Payslip.ctc`.

**Rationale.** The flag was stored on the model, serialized by the API and
editable as a checkbox in the Salary Rule form — and `payroll/engine.py` never
read it. Ticking "Employer cost" on a provident-fund rule still reduced the
employee's take-home pay, because every rule's amount was accumulated into
`categories` regardless of who bears it. Configuration that silently does
nothing is worse than configuration that is absent, and this particular
omission produced wrong money.

Employer rules stay visible to later rules by code, since an employer-side rule
may legitimately reference the employee-side figure. The flags are snapshotted
onto `PayslipLine` so a historical payslip keeps reading correctly after a rule
is edited.

---

## D-022 — The payslip PDF embeds a rupee-capable font

**Decided by:** Michael, session 04 · 2026-09-05

`payroll/pdf.py` registers a TrueType face carrying U+20B9 when the platform
has one, and falls back to an ASCII `INR` prefix when it does not. Every table
sets a base `FONTNAME` across its whole grid.

**Rationale.** ReportLab's built-in Helvetica is a Type 1 face encoded WinAnsi,
which has no rupee glyph, so every money figure on every payslip PDF rendered a
substitute character. The PDF is a required deliverable and no harness had ever
opened one — they only assert that bytes come back.

Embedding the font was not sufficient on its own: each `TableStyle` set
`FONTNAME` only on its header row or label column, so the body cells — exactly
where the money sits — still fell back to Helvetica. The base entry fixes that.

The ASCII fallback matters because the build machine happens to have Arial;
a teammate's machine might not, and a payslip that renders correctly only on one
laptop is not fixed.

---

## D-023 — Pay is prorated to the contract's own dates

**Decided by:** Michael, session 04 · 2026-09-05

`gather_period_facts` clamps the day window to the contract, and a proration
factor scales any percentage taken against the contract wage. Percentages of
another rule are left alone, because their base is already prorated.

**Rationale.** Expected days were measured across the whole payroll period with
no reference to `contract.start_date` or `end_date`, and a percentage rule took
its cut of the full monthly wage. An employee joining on 20 February was
therefore paid a full February. It is the commonest real payroll case and the
one a payroll manager would refuse to sign, and it sat inside the graded rule
engine. The roadmap had it as deferred future work (N-3); with time in hand it
was worth converting a documented weakness into a strength.

---

## D-024 — Overtime in the seed is confined to February onward

**Decided by:** Michael, session 04 · 2026-09-05

Seeded attendance spans December 2025 to March 2026, but only February onward
carries overtime.

**Rationale.** Attendance previously started in February, so the December and
January payslips read "Worked Days 0.00 / 23.00" — the payruns were arithmetically
correct but looked broken. Extending attendance fixes that, but sprinkling
random overtime across every month would swamp the demo's two headline signals:
December sits under January purely because two employees resolve to older,
cheaper contracts, and February rises purely because overtime reached payroll.
Keeping the earlier months clean preserves both.

Attendance is also no longer generated on public holidays, which had made worked
days exceed expected days — January read 22 of 21.

---

## Session 05 — Franklin

### D-025 — Roles are capabilities, and an account holds the union of its roles
**Decided:** session 05 · **Status:** settled

The five roles are exactly the ones PDF §3 names: Employee, HR Manager, HR
Payroll User, HR Payroll Manager, Admin. They are defined once, declaratively,
in `project/backend/accounts/capabilities.py`, and everything else — the
permission classes, the navigation manifest, the frontend's `auth.has()` — reads
that one table.

**An account may hold several roles, and its effective permission is the union
of them, not the highest single role.** The mockup's LOGIN / USER ACCESS NOTE
says to assign "one or more roles", and "HR Manager + Payroll User" is a
combination a real company grants; it has to behave as the sum of both.

The four pre-existing booleans (`is_admin`, `can_manage_hr`, `can_run_payroll`,
`can_configure_payroll`) survive as *views onto* the matrix rather than as a
second copy of the rules, which is why 86 existing account tests kept passing
untouched.

**Do not** add a role check anywhere else. If a new rule is needed, it is a new
capability in that file.

### D-026 — Where the user's examples contradict the sources, the sources win
**Decided:** session 05 · **Status:** settled, but flag it to the user

The same message that gave examples also said "strictly follow the problem
statement and excaildraw". Two examples contradict PDF §3:

- "hr manager … cant create a new attendance record" — the PDF gives HR Manager
  full CRUD on Attendance. Followed the PDF, but split by *intent*: an
  employee's own check-in is a **punch** (own record, today only, network-gated);
  an HR Manager's is a **correction** (any record, any date, flagged
  `is_manually_edited`, written to the audit log). Both readings are satisfied.
- "payroll amanger can see only employee details and holidays" — the PDF gives
  the Payroll Manager everything the Payroll User has plus full CRUD on payruns,
  payslips, structures and rules. Followed the PDF.

Recorded rather than settled silently. If there is a chance to ask, ask.

### D-027 — Six themes, chosen per browser rather than per account
**Decided:** session 05 · **Status:** settled

The user asked for four to six full design languages. Six exist in
`project/frontend/src/themes.css`: Ledger, Console, Atrium, Blueprint, Marigold,
Graphite. Each sets its own type pairing, corner geometry, border weight, shadow
behaviour, density and label treatment — not merely a palette, which is why
`index.css` was rewritten so that nothing hard-codes a colour, radius, shadow or
padding.

The choice lives in `localStorage`, not on the User model. Someone presenting on
a projector wants Blueprint for its contrast; the same person at night wants
Console. That is a property of where you are sitting, not of who you are — and
it keeps the server out of a preference that has no business being audited.

Every theme's font stack ends in a real system fallback **of the same class**
(serif / grotesk / mono / humanist), so an offline demo machine still gets six
distinguishable looks rather than six copies of Arial.

### D-028 — A role's unusable menus are absent, and the menu is built server-side
**Decided:** session 05 · **Status:** settled

`/api/auth/me/` returns a navigation tree already pruned to the account's
capabilities, and the shell renders whatever it is given. The mockup's access
note asks to "show only the modules and actions allowed by the user's assigned
role" — absent, not greyed out.

Building the menu in the frontend would be a second copy of the rules, and
second copies drift: eventually the menu offers a link that 403s. Hiding remains
presentation only; every route is independently enforced server-side.

### D-029 — Four dashboards behind four endpoints, not one endpoint with hidden cards
**Decided:** session 05 · **Status:** settled

`/api/dashboard/` (payroll), `/api/dashboard/hr/`, `/api/dashboard/me/`,
`/api/dashboard/admin/`.

Hiding a card in the browser leaks its numbers to anybody who opens the network
tab. The HR Manager role is defined as having "no access to payroll features",
so the payroll figures must never leave the server for that role. This also
closed a real leak: `/api/dashboard/` had only been gated on being signed in, so
an HR Manager could read total net paid.

### D-030 — Self-service is split by blast radius, not by convenience
**Decided:** session 05 · **Status:** settled

Phone, personal email and address are the employee's own business and apply
immediately. Name, date of birth, gender, PAN, **bank account number and IFSC**
go through an HR approval queue.

Repointing a bank account the day before a payrun is the single most attacked
field in any payroll system, and a self-service change with no second pair of
eyes makes the whole control decorative. Nobody may approve a change to their
own record — HR rights or not — and that check lives on the model's `approve()`,
at the write, not in the view.

Department, manager, position, contract and wage are not self-service in either
form. They are HR's records and appear on the profile screen as read-only.

### D-031 — Sessions expire, and the network is re-checked on every request
**Decided:** session 05 · **Status:** settled

DRF's token never expires. `accounts/authentication.py` adds an idle timeout, an
absolute lifetime and optional address binding, all driven by an
Admin-editable settings row.

The network policy is checked on **every request**, not only at sign-in.
Checking once would make the control a formality: authenticate at the office,
then use the token from anywhere. `X-Forwarded-For` is ignored unless
`TRUSTED_PROXY_COUNT` says a proxy is genuinely in front — otherwise anyone
claims to be on the office Wi-Fi by setting one header.

### D-032 — Worked time is decimal in the data and hours-and-minutes on screen
**Decided:** session 05 · **Status:** settled

Payroll multiplies hours by rates, so the stored value stays decimal. But `8.45`
is eight hours and **twenty-seven** minutes, not forty-five, and a timesheet
that invites that misreading is a timesheet nobody trusts. `core/formatting.py`
converts; the API serves `worked_hm` / `overtime_hm` / `elapsed_hm` beside the
decimals. The mockup agrees — its attendance widget reads `6h56`.

The same reasoning killed the old overtime tile. A count of how many *times*
overtime happened answers no question anybody has; the useful pair is how much
overtime there was and how many people carried it.

### D-033 — PRD criterion 4 is met with an off-cycle correction payslip
**Decided:** session 06 · **Status:** settled · **The user was asked and said "decide urself"**

Criterion 4 wants at least two distinct warning codes before validation. The
22-person demo roster raised only `AC_MISSING`, twice.

Three options were put to the user. `NO_CONTRACT`, `NEGATIVE_NET` and
`NO_STRUCTURE` were all rejected for the same reason: they are **ERROR**
severity, and an errored payrun cannot be validated, so seeding one would break
demo steps A8 and A9 two beats after the warning is read out.

`DUPLICATE` is the exception. It is warning severity, so Validate still
proceeds; it needs nothing but a payslip that already covers the period; and it
is the **problem statement's own named example**. So the seed leaves one —
`March 2026 (off-cycle correction)`, a single payslip for Vikram Rao, computed
and deliberately not paid, exactly as a real correction sits mid-month. Vikram
appears nowhere in the demo script, so the three warnings name three different
people.

Cost, accepted knowingly: the demo's March run now creates 19 payslips rather
than 20 and reads "3 warning(s)" rather than 2. The button still says
`Create payrun (20)` — twenty are selected, one is skipped, and the skip is the
point.

### D-034 — The dashboard opens on the newest *paid* period, named by the server
**Decided:** session 06 · **Status:** settled

Following from D-033: the correction run is the newest period and holds one
payslip, so a dashboard defaulting to "newest payrun" would open on it with
every KPI reading as a collapse. Paid means finished, and finished is what a
dashboard should show. This is a better default independently of D-033 — any
month half-computed would have caused the same.

The important half is that **two** places were deciding it. `_filters` picked
the period when none was passed, and `Dashboard.jsx` separately seeded its
filter state from `periods[0]`. Fixing only the backend would have left the
screen asking for the off-cycle period anyway. `/api/dashboard/filters/` now
returns `default_period` and both read that one value.

**The general rule this is an instance of:** when a screen and its API both
decide the same thing, they will eventually decide it differently. Name the
answer once, on the server, and have the screen read it.

### D-035 — A theme selector must outrank the fallback that backs it up
**Decided:** session 06 · **Status:** settled

`index.css` has to `@import "./themes.css"` at the top — CSS permits `@import`
nowhere else — and then declares Ledger's values on a bare `:root` so a theme
that forgets a token degrades instead of breaking. But `:root` and
`[data-theme="x"]` have **identical specificity**, so the later block wins, and
the later block is always the fallback. Every one of the six themes silently
resolved to Ledger: the attribute was set, the choice was stored, the swatch
highlighted, and not one token changed.

Every theme block is therefore written `:root[data-theme="x"]`, which is (0,2,0)
and beats the fallback. **Never flatten those selectors back.** The reasoning is
written into the top of `themes.css` as well as here.

The wider lesson, which cost this session an hour to learn and is worth more
than the fix: **a control that visibly responds is not evidence that anything
downstream of it happened.** Session 05 checked the theme switcher by watching
the swatch highlight. Four lines of `getComputedStyle` settle it properly.

### D-036 — Chart colours are read from the live tokens, never mirrored by hand
**Decided:** session 06 · **Status:** settled · supersedes the Recharts note in `ui-design-language.md` §2

Recharts needs concrete colour strings, so its palette used to be a hand copy of
Ledger's tokens at the top of `Dashboard.jsx`, with a comment telling future
sessions to keep the two in step. That is fragile with one theme and simply
wrong with six: it drew a terracotta line across Blueprint's electric blue, and
on both dark themes the axes were a light-theme grey that vanished into the
card.

`lib/theme.js` now exposes `chartPalette()` and `useChartPalette()`, which read
the tokens back out of the document, with a `MutationObserver` on `data-theme`
so charts re-colour **live** when the theme is switched with a dashboard open —
which is exactly what a demo does.

### D-037 — Route reachability is derived from the server's navigation tree
**Decided:** session 06 · **Status:** settled

Typing `#/payroll` as an HR Manager rendered the Payruns screen: empty table,
"0 records", a permission error underneath. It looked broken rather than
refused.

The guard in `App.jsx` deliberately keeps **no second copy of the capability
table**. It reads the navigation tree `/api/auth/me/` has already pruned for
this account: a menu the account cannot use is absent (D-028), so a route absent
from that tree is a route it may not open. This is presentation, not
enforcement — the server 403s regardless.

One carve-out, and it is a rule rather than an exception: a **detail** route can
be reachable where its **list** is not, when the server scopes the resource to
the caller. `/payslips` is the operator's index; `/payslips/68` is one record,
and the queryset narrows to the caller's own employee. Without this the Open
button on My Payslips refused the very employee it was built for.

### D-038 — Demo-only affordances compile out of a production build
**Decided:** session 06 · **Status:** settled

The five one-click role chips on the login screen are the fastest way to switch
persona on stage and plainly wrong in a shipped product. They are gated on
`import.meta.env.DEV`, so `npm run dev` — which is how the demo runs — keeps
them and `npm run build` removes them. The email and password prefill is gated
the same way, so a production build opens on empty fields.

This is the general answer for "useful in the demo, wrong in the product":
neither delete it nor ship it, compile it out.

### D-039 — Screen copy states the effect and does not argue for it
**Decided:** session 06 · **Status:** settled · refines `ui-design-language.md` §5

§5 says write labels, not explanations, and both Profile and Security argued
with the reader — "an unlocked laptop should not become a permanent account
takeover", "a clock you can punch from your sofa is not attendance".

The test now applied: **keep every fact the user cannot otherwise know, drop the
justification.** "Your current password is required. Changing it signs out every
other session." keeps both consequences and loses the sermon. Security's
switches keep their one-clause effects, because the effect of a security switch
is invisible and expensive to guess wrong.

The reasoning that was cut is not lost — it lives in the docstrings of
`accounts/security.py` and `capabilities.py`, which is who it was written for.

### D-040 — Git history is left exactly as it is
**Decided:** session 06 · **Status:** settled · **the user's own decision, asked and answered**

Session 04 left an open question about removing Claude's commits. Every commit
is authored by one of the three teammates; exactly one (`12a632f`, the root
scaffold) carries a Claude co-author trailer, and that trailer is why `claude`
appears in GitHub's contributor list.

Removing it means rewriting ~120 commits and force-pushing, which breaks the
other teammates' clones. Both operations are denied at tool level in
`.claude/settings.json` by design. The user was asked directly and chose
**"Leave history alone."** Do not reopen this.


---

### D-041 — The HR Payroll User reads payroll and writes nothing

**Decided by:** Michael, session 07 · 2026-09-06 · at the user's instruction

Nine capabilities, all reads: employees, contracts, attendance, leave,
allocations, payruns, payslips and the two dashboards. No contract wage, no
attendance correction, no leave approval, no employee add/edit/delete, no
payrun create/compute/validate/pay, no configuration of any kind.

**Rationale.** PRD 3.2 grants this role "all HR Manager permissions plus CRU on
Payruns and Payslips". That single grant lets one login raise a wage, approve
the leave that offsets it, correct the attendance behind it, and then compute
and validate the payrun that pays it — every input to a payslip and the payslip
itself, unwitnessed. The role's actual job is checking a run somebody else
produced, and checking needs reading, not writing.

Own-scope self service is untouched, because it lives in `BASELINE` rather than
in any role: this person still punches their own clock, books their own leave
and reads their own payslip.

**Deliberately narrower than the PRD.** Recorded so nobody "fixes" it back.

---

### D-042 — HR Manager and Payroll Manager are siblings, not a ladder

**Decided by:** Michael, session 07 · 2026-09-06 · at the user's instruction

Neither role's capability set contains the other's.

* **HR owns people** — the employee record and the contract on it, hiring and
  offboarding, leave decisions and allocations, attendance corrections, and the
  HR configuration those depend on (schedules, leave types, the reference
  catalogues).
* **Payroll owns the payrun** — create, compute, validate, pay, delete, and
  nothing that feeds into it.

Only the Admin holds both sides. That is now what makes an Admin an Admin, and
`_ADMIN` is written as the explicit union of the two so it cannot silently lose
a capability when either side is narrowed.

**Rationale.** The PRD stacks the five roles so each contains the last, which
puts the person who signs the payrun in charge of every number it consumes.
Splitting on *subject* rather than *seniority* is the standard control, and it
is the one a judge recognises.

**Consequence to know:** the Payroll Manager can no longer set a wage. Wages
live on contracts, contracts are part of the employment relationship, and that
is HR's.

---

### D-043 — Salary structures and rules are readable by payroll, writable only by the Admin

**Decided by:** Michael, session 07 · 2026-09-06 · at the user's instruction

Both payroll ranks read them; neither writes them.

**Rationale.** A salary rule is the formula that turns a wage into a payslip, so
writing one is deciding pay just as surely as setting the wage is. Leaving it
with the Payroll Manager would let one person add a rule and then run the payrun
that applies it. Reading stays, because a payrun cannot be checked against rules
that cannot be seen.

This is the widest departure from PRD 3.2, which gives the Payroll Manager full
CRUD here. It is deliberate.

---

### D-044 — An account holds exactly one role

**Decided by:** Michael, session 07 · 2026-09-06 · at the user's instruction

`UserSerializer.validate_role_ids` refuses a second role on create and on
update. The form shows radios, not checkboxes.

**Rationale.** The mockup's access note says "one or more roles", and
`capabilities_for()` was built to union them. That was defensible while the
roles formed a ladder. Under D-042 they are siblings, so holding both manager
roles is not a bigger role — it is both jobs at once, which is exactly what the
separation of duties exists to prevent.

**What did not change.** The link is still many-to-many and the union still
runs. The matrix must stay correct for any set it is handed, including rows
written before this rule. Only the assignment path is capped, so relaxing this
later is one validator.

**Note:** an account may still hold *no* role, which yields BASELINE only.

---

### D-045 — Breadth of read is decided by a read capability, never by a write flag

**Decided by:** Michael, session 07 · 2026-09-06

Six querysets decided who may see everyone's rows by testing `can_manage_hr`,
which is really `EMPLOYEE_WRITE`; the payslip queryset tested `can_run_payroll`,
which is `PAYRUN_WRITE`. They now test `EMPLOYEE_READ_ALL`, `CONTRACT_READ_ALL`,
`ATTENDANCE_READ_ALL`, `TIMEOFF_READ_ALL`, `ALLOCATION_READ_ALL` and
`PAYSLIP_READ_ALL` respectively.

**Rationale.** Asking a write question to decide a read meant a role could not be
made read-only without also being made blind. Making the Payroll User read-only
silently narrowed it from 61 payslips to its own 3 — caught only because the
audit grew a READ BREADTH section. Any future narrowing hits the same trap
unless the question matches the answer.

---

### D-046 — `seed --flush` is what "a known demo state" means, so it resets everything

**Decided by:** Michael, session 07 · 2026-09-06

The flush now also deletes the `SecuritySetting` singleton and every
`NetworkPolicy`, letting the row be recreated at model defaults.
`audit_permissions.py` sweeps the records its write probes create.

**Rationale.** Security settings are one row that no model in the flush list
touched, so they survived every reseed. Once `probe_forms.py` and
`smoke_api.py` had exercised the security screen, the demo opened on "Sign-in is
restricted to 0 permitted networks" and "Sessions are bound to the address they
were opened". The first only reads alarmingly; the second signs everybody out
the moment the machine changes network, which on demo day is the gap between
venue wifi and a phone hotspot.

Running the harnesses immediately before presenting is now safe.

---

### D-047 — Seeded attendance follows each contract's working schedule

**Decided by:** Michael, session 07 · 2026-09-06

`_attendance` reads the employee's contract's schedule lines for the weekdays
they work and the hours they work, instead of generating Monday-to-Friday at
eight hours for everyone. Overtime is measured against the person's own
scheduled day rather than a flat 8.5 hours.

**Rationale.** The part-time contract is 20 hours over four days and the seed
produced five eight-hour days: 23 worked against 19 expected, roughly 44 hours
against a 20-hour contract. Worked days exceeding expected days is incoherent on
its face, and it undercuts the two things this area is graded on — the derived
weekly hours of graded rule #2, and attendance feeding worked days (D-002 #1).

**Figures moved.** Attendance 1746 → 1731; February net ₹15,58,667.87 →
₹15,58,320.41. **December and January are unchanged**, so the demo's
Dec < Jan < Feb evidence is intact. `core/tests.py` pins the new numbers and now
also asserts the invariant rather than the number.

---

### D-048 — A screen whose subject is "mine" states its scope rather than inheriting it

**Decided by:** Michael, session 07 · 2026-09-06

`MyPayslips` asks for one employee by id. `useResource` accepts a null path
meaning "do not fetch".

**Rationale.** The screen relied on the server's queryset to narrow it, and said
so in a comment that claimed it "would show nothing extra even if it asked for
it". That only holds from an Employee's seat: the three roles holding
`payslip.read.all` are never narrowed, so each saw all 61 payslips in the
company under the heading "My payslips — every period you have been paid for".
Not a leak, but the page stated something false about whose money it was.

The general rule: **inherited scope is invisible scope.** If a screen's whole
subject is own-scope, it says so.

---

### D-049 — The wordmark's prominence comes from size, weight and a rule — not colour

**Decided by:** Michael, session 07 · 2026-09-06

18px at weight 700 against 13px navigation, fenced with a hairline that takes
`--topbar-border`.

**Rationale.** `ui-design-language.md` rule 2 says colour carries meaning or it
is warm neutral, never decoration, and rule 3 says hairlines, not shadows,
outside floating layers. A tinted chip or a glow behind the mark would be louder
and would spend something the palette reserves for state. The typographic route
gets the same prominence honestly, follows all six themes, and keeps the bar at
46px.

---

### D-050 — `seed --flush` resets the audit trail too

**Decided by:** Franklin, session 08 · 2026-09-06

`AuditLog` and `LoginAttempt` are deleted by `seed --flush`, alongside the
security settings row that D-046 already added.

**Rationale.** Both tables sit below everything else in the dependency graph, so
nothing cascaded to them and they survived every reseed — the same way the
settings row used to. `AuditLog` holds its actor with `SET_NULL`, so a flush
turned every row into an orphan naming an account that no longer existed. The
Admin lands directly on that table, and its opening state read *"User created —
admin@oxp.com created perm.probe@oxp.com"*, a refusal counter of 1, and fourteen
sign-ins nobody made. All harness residue, on the demo's first admin screen.

`LoginAttempt` is not merely cosmetic: it is what `_recent_failures` counts to
decide a lockout, so a run of failed sign-ins could leave a demo account locked
with no supported way to clear it.

Both are append-only by design and neither is reconstructible, so they are
dropped **only here**, where "a known demo state" is the entire purpose of the
command. The empty table is not a loss: the demo's own sign-ins repopulate it
within seconds, so every row a judge reads is something that just happened in
front of them.

---

### D-051 — The register opens on the newest *finished* run, and the server says which

**Decided by:** Franklin, session 08 · 2026-09-06

`Reports.jsx` reads `default_period` from `/api/dashboard/filters/` instead of
taking `payruns.rows[0]`.

**Rationale.** This is D-034 a second time, in a screen that was missed. The
rows are ordered `-period_start`, so "the first row" is the newest run — which
is the off-cycle correction holding a single payslip. The payroll register
therefore opened on a one-line report instead of February's twenty.

D-034's own general rule applies unchanged: *when a screen and its API both
decide the same thing, they will eventually decide it differently.* The server
already names the answer; the screen now reads it, and falls back to the newest
visible run only if the call fails or names a run this account cannot see.

---

### D-052 — Content-Disposition is exposed to the browser

**Decided by:** Franklin, session 08 · 2026-09-06

`CORS_EXPOSE_HEADERS = ["Content-Disposition"]`.

**Rationale.** The register export builds a per-run filename and sends it as
`Content-Disposition: attachment; filename="register-February-2026.csv"`.
`payrunRegister` reads that header to name the download, and its comment says
so. It had never once succeeded: only the seven CORS-safelisted response headers
are readable from JavaScript cross-origin, the frontend is a different origin
from the API, and `Content-Disposition` is not one of them. Every export fell
through to the `"register.csv"` fallback, so exporting three months produced one
name three times and the files collided.

The server was right and unheard. Verified in the browser afterwards: three runs,
three distinct filenames.

---

### D-053 — Submitting a leave request is the act of submitting it

**Decided by:** Franklin, session 08 · 2026-09-06 · *reported by the user*

`TimeOffRequestViewSet.perform_create` saves with `state=TO_APPROVE`. The screen
treats `DRAFT` and `TO_APPROVE` alike as undecided.

**Rationale.** A request created through the API took the model default `DRAFT`,
and **nothing anywhere advanced it**: there is no submit or confirm action on the
viewset, `TO_APPROVE` appeared nowhere in `timeoff/api.py`, and the screen
offered Approve and Refuse only on `TO_APPROVE`. So every request an employee
raised landed in a state nobody could act on and the requester could not leave.
It read as pending and was a dead end.

No harness caught it because the seeded rows set their state directly on the
model, so they were born `APPROVED` or `TO_APPROVE` and the approval queue looked
healthy as long as nobody actually submitted anything.

There is no draft-and-send-later flow to preserve — the form's button says
Submit and the state filter offers no Draft — so creation lands in the queue.
`DRAFT` stays in `STATES`, and the screen still acts on it, so any row written
before this remains decidable rather than stranded.

---

### D-054 — A workflow state is not an input field

**Decided by:** Franklin, session 08 · 2026-09-06

`state` is read-only on `TimeOffRequestSerializer`. `Allocation.state` stays
writable, deliberately.

**Rationale.** `state` was writable, and creating a request is the one write an
ordinary employee always has. PATCH and the `approve` action were already
refused to them, so the create payload was the way through: `POST {"state":
"APPROVED"}` returned 201 with state `APPROVED` — leave granted outright,
consuming the requester's own allocation and, for an unpaid type, moving their
own payslip. Confirmed over HTTP before the fix and again after.

The state moves only through `approve()` and `refuse()`, both of which require
`timeoff.approve`.

The asymmetry with `Allocation` is intentional and worth stating: an allocation
is a **grant raised by HR** under `allocation.write`, so setting its state is not
an escalation, and two harnesses create allocations in a chosen state. The
question is never "is this field writable" but "who writes it, and does writing
it grant them something".

---

### D-055 — "Awaiting you" means awaiting *you*

**Decided by:** Franklin, session 08 · 2026-09-06 · *reported by the user*

The HR dashboard's queue excludes the viewer's own employee record, and the KPI
counts the same set.

**Rationale.** `ProfileChangeRequest.approve()` has always refused a reviewer
deciding a change to their own record — an HR Manager who could approve their own
bank-account change would make the control decorative. The dashboard was not
applying the same rule when building its queue, so an HR Manager's own pending
request appeared in the panel headed *"awaiting you"* beside an Approve button
whose only possible outcome was a 400.

That is the inverse of PRD-3.1: never offer a control the server will refuse. The
requests table now says **"Another approver"** on your own row instead of
offering buttons.

**Excluded from the queue is not hidden.** The full list is untouched — HR still
reads every request including their own, and sees it sitting there pending.

---

### D-056 — A screen only reachable from inside "My profile" is a screen nobody finds

**Decided by:** Franklin, session 08 · 2026-09-06 · *reported by the user*

**Employees → Change Requests** (`/profile/requests`), gated on `PROFILE_APPROVE`.

**Rationale.** The user reported that HR never received profile-change approvals.
They did — the queue worked — but its only door was a tab inside **"My profile"**,
a personal-scope screen that for the admin login opens by announcing there is no
profile to show. So the two roles that may decide these requests had no way to
find them, and requests sat pending because nobody knew where to look.

The screen, the route and the capability all already existed. Only the door was
missing. Adding it to the server-side navigation manifest means the entry appears
for exactly the roles holding the capability — verified as present for the Admin
and the HR Manager, absent for both payroll ranks and the Employee.

**The general rule:** a working feature with no entrance is indistinguishable
from a broken one, and will be reported as broken.
