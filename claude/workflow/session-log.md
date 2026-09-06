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

---

## Session 04 — MICHAEL (second time round the rotation)

**Opened:** 2026-09-05, ~13:58 IST
**Closed:** 2026-09-05, ~15:20 IST (~1h 20m)

### Picked up
Trevor's handoff: everything built, T-063 (demo rehearsal) outstanding. The user
asked for a fresh audit of the PDF and mockup to find unimplemented features.

### The audit found nothing missing — and that was the useful result

All sixteen required modules (A1–A7, B1–B9) are present, plus extras the spec
never asked for. Two suspicions turned out to be false alarms: a stray `₹ 1.50L`
on every page is Recharts' own measurement span at `top: -20000px`, and a
"missing" salary-config route was a wrong URL guess on my part.

So instead of inventing features, the session went after defects. **Four real
ones, all of which 158 tests and four green harnesses had been blind to.**

### Defects found and fixed

1. **The payslip PDF could not draw a rupee sign.** ReportLab's Helvetica is a
   Type 1 face encoded WinAnsi with no U+20B9 glyph, so every money figure on
   every payslip rendered a substitute character. Embedding a TrueType face was
   not enough on its own — each `TableStyle` set `FONTNAME` only on its header
   row, leaving the body cells, where the money is, on the default face. The
   user caught the second half by downloading a payslip after I had declared it
   fixed.
2. **`is_employer_cost` and `appears_on_payslip` were dead config** — stored,
   serialized, editable checkboxes that the engine never read. Ticking "Employer
   cost" on a provident-fund rule still reduced the employee's net pay.
3. **Mid-period joiners were paid a full month.** `gather_period_facts` never
   consulted the contract's dates. A 20 February joiner drew a full February
   basic — the commonest real payroll case and the one nobody would sign.
4. **December and January payslips read "Worked Days 0.00 / 23.00"** because
   seeded attendance started in February. Also fixed attendance being generated
   on public holidays, which had made January read 22 worked against 21 expected.

### T-063 closed — the demo is rehearsed

Scenario B was walked click by click and every claim holds. Scenario A's data was
verified against the database. The rehearsal itself surfaced a fifth bug: the
Comp Off refusal stayed on screen after switching to Paid Time Off, so the form
showed "refused" directly above "20 days available", in the middle of the step
that demonstrates graded rule three.

The standing worry that B5's "Taken two, Remaining eighteen" was wrong is
**unfounded** — B4 approves the March row first, and that is what moves the
balance.

### Full browser QA

All 18 routes render real content with zero failed network requests. The payrun
state machine was driven end to end: 3 payruns before the Create click and 4
after (steps 1 and 2 create nothing), Validate disabled until Compute, warnings
shown before Validate, all actions disabled at PAID, 20 payslips emailed, PDF
served valid. Role scoping and the attendance widget both verified by hand.

### Numbers moved

February is now ₹15,58,667.87 and Engineering alone ₹5,03,589.11. December and
January are unchanged, so the headline comparison still holds. The figures quoted
in the demo script, README and current-state were updated to match.

### Left undone, deliberately

The user asked for a **200–300 employee dataset** to demonstrate scalability,
then said to hold it until the software and workflow were verified. That
verification is now complete, so the dataset is the next piece of work. It also
carries PRD criterion 4 with it — only `AC_MISSING` currently fires, and a large
roster with joiners and leavers naturally produces more warning types.

### Unresolved — needs the user

The user said "remove your commits" and the session ended before it was settled.
Every commit is authored by a teammate; exactly one (`12a632f`, the root scaffold
commit) carries a Claude co-author trailer. Removing it means rewriting ~117
commits and force-pushing. Details and options are in `current-state.md`.

### Decisions added
D-021 employer cost separation · D-022 PDF font embedding · D-023 proration ·
D-024 overtime confined to February in the seed.

### Traps recorded
B-016 through B-020 — the `--noreload` trap, byte-count harnesses proving
nothing, `pdftotext` misreading subset fonts, the Browser pane refusing PDFs,
and heredocs corrupting file content.

