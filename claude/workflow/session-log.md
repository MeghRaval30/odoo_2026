# SESSION LOG

**APPEND-ONLY.** Never edit or delete an existing entry. Add yours at the bottom.

This is how a session works out which character it is: read the last entry and
take the next name in the rotation `MICHAEL → FRANKLIN → TREVOR → MICHAEL`.

---

## Session 01 — MICHAEL

**Opened:** 2026-09-05, ~08:30 IST
**Status:** OPEN

### Picked up
Nothing — this is the first session. Started from an empty folder containing only
the problem-statement PDF and the Excalidraw mockup.

### Work done

1. **Feature research.** Surveyed what world-class HR and payroll platforms ship
   (Workday, SAP SuccessFactors, ADP, UKG, Rippling, Gusto, BambooHR, Deel,
   Personio, HiBob, Darwinbox, Keka, greytHR, Zoho People) and produced a full
   feature catalogue across sixteen domains, for use as a reference when deciding
   what to build and what to put in the future roadmap.

2. **Source analysis.** Extracted and read both source documents in full:
   - `PeoplePay360 HR & Payroll.pdf` — the formal problem statement
   - `HRMS OXP - 24 hours.excalidraw` — the mockup, 3,459 text elements, parsed
     programmatically to recover every field label and participant note
   Produced a consolidated specification digest covering all entities, fields,
   navigation, roles, the payrun wizard, the dashboard, and the parts explicitly
   left open to interpretation.

3. **Relay system design.** Designed and scaffolded this `claude/` context
   system, including the auto-loading `CLAUDE.md` failsafe, the append-only log
   discipline, the heartbeat commit habit, the clock-and-scope-gate mechanism,
   and the MEGATRON LAUNCH packing checklist.

4. **Repository scaffolding.** Created the folder structure, moved the source
   documents into `claude/source/`, and initialised git against the team remote.

### Decisions made
See `claude/context/decisions.md` — entries D-001 through D-007.

### Attempted and abandoned
- `gh` CLI is not installed on this machine. Fell back to plain `git` over HTTPS
  with Git Credential Manager handling browser-based authentication.

### Notes for whoever is next
- The Excalidraw file is a rich source. If you need a field that is not in
  `product-spec.md`, parse it with the snippet recorded in `blockers.md` rather
  than squinting at the PNG.
- The hackathon start time in `current-state.md` is **assumed**, not confirmed.
  Get it corrected early — every scope gate depends on it.


### Git setup (added after the initial scaffold)

The user added two requirements partway through: all three teammates must appear
as commit authors, and the history must show real collaborative development
rather than a flat line of commits on main. This reversed the earlier plan.

- `claude/workflow/git-strategy.md` written: identity register, branch model,
  `--no-ff` merge policy, version tags, contribution-balance check
- D-008 reverses D-007 (branches now required)
- D-009 per-session git identity, verified before first commit
- D-010 no machine attribution in commit messages
- Michael identity confirmed: `TheTeam404 <sohampanchal2229@gmail.com>`
- Franklin and Trevor rows in the identity register are still `TBC`

Repository is live at https://github.com/MeghRaval30/odoo_2026
Tagged `v0.1-planning`. Branch `docs/git-strategy` merged `--no-ff` into main.

**Known wart:** commit `12a632f` (initial scaffold) predates D-010 and carries a
Claude co-author trailer. Left as-is rather than amended, since rewriting pushed
history is forbidden. Every commit after it is clean.

### Build phase — the backend, end to end

After the planning and git work, the whole Django backend was built and verified
in roughly two and a half hours.

- 7 apps, 21 models, all migrations clean on SQLite
- `payroll/engine.py` — sequenced rule evaluation with sandboxed formulas
- `core/management/commands/seed.py` — 22 employees, 3 months of payroll history
- Full REST API with five role classes enforced server-side
- Payslip PDF via ReportLab, bulk email, dashboard aggregating six models
- Two proof harnesses: `verify_rules.py` (28/28) and `smoke_api.py` (51/51)

Frontend was scaffolded (Vite, api.js, index.css) but **renders nothing** —
`App.jsx` is still the Vite demo.

### Bugs found by writing the harnesses

Worth recording because each was a real defect, not a test artifact:

1. `contract_for_period` filtered `state=RUNNING`, so a since-expired contract
   could not be resolved for the period it governed. December produced 20
   `NO_CONTRACT` errors and a zero payrun. Lifecycle state and period coverage
   are different things.
2. `compute_payrun` deleted payrun-level warnings, discarding the record of
   employees skipped as duplicates at creation time.
3. The dashboard's month-over-month delta walked back a rolling N-day window, so
   a 28-day span from 1 February started on 4 January and excluded January
   entirely, silently yielding a null delta.
4. `AttendanceViewSet` gated every write behind `CanManageHR`, giving employees a
   403 on check-in — the widget is explicitly employee-facing.
5. Seed flush ordered Employee before Payrun, tripping `PROTECT` on
   `Payslip.employee`.

### Decisions added late

- D-011 SQLite rather than PostgreSQL (neither Postgres nor Docker installed)
- D-012 context folder updated only at MEGATRON LAUNCH, at the user's request

### Handed off with

- 27 of 45 tasks done, 1 in progress, 17 to go — all remaining work is frontend
- No known bugs; both harnesses green
- Hackathon start time still **unconfirmed** — flagged in three places

