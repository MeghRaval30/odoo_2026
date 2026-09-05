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