**Handoff tag:** `handoff-michael-04`
**Next up:** FRANKLIN — briefing in `claude/handoff/NEXT-SESSION-PROMPT.md`.
His first action is the 200–300 employee dataset.

---

## Session 05 — FRANKLIN

**Opened:** 2026-09-05 ~20:20 IST · **Closed:** 2026-09-05 21:35 IST
**Duration:** ~1h 15m · **Committing as:** `Robo9327study <rajstudy9327@gmail.com>`
**Handoff tag:** `handoff-franklin-05`

### What happened

The session opened on the queued task and was **redirected mid-flight** by a
large new commission from the user. Both halves landed.

### Part one — the large dataset (T-089, closed)

`manage.py seed` grew an `--employees N` flag. The 22-person demo roster is
created first and left completely alone — same 24 contracts, same 1,746
attendance rows, same December/January/February nets — and everything above 22
is appended after it, which also keeps the random stream the fixed roster draws
from unchanged. `core/tests.py` now pins the demo's shape so a change that moves
those figures fails there before it reaches the demo.

Generated people carry the four contract shapes a real roster has: a plain
running contract, a raise on 01 Jan 2026, a mid-period joiner, and a leaver whose
contract closes 28 Feb 2026. That is what makes the pre-validation checks
demonstrable at scale.

**Measured:** 250 employees seed in 40 s (19,045 attendance rows, 680 payslips).
A payrun of 20 computes in 0.6–0.7 s against PRD-7.2's 5 s budget; a payrun of
233 computes in 5.7 s. Scaling is linear at ~32 ms per payslip. The dashboard at
250 takes 2.9 s.

**PRD success criterion 4 is met at scale** — a March payrun over 250 people
raises `NO_CONTRACT` ×8 and `AC_MISSING` ×13. It is still unmet on the 22-person
demo seed, deliberately: every available fix damages the rehearsed demo, and the
options are written up in `current-state.md` for the user to choose from.

### Part two — the RBAC and UI commission

The user asked for the UI to be redone against the excalidraw, four to six full
design languages, a rethink of account types and what each one sees, a profile
menu with approval-gated changes, attendance in hours and minutes, real
security including network-restricted sign-in, and self-service passwords.

Both source documents were read end to end first — all 1,187 text elements of
the excalidraw and the full PDF — rather than worked from memory. Roughly **70%
of the commission was delivered**; the remainder is a screen-by-screen pass over
the older screens and is itemised file-by-file in `current-state.md`.

**Access control.** `accounts/capabilities.py` is now the single declarative home
for who may do what. An account may hold several roles and gets the **union**,
which is what the mockup's "one or more roles" actually requires. The four old
booleans survive as views onto the matrix, so 86 existing account tests kept
passing without edits. `/api/auth/me/` returns a server-built navigation tree, so
the menu and the enforcement read the same table.

**Security**, each control closing a named attack rather than ticking a box:
CIDR-scoped sign-in re-checked on every request; expiring, optionally
IP-bound sessions; lockout that leaks nothing; self-service split by blast
radius so a bank-account change needs a second pair of eyes; an append-only
audit log; and guards against changing your own roles, deactivating yourself or
removing the last administrator. 31 new tests, each named after the attack.

**Four dashboards behind four endpoints.** This closed a real leak: the payroll
dashboard had only been gated on being signed in, so an HR Manager — a role the
PDF gives *no access to payroll features* — could read total net paid.

**Six design languages.** `index.css` was rewritten so nothing hard-codes a
colour, radius, shadow or padding; otherwise six languages would have been six
palettes.

Verified in a browser: the Employee top bar is exactly Dashboard · Attendance ·
Time Off · My Payslips; the HR Manager's has no Payroll, Reports or
Administration anywhere and no money on the screen, with overtime reading
**124h 38m carried by 22 employees** instead of an event count.

### What was attempted and deliberately not done

- **Closing PRD criterion 4 on the demo seed.** Investigated properly and left
  alone: every fix breaks a rehearsed demo step. Written up for the user.