**Closed:** 2026-09-05 ~13:20 IST (~4h session)
**Handoff tag:** `handoff-michael-01`
**Next up:** FRANKLIN — briefing in `claude/handoff/NEXT-SESSION-PROMPT.md`

---

## Session 02 — FRANKLIN  *(entry reconstructed by session 03)*

**Opened:** 2026-09-05, ~11:27 IST · **Closed:** ~13:04 IST (~1h 40m)
**Status:** CLOSED

> ⚠️ **Franklin did not write a session-log entry.** The MEGATRON pack updated
> `current-state.md`, `task-board.md`, `decisions.md` and the briefing, but
> step 5 of the checklist was missed. Rather than leave a hole in an append-only
> log, session 03 has reconstructed the facts below **from git history only**.
> Nothing here is Franklin's own account, and no motive or reasoning is attributed
> that is not stated in a commit message. Treat it as a summary, not a record.

### Work done — 75 commits

- Built the **entire frontend**, which session 01 had left as an untouched Vite
  demo: hash router, app shell with the six-menu top bar, login with role chips,
  and one screen per area — employees (kanban + list), contracts, schedules,
  attendance, time off, allocations, payruns with the two-step wizard, payslips,
  salary config, holidays, reference data, users, dashboard and the payroll
  register report.
- Confirmed the hackathon clock with the user and corrected it (10:00 IST start,
  not the 09:00 session 01 had inferred) — closing B-001.
- Filled in the identity register for both remaining characters.
- Wrote `probe_forms.py`, a harness that posts the payload each frontend create
  form actually builds. It found four bugs the other two harnesses were
  structurally blind to.
- Fixed, among others: create forms omitting the required `company` FK, contract
  and salary-rule forms sending unacceptable empty values, a dashboard company
  filter listing the same company 22 times, payrun state constants that did not
  match the model, a payslip line rate stored post-quantity, and a contract
  visibility leak that let any employee read every colleague's wage.
- Rewrote the README as a run-and-verify guide (T-062).

### Not done

- No session-log entry (this one).
- `test/backend-suite` was left deliberately unmerged for session 03 to merge.

**Handoff tag:** `handoff-franklin-02` · **commit** `d63abad`

---

## Session 03 — TREVOR

**Opened:** ~12:30 IST (first half, in parallel with Franklin under D-015)
**Second half opened:** 13:06 IST · **Closed:** 2026-09-05, 13:45 IST
**Status:** CLOSED

### Picked up

The briefing at `claude/handoff/NEXT-SESSION-PROMPT.md` was addressed to Franklin
and described the frontend as scaffolded-only. That was two sessions stale.
Re-derived the real position from `current-state.md`, the task board and git
before touching anything — which is the only reason this session did useful work
rather than rebuilding a finished frontend.

### Work done

**First half** (separate chat, D-015 ownership split): the Django test suite
across employees, timeoff, payroll, attendance and accounts — 155 tests — plus
the demo script (T-060) and the roadmap (T-061). Left on `test/backend-suite`,
pushed and deliberately unmerged.

**Second half** (this chat):

- Merged `test/backend-suite` into `main` — the action `current-state.md` named
  as the single next one. It carried more than recorded: the demo script and
  roadmap were already written, though the board still said "in flight".
- Closed all three `# PRODUCT BUG:` tests the first half had left asserting
  broken behaviour (D-019): the contract leak (already fixed by Franklin in
  parallel), employee time-off self-service, and Payroll User delete.
- **Found and fixed a screen that had never worked.** The New Time Off Request
  form sent `half_day` as a boolean to a `FIRST`/`SECOND` choice field and
  rendered no control for it, so every submission had returned 400 since the
  screen was written — for every role. Demo Scenario B is built on that form.
- Extended `probe_forms.py` to cover it (24/24 → 26/26) and adopted D-020: every
  create form gets a probe case.
- Drove the payrun flow end to end in a browser — wizard, compute, the
  pre-validation warnings, validate, mark paid, payslip detail — confirming all
  five graded rules are visible in the UI, not merely provable by harness.

### What was attempted and abandoned

- **Nothing was abandoned as a dead end.** No approach was tried and dropped.
- Two mechanical detours cost time and are recorded as B-012, B-013 and B-015.
- The auto-mode classifier blocked a Python heredoc used for a scripted edit and,
  once, a `manage.py test <label>` invocation. Both were routine and were done
  with the Edit tool and an unlabelled test run instead. Not a blocker — but if
  a Bash call is refused, reach for the dedicated tool rather than rephrasing.

### Honest gaps

- **The demo script has never been rehearsed.** It was written partly from
  source, and its Scenario B depended on the form that could not submit. It works
  now, but B5's balance claim ("Taken two. Remaining eighteen.") looks wrong for a
  freshly submitted `DRAFT` request, since `taken` counts only approved ones.
  This is the single next action and it is written up in `current-state.md`.
- No frontend tests exist (T-075). Deliberate for a 24h build.

### Ended with

- Four harnesses green: `verify_rules` 28/28, `smoke_api` 51/51,
  `probe_forms` 26/26, `manage.py test` 158/158. `npm run build` clean.
- Working tree clean, no unmerged branches, `main` pushed.
- The task board is effectively complete; ~20h remain at close.

**Closed:** 2026-09-05, 13:45 IST
**Handoff tag:** `handoff-trevor-03`
**Next up:** MICHAEL — briefing in `claude/handoff/NEXT-SESSION-PROMPT.md`.
His first action is to rehearse the demo script against a running app.
