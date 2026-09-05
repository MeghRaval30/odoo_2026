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

**Closed:** _(pending)_
**Handoff SHA:** _(pending)_
**Next up:** FRANKLIN