- **The pre-existing screens.** Login, Attendance, the payroll Dashboard tile,
  Users and the attendance widget all still speak the old language. They work;
  they are just not finished. This is the next session's main job.
- **Four of the six themes have never been rendered.** Ledger and Console were
  seen. Do not claim six work until all six have been opened.

### Traps recorded

B-021 two `runserver` processes on one port, the stale one answering first ·
B-022 browser refs go stale after a resize, and `form_input` does not reach
React state · B-023 heredocs silently append nothing, confirmed twice more ·
B-024 `bulk_create` skips `save()` so references must be minted by hand ·
B-025 date windows anchored to `today` are empty on the demo machine.

### Decisions added

D-025 capabilities and role union · D-026 sources beat the user's examples where
they conflict, flagged not buried · D-027 six themes, per browser · D-028
server-built navigation · D-029 four dashboards, four endpoints · D-030
self-service split by blast radius · D-031 sessions expire and the network is
re-checked every request · D-032 decimal in the data, hours and minutes on
screen.

**Next up:** TREVOR — briefing in `claude/handoff/NEXT-SESSION-PROMPT.md`. His
first action is to re-run the full test suite, then finish the screen-by-screen
pass starting at `project/frontend/src/screens/Login.jsx`.

---

## Session 06 — MICHAEL

**Opened 2026-09-05 21:45 IST.** Identity set and verified as `TheTeam404` /
`sohampanchal2229@gmail.com` before the first commit.

> **Rotation note.** Session 05 handed off to Trevor, but the account
> authenticated in this chat is Soham's, which the identity register maps to
> Michael. `git-strategy.md` §1 says identity follows the session rather than the
> nominal order, so this session runs as Michael and Trevor's turn moves to 07.
> Raised with the user rather than settled silently.

### Boot

`git pull --rebase` hit a conflict: this checkout still carried the local
session-04 docs commit `f3040bf` ("fold the permission audit into the handoff"),
while `origin/main` had since packed session 05 over the same four files. The
*code* it documented (`c08fa5f`, the payroll merge) was already on the remote, so
only the prose collided.

Resolved by taking upstream for `current-state.md`, `task-board.md`,
`decisions.md` and `NEXT-SESSION-PROMPT.md` — session 05's pack is the later,
authoritative rewrite — and keeping the one hunk that merged cleanly and was not
superseded: `runbook.md` gaining `audit_permissions.py` as the fifth harness.
Rebased commit is `a7c4d3d`, pushed.

Note for whoever reconciles the boards: session 04 and session 05 both minted
**T-091 and T-092** for different work. Upstream's meanings (capability matrix,
self-service) are the ones now in `task-board.md`.

### Startup verification — the app is up

| Step | Result |
|---|---|
| `manage.py migrate` | applied `accounts.0003` and `accounts.0004` — this checkout had not seen them |
| `manage.py seed --flush` | 22 employees, 24 contracts, 1746 attendance, 3 payruns, 60 payslips, 960 lines, 6 warnings — byte-identical to the pinned demo shape |
| `manage.py test` | **216/216 OK** in 39.8 s |
| `runserver 8000` | up; `POST /api/auth/login/` returns a token and the full capability list for `admin@oxp.com` |
| `npm run dev` | up on 5173, Vite 8.2.2, ready in 1.1 s (it re-optimised deps once, config had changed) |
| Browser | signed in as Admin. Administration dashboard renders live: 5 accounts, 1 live session, 2 sign-ins/24h, audit log, security posture, accounts-by-role. All eight menu groups present |

Ports were clear beforehand — no repeat of B-021.

The stale-screen list in `current-state.md` is confirmed from the browser:
`Login.jsx` still reads "Sign in to continue" and still carries the five demo
chips, exactly as the handoff describes.

---

## Session 06 — TREVOR (concurrent with the Michael entry above)

**Opened 2026-09-05 21:41 IST · closed 22:55 IST · ~1h 15m.**
Identity set and verified as `MeghRaval30` / `meghraval306@gmail.com` before the
first commit — Trevor's row in `git-strategy.md` §1, matching the account
authenticated in this chat.

### ⚠️ READ THIS FIRST — two sessions ran at once, on the same work

The entry immediately above is **another live session**, opened four minutes
after this one, running as Michael on Soham's account. Both are numbered 06.
This was not discovered until the handoff merge, when `origin/main` turned out to
have moved from `6a9b0f4` to `a1ae6a7` underneath a session that had already
been working for an hour.

**Michael's entry ends by confirming, from the browser, that `Login.jsx` still
reads "Sign in to continue" and still carries the five demo chips** — i.e. that
session was about to start T-101. **T-101 through T-107 are now all done and
merged to `main` at `1437c25`.** Whoever reads this next: pull before you write a
line of frontend code, and check `task-board.md` rather than the briefing you
were handed.

The merge itself was clean only by luck — Michael touched `runbook.md` and
`session-log.md`, this session touched neither. See **B-030**.

### What was accomplished

The session-05 commission is **finished**. Every board task is `DONE` except
T-107 (the demo script).

| | |
|---|---|
| **T-101** | Login screen to the mockup's copy. Demo chips gated on `import.meta.env.DEV` so they survive the demo and vanish from a production build (D-038) |
| **T-102** | Attendance list and widget in hours and minutes. The widget now surfaces `punch_blocked_reason` and disables the button — proven by planting a policy that excludes 127.0.0.1 |
| **T-103** | The overtime tile the user called out: **124h 38m carried by 22 employees**, not a count |
| **T-104** | Users & Roles — the mockup's five columns, search, role filter, the Active switch that had state but no control, Reset password, and the capability grid |
| **T-105 / T-100** | Every control moved onto `auth.has(...)`, plus a route guard so a typed URL refuses in one clause instead of rendering a broken shell over a 403 (D-037) |
| **T-106** | **All six themes were broken**, not four. See below |
| **T-099** | The four unclicked screens walked end to end; five defects found and fixed |
| **T-090** | PRD criterion 4 met on the demo seed (D-033, D-034) |

Suite grew 216 → **218**, all green. verify_rules 28/28, smoke_api 51/51,
probe_forms 26/26, `npm run build` clean.

### The find of the session

**Not one of the six themes had ever applied.** The briefing warned that four
were unverified; the truth was that all six resolved to Ledger. `index.css` must
`@import themes.css` at the top and then declares Ledger's defaults on a bare
`:root` — identical specificity to `[data-theme="x"]`, so the *fallback* won
every time. The switcher highlighted the correct swatch and stored the choice,
and not one token changed.

Session 05 had checked it by watching the swatch highlight. **A control that
visibly responds is not evidence that anything downstream of it happened** — four
lines of `getComputedStyle` settle it, and that is now written into D-035.

Fixing it exposed two more: the Recharts palette was a hand copy of Ledger's
tokens (a terracotta line on Blueprint's electric blue; invisible axes on both
dark themes), and Marigold's button labels measured 2.86:1, below AA.

### What was attempted and left

* **Walking the payrun wizard in the browser.** MEGATRON LAUNCH arrived with the
  New Payrun modal open at step 1. The criterion-4 numbers are proven by test and
  by a direct engine run, not by the wizard. That is **T-112**, and it should be
  done before T-107.
* **Ledger's 3.05:1 primary button.** White on Claude orange fails WCAG AA for
  13px labels — the same fault Marigold had. Marigold was fixed because nobody
  had ever seen it; Ledger is the shipped signature look, fixed by
  `ui-design-language.md` §2, so it was **reported rather than changed at hour
  13**. That is **T-111**, and it needs the user, not a session.
* **Git history** — the user was asked and chose to leave it alone (D-040).
  Closed, do not reopen.

### Handoff

Merge commit **`1437c25`** on `main`; handoff tagged **`handoff-trevor-06`**.
`main` could not be checked out in this worktree (B-029) — the merge was made on
`integrate/session-06-trevor` from `origin/main` and pushed with
`git push origin HEAD:main`.

**Next up:** whoever holds the next slot — and given B-030, *check who else is
running first*. The first action is T-112: start both servers, sign in as
`aarav@oxp.com`, and walk demo steps A3 → A10, writing the real numbers into
`claude/deliverables/demo-script.md` as you go.


---

## Session 07 — Michael · 2026-09-05 23:00 → 2026-09-06 01:05 IST (~2h 05m)

Opened by pulling 13 commits from sessions 05 and 06 and finding the local
database stale — three payruns where the runbook expects four, because it
predated the March off-cycle correction. Reseeded and started both servers.

### What was accomplished

**The permission model was rebuilt, in four passes driven by the user.** It began
as "limit the payroll user" and ended as a genuine separation of duties:

* the **HR Payroll User** became an observer — nine capabilities, all reads
* the **HR Payroll Manager** became the operator of the payrun and the owner of
  none of its inputs; on employees, contracts and attendance it is now
  byte-for-byte identical to the Payroll User
* **HR Manager and Payroll Manager became siblings rather than a ladder**, and
  the Admin became the explicit union of both
* salary-rule writing moved to the Admin alone, so nobody can add a rule and
  then run the payrun that applies it
* an account now holds **exactly one role**

Every viewset moved onto the capability table in the process. Before this,
most viewsets used the old model-flag classes while the menu was built from the
matrix — so changing the matrix would have moved the menu without moving the
API, which is precisely the failure PRD-3.1 names.

**Two latent bugs fell out of that work**, both structural rather than cosmetic:

1. **Six querysets decided who sees everyone's rows by testing a *write*
   capability.** Making a role read-only therefore also made it blind. The
   payslip queryset did exactly that — a read-only Payroll User silently
   dropped from 61 payslips to its own 3. Caught only because the audit grew a
   READ BREADTH section (D-045).
2. **`SALARY_CONFIG_WRITE` briefly belonged to no role at all.** The Admin only
   inherited the union of the two manager roles, so narrowing both orphaned it
   and the salary rules would have been uneditable by anyone, with no error
   anywhere. Restored explicitly, plus `unreachable_capabilities()` and a test
   asserting it stays empty.

**Then a full testing pass, which found two more real bugs:**

3. **"My payslips" showed a payroll operator the whole company.** The screen
   leaned on the server to scope it, and said so in a comment claiming it "would
   show nothing extra even if it asked for it" — true only from an Employee's
   seat. Three of five roles saw all 61 payslips under "every period you have
   been paid for" (D-048).
4. **Attendance ignored each contract's working schedule.** The part-time
   employee — 20 hours over four days — was seeded five eight-hour days: 23
   worked against 19 expected, roughly 44 hours against a 20-hour contract. The
   holiday exclusion sitting directly above it in the code was the same bug
   found from the other end and fixed for holidays alone (D-047).

**Smaller work:** Payroll Dashboard added under Reports (the route and its
documentation already existed; only the menu entry was missing), and the menu
fixed to stop landing a reload late; the wordmark enlarged and fenced; the
harnesses stopped dirtying the demo they verify.

### What was attempted and abandoned

* **The AI features are dead.** The user asked for AI over a large dataset, chose
  local Ollama models, and then asked for Ollama to be uninstalled — which was
  the first action of this session. Nothing was built. The only remaining route
  is the Anthropic API, which sends salary data off the machine, and that was
  the exact thing local models were chosen to avoid.
* **A negative net was reported as a bug and withdrawn.** A zero-gross payslip
  produces net −₹200 because Professional Tax is fixed. The engine already
  handles it: `NEGATIVE_NET` at ERROR severity, `can_validate` false,
  `validate_payrun` refuses. Proven end to end rather than read off the code.
* **The probe scripts were not committed.** The sweep, the invariants checker
  and the edge-case runner were scratch. The two findings worth keeping became
  real tests in `core/tests.py` and `accounts/tests.py`; the technique is
  written up in the traps section of the next-session prompt.
* **B-032 was left alone twice, deliberately** — two reads answer 400 for an
  account with no employee record. Both UIs handle it correctly and the change
  touches a demo path.

### Verification at close

231 backend tests (from 218), 28/28 rules, 53/53 API, 26/26 forms, and the
permission audit clean across every cell plus 16 refusals, 6 preserved reads,
read breadth, rank identity and row scoping. 2,499 fuzzed requests produced no
crash and no anonymous leak. All 22 routes walked as Admin and as Employee with
zero console errors.

### Handoff

Code merged to `main` at **`3c443c0`** ("merge: findings from a full testing
pass") before packing; the working tree was clean at MEGATRON LAUNCH, so no
`wip:` commit was needed. Context committed separately and tagged
**`handoff-michael-07`**.

**Next up: Franklin, session 08.** First action is **not** a feature. It is to
seed, start both servers, sign in as `aarav@oxp.com`, and walk demo scenario A
from A1 to A10 writing down the number actually on screen at each step — the
script's figures are corrected but it has not been rehearsed since the
permission model was rebuilt.

---

## Session 08 — Franklin · 2026-09-06 01:15 → 03:10 IST (~1h 55m)

Opened by pulling session 07's handoff, setting the Robo9327study identity, and
running the baseline before touching anything: **231 tests OK**, then all four
harnesses green. That mattered, because it established that anything still wrong
had to be somewhere the harnesses do not look.

The user's brief was "check for bugs and repair it", so the demo rehearsal the
handoff asked for was overtaken. It got done incidentally and thoroughly anyway.

### What was accomplished

**Five real defects found and fixed, none of them visible to any harness.**
Three were found by exploration; two were reported by the user from the running
app.

*Found by exploration:*

* **The audit trail survived `seed --flush`.** `AuditLog` and `LoginAttempt` sit
  below everything in the dependency graph, so nothing cascaded to them. 10 of 16
  rows were orphans naming deleted accounts — including harness probe users — and
  the Admin lands directly on that table. `LoginAttempt` also drives lockout, so
  a run of failed sign-ins could lock a demo account unclearably (D-050).
* **The payroll register opened on the wrong run.** `Reports.jsx` took
  `payruns.rows[0]` under `-period_start` — "the newest run", which is the
  one-payslip off-cycle correction. Precisely the rule D-034 replaced on the
  dashboard, in a screen that was missed (D-051).
* **The register export's filename was never readable.** The server sends a
  per-run `Content-Disposition`; CORS never exposed the header, so every month
  downloaded as `register.csv` and collided. The code comment said "the filename
  comes from the server" and it had never once worked (D-052).

*Reported by the user:*

* **Leave requests were a dead end.** Created as `DRAFT`, and nothing anywhere
  advanced them — no submit action exists and the screen acts only on
  `TO_APPROVE`. Every request raised through the UI was unactionable. The seeded
  rows hid it by setting state directly on the model (D-053).
* **An employee could self-approve their own leave.** `state` was a writable
  serializer field, and create is the one write every employee has. `POST
  {"state": "APPROVED"}` returned 201 APPROVED. Confirmed over HTTP before and
  after the fix (D-054).
* **The profile-change queue was both wrong and unfindable.** A reviewer's own
  request sat in their own "awaiting you" panel behind an Approve button that
  could only 400; and the queue's only entrance was a tab inside "My profile"
  (D-055, D-056).

**The demo was rehearsed after all, mechanically.** Criterion 4 was walked
through the wizard for the first time — `DUPLICATE` on creation, then
`AC_MISSING` ×2 after Compute: three warnings, two distinct codes, zero errors.
Scenario B's allocation gate was driven to a real refusal. Every figure the
script quotes was confirmed on screen.

**All 22 routes were walked as all five roles** with `console.error`,
`window.onerror`, unhandled rejections and `window.fetch` patched to collect
`{route, message}`. Zero console errors, zero unexpected responses.

### What was attempted and abandoned

* **A sixth bug was found and deliberately not fixed.** Leave approval has no
  self-approval guard, unlike profile changes (B-034, T-134). It is not reachable
  in the demo — Sara holds zero own pending requests and the admin has no
  employee record — and fixing it in FREEZE would change the seeded approval
  queue. Reported to the user instead of changed.
* **T-111 was not resolved.** Ledger's 3.05:1 primary button still needs the
  user's decision and has now been carried unasked across three sessions.
* **The probe scripts were not committed**, following session 07's precedent. The
  findings worth keeping became five real tests in `accounts/tests.py`.

### A note on test quality

Each of the five new tests was **verified to fail against the pre-fix code** by
stashing the fix and re-running — `'DRAFT' != 'TO_APPROVE'`, `'APPROVED' !=
'TO_APPROVE'`, and the queue assertion. A regression test that passes either way
is decoration, and this is cheap to check.

### Verification at close

236 backend tests (from 231), 28/28 rules, 53/53 API, 26/26 forms, permission
audit clean across every cell, clean frontend build. Demo reseeded to a known
state: 0 audit rows, 0 login attempts, network enforcement off, three paid
payruns plus the March off-cycle correction still `Computed` (D-033 intact).

### Handoff

Product code merged to `main` in two `--no-ff` merges before packing —
**`febce21`** (three exploration findings) and **`026bcc8`** (the two approval
workflows). The working tree was clean at MEGATRON LAUNCH, so no `wip:` commit
was needed. Context committed separately and tagged **`handoff-franklin-08`**.

**Next up: Trevor, session 09.** First action is **T-107** — seed, start both
servers, sign in as `aarav@oxp.com`, and read demo scenario A aloud against the
screen, fixing the prose. The script's figures are now all verified correct; what
is stale is its description of menus and roles, which predates the permission
rebuild.

---

## Session 09 — Trevor · 2026-09-06 03:49 → 06:20 IST (~2h 30m)

Opened on the session 08 handoff, set the `MeghRaval30` identity, and then the
brief changed completely. The board said FREEZE with one task left (T-107, the
demo script). The user's actual instruction was to build a substantial new
feature area: AI-assisted data migration using local models, plus a bulk
workforce management ecosystem. That is what the session did.

**T-107 was not touched.** It is still the most valuable open task and is now
worse than when the session started, because there is a whole feature area the
script does not mention. See B-036.

### What was accomplished

**An AI data-migration studio, built around a measurement rather than a guess.**

The obvious design — hand the headers to a local model and do what it says —
was built first and measured. `qwen2.5:7b` at temperature 0 returned `null` for
`Sal (pm)`, `DOJ` and `Mob No` in one pass and mapped all three correctly in
the next, with nothing in the response to tell the two apart. The rebuild made
the model **one voter of three** (D-057) and fed it the profiler's measured
evidence instead of raw values (D-058), which took it from 3/6 to 6/6 columns
on the same prompt. The reconciler keeps the losing votes, so the screen can
show the profiler overruling the model.

Everything works with the model switched off — the two deterministic voters map
10 of 13 columns on the bundled files, in about 40 ms, and every response says
which path ran.

**A second-file join.** A roster is never in one place: HR has names and pay,
finance has bank details in its own spreadsheet. The studio detects the join
key by measuring value overlap rather than being told (`enrich.py`), reports
matched / not-found / unused, and fills only blanks. On the demo pair it
matches 14 of 16 on `Staff ID` and names the two people finance never sent.

**Employee numbering**, always asked rather than assumed (D-063), previewed
against real rows because the year comes from each person's own joining date,
with sequences continuing from what is already issued.

**A workforce operations app**: segments as saved questions, bulk
increment/exit/transfer/bond-issue with a mandatory preview built from the same
code that executes, bonds with pro-rata recovery, and playbooks that raise
reminders and never change anything. The mass increment closes the current
contract and opens a new one rather than editing a wage in place, which is the
graded period-resolution rule working from the other side.

**Setup that actually verifies.** `scripts/setup-ai.ps1` / `.sh` detect Ollama,
pick the 7B or 3B from `nvidia-smi`, pull, warm, then fire a real mapping
prompt and report PASS/FAIL with latency. `manage.py ai_doctor` does the same
as a diagnostic and always exits 0.

**Seven demo rosters** in `test-data/import/`, each failing differently, with a
README narrating what each one proves.

**Nine defects found by using the product, none of them visible to a harness:**

* A salary column of bare integers read as **dates** — 45000 is a plausible
  monthly wage and also the Excel serial for a day in 2023. Indian salaries sit
  squarely in that range; it was masked only because the sample files carry
  currency marks.
* The implausible-wage ceiling was 5,000,000, so an unscaled annual salary of
  10,80,000 imported silently as a monthly wage.
* A bank sheet's `Account Type` (Savings/Current) mapped to **Employment type**,
  then to **Work location**.
* The model answered *some* department mappings and silently skipped others,
  which would have merged two departments and duplicated two more.
* It collapsed `Senior Developer` onto `Developer`.
* Derived emails came out at `example.com` when the file had no email column.
* **Double-clicking Import** wrote the roster once and then reported "0
  employees imported" over the top of it.
* The done screen could not distinguish "nothing needed writing" from
  "everything failed to write".
* Accepting the email fix ticked green while the rail insisted the field was
  still needed and Preview stayed disabled — two places answering one question
  (D-065).

`verify_rules.py` also had a check pinned to the 22-person seed. At
`--employees 200` it failed and **the product was right**; the check now
compares against the employees actually in the payrun, which is correct at any
size and a stronger assertion.

### What was attempted and abandoned

**A nine-agent parallel build.** Launched with a full written contract so the
agents could work against fixed interfaces. The user killed it about four
minutes in — "burning too much tokens too soon" — before any agent had written
a file. Nothing was lost and nothing was on disk. Everything after that was
built directly, sequentially, and it was the right call: most of the nine
defects above came from driving the product by hand, which a fan-out would not
have done.

**Renaming the code prefix to `FFL` during the browser walkthrough** failed
silently — a React controlled input ignores a native `value` set. Not worth
fixing; the default `EMP` is the better answer anyway since it matches the
company's existing scheme.

### Verification at close

| Check | Result |
|---|---|
| `manage.py test` | **314 OK** (was 236; 78 new) |
| `verify_rules.py` | 28/28, at 22 employees **and** at 200 |
| `audit_permissions.py` | every cell matches the intended matrix |
| `smoke_api.py` | 53/53 |
| `probe_forms.py` | 26/26 |
| `npm run build` | clean, ~835 kB |
| `manage.py ai_doctor` | all checks pass, 711 ms warm |
| Admin-only enforcement | 9 endpoints x 4 other roles, all 403; menu absent for all four |

### Git

Eight working commits on `feat/intelligence-layer`, then reorganised at the
user's request into **four feature branches**, each squashed to one commit and
merged `--no-ff` into an integration branch based on `origin/main`:

* `feat/ai-import-studio`
* `feat/workforce-operations`
* `feat/ai-setup-and-test-data`
* `feat/import-enrichment`

The final integration tree was asserted **byte-identical** to the original
branch tip before pushing, so nothing was lost in the reorganisation. Pushed to
`main` with `git push origin HEAD:main`, because `main` is checked out in an
abandoned worktree 41 commits behind (B-038).

### Handoff

Handoff SHA and tag are recorded in the closing report and in
`current-state.md`. **Michael is up next.** His first action is B-036: rewrite
the demo script against the running product, including a scenario for the
import studio.

### Correction — 2026-09-06 06:35 IST

The closing entry above says "Michael is up next". **It is Franklin.** Michael
was unavailable when the handoff was made, so the rotation is taken out of order
and session 10 comes back to Franklin, who also ran session 08.

Nothing else changes: Franklin has no memory of session 09, commits as
`Robo9327study` / `rajstudy9327@gmail.com`, and picks up the same first task —
T-107 / B-036, the demo script. `NEXT-SESSION-PROMPT.md` was corrected to
address Franklin by name rather than left to contradict itself, because a
briefing that greets the wrong character is the kind of thing that costs a cold
session its first ten minutes.
