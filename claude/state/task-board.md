# TASK BOARD

**This is the single source of truth for task status.** Do not duplicate status
into any other file. Update a task the moment it changes — not at the end of your
session.

**Statuses:** `TODO` · `IN PROGRESS` · `BLOCKED` · `DONE` · `CUT`
A task you started but did not finish is `IN PROGRESS`, never `DONE`.

---

## Phase 0 — Setup & Planning

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-001 | Read and digest problem statement PDF | `DONE` | Michael | |
| T-002 | Parse Excalidraw mockup, extract all fields | `DONE` | Michael | 3,459 text elements parsed |
| T-003 | Design relay context system | `DONE` | Michael | |
| T-004 | Scaffold `claude/` folder + `CLAUDE.md` | `DONE` | Michael | |
| T-005 | Write the PRD | `DONE` | Michael | `claude/context/prd.md` v1.0 |
| T-006 | Write the data model / schema | `DONE` | Michael | `claude/context/data-model.md` v1.0 |
| T-007 | `git init`, connect remote, first push | `DONE` | Michael | pushed; branching model live |
| T-008 | Confirm hackathon start/end time with user | `DONE` | Franklin | 10:00 IST 05 Sep -> 10:00 IST 06 Sep, confirmed by user |

## Phase 1 — Backend foundation

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-010 | Django project scaffold + DRF + Postgres config | `DONE` | Michael | Django 6.1 + DRF 3.18, SQLite (D-011) |
| T-011 | Auth: custom User linked to Employee | `DONE` | Michael | email-login User, OneToOne to Employee |
| T-012 | Roles & permission classes (5 roles) | `DONE` | Michael | 5 role classes, enforced server-side |
| T-013 | Core models: Company, Department, JobPosition | `DONE` | Michael | + WorkLocation, Holiday |
| T-014 | Employee model + serializers + viewset | `DONE` | Michael | list/detail serializers, smart-button annotations |
| T-015 | WorkingSchedule + ScheduleLine, derived weekly hours | `DONE` | Michael | **verified** 40h->41h on line edit |
| T-016 | Contract model + period-overlap constraint | `DONE` | Michael | **verified** Dec=expired, Feb=running contract |
| T-017 | Attendance model, worked-hours computation | `DONE` | Michael | derived worked_hours, one-open-session constraint |
| T-018 | TimeOffType, Allocation, Request models | `DONE` | Michael |  |
| T-019 | Leave balance engine (allocation gating + consumption) | `DONE` | Michael | **verified** gate blocks, balance derives, cancel restores |
| T-020 | SalaryStructure + SalaryRule models | `DONE` | Michael | 14 rules seeded on Regular structure |
| T-021 | **Rule computation engine** (fixed / percentage / formula) | `DONE` | Michael | **verified** sequenced, idempotent, sandboxed |
| T-022 | Payrun + Payslip + PayslipLine models | `DONE` | Michael | + PayslipWarning |
| T-023 | Payrun state machine: Draft→Compute→Validate→Paid | `DONE` | Michael | **verified** PAID is terminal and read-only |
| T-024 | Payroll validation warnings | `DONE` | Michael | **verified** A/C missing fires on 2 employees |
| T-025 | Dashboard aggregation endpoints | `DONE` | Michael | aggregates 6 models, filters re-drive data |
| T-026 | Payslip PDF generation | `DONE` | Michael | ReportLab (pure wheel, no GTK) |
| T-027 | Bulk payslip email from Payrun | `DONE` | Michael | console/locmem backend, PDF attached |
| T-028 | Seed data command | `DONE` | Michael | 22 employees, 3 months, 840 payslip lines |

## Phase 2 — Frontend

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-030 | React scaffold, routing, API client, auth flow | `DONE` | Franklin | hash router, auth gate, api client wired |
| T-031 | App shell: top nav with the 6 required menus | `DONE` | Franklin | six menus; Time Off items only in its dropdown |
| T-032 | Login screen | `DONE` | Franklin | + one-click chips for all five demo roles |
| T-033 | Employee Kanban + List + Form, smart buttons | `DONE` | Franklin | kanban + list share one form; 3 tabs; smart buttons |
| T-034 | Contract list + form | `DONE` | Franklin | RUNNING marked with a green rule; + Resolve-by-period probe |
| T-035 | Working Schedule list + form with day lines | `DONE` | Franklin | day lines; no weekly-hours input, it is derived |
| T-036 | Attendance list + form | `DONE` | Franklin | list + correction form; edits flagged is_manually_edited |
| T-037 | Attendance check-in/out widget in top bar | `DONE` | Franklin | top-bar widget; hides for accounts with no linked employee |
| T-038 | Time Off: Requests, Allocations, Types | `DONE` | Franklin | requests, allocations and types all built |
| T-039 | Approve / Refuse flow | `DONE` | Franklin | approve/refuse post to the server actions |
| T-040 | Salary Structure + Salary Rule screens | `DONE` | Franklin | structures list + rule form, value fields switch on computation |
| T-041 | Payrun wizard (2 steps, no record until step 2) | `DONE` | Franklin | step 1 creates nothing; step 2 searchable with 1-N/N counter |
| T-042 | Payrun form + action bar | `DONE` | Franklin | Compute/Validate/Mark Paid/Send + Export Register |
| T-043 | Payslip form with salary computation table | `DONE` | Franklin | sequence-ordered computation table + Print Payslip |
| T-044 | Payroll Dashboard | `DONE` | Franklin | 5 spec KPIs, 4 filters, all re-drive; + register report |
| T-045 | User Management (admin only) | `DONE` | Franklin | admin only; server refuses self-role-escalation |

## Phase 3 — Integration wins (D-002)

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-050 | Attendance → worked days + LOP on payslip | `DONE` | Michael | worked_days + LOP land on payslip |
| T-051 | Overtime hours → salary rule input | `DONE` | Michael | OT rule pays 1.5x derived hourly rate |
| T-052 | Approved unpaid leave → payroll deduction | `DONE` | Michael | unpaid leave -> LOP deduction |

## Phase 4 — Deliverables

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-060 | Demo script, 2 end-to-end scenarios | `DONE` | Trevor | written and committed; **not rehearsed** — see T-063 |
| T-061 | Future roadmap writeup | `DONE` | Trevor | 694 lines, grounded in the current code |
| T-062 | README for judges | `DONE` | Franklin | run-and-verify guide, demo accounts, seed evidence |
| T-063 | **Demo rehearsal + correct the script in place** | `DONE` | Michael | **top priority.** Scenario B was written against a form that could not submit until T-079; B5's balance claim is suspect |

## Phase 5 — Quality (added session 02/03)

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-070 | Form-payload probe harness | `DONE` | Franklin | `probe_forms.py`; extended to **26/26** by T-080 |
| T-071 | Django test suite: employees, timeoff, payroll | `DONE` | Trevor | merged into `main` |
| T-072 | Django test suite: attendance | `DONE` | Trevor | 420 lines, committed and green |
| T-073 | Django test suite: accounts / role matrix | `DONE` | Trevor | 830 lines, five-role matrix, both allowed and denied sides |
| T-074 | Merge `test/backend-suite` into main | `DONE` | Trevor | `--no-ff` at `7688be1`; suite now 158/158 |
| T-075 | Frontend tests | `TODO` | | none exist; lowest priority — the browser pass and `probe_forms.py` cover the same ground more cheaply |

## Phase 6 — Bug fixes found in session 03

Three of these were *documented as failing tests* by session 03's first half,
which asserted the broken behaviour on purpose. Closing them meant reversing
those assertions, not deleting them — each is now a regression guard.

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-076 | Contract scope test caught up to Franklin's fix | `DONE` | Trevor | the merge made it fail *by succeeding*; leak was already closed in `e894840` |
| T-077 | Employee could not raise their own time-off request | `DONE` | Trevor | carve-out substitutes the employee **before** validation, not in `perform_create` — the allocation gate reads that field |
| T-078 | Payroll User could delete payruns | `DONE` | Trevor | delete is the whole difference between the two payroll rows of the spec matrix |
| T-079 | **Time Off request form could never submit, for anyone** | `DONE` | Trevor | `half_day` sent as a boolean to a `FIRST`/`SECOND` choice field, with no control rendered at all. 400 since the screen was written |
| T-080 | Probe now covers the time-off request form | `DONE` | Trevor | the one uncovered create form was the broken one. 24/24 → 26/26 |
| T-081 | Browser pass over the payrun flow | `DONE` | Trevor | wizard → compute → validate → mark paid → payslip detail, driven by hand |

---

## ~~Critical path~~ — closed

~~`T-010 → T-013 → T-014 → T-016 → T-020 → T-021 → T-022 → T-023 → T-024`~~

**Struck out: the whole chain is DONE and verified.** T-021, the salary rule
engine, was the highest-risk item in the project and has been green since session
01. There is no longer a build-blocking dependency anywhere on this board.

## ~~Suggested three-way split~~ — closed

**Struck out: every stream is finished.** Streams A, B and C all completed across
sessions 01–03. The split was a plan for building; nothing is left to build.

## Priorities for the time actually remaining (~20h at 13:40)

Everything below is optional except the first line.

| Order | What | Why |
|---|---|---|
| 1 | **T-063 — rehearse the demo and fix the script in place** | The only item with real risk left. Scenario B has never been walked, and it is the half of the demo built on the form that was broken until T-079 |
| 2 | Re-ask open question 3 — is a deployed demo required? | Asked twice, never answered. Cheap now, expensive at hour 22 |
| 3 | Polish only if the rehearsal surfaces something | Do not open new work on a green board |
| 4 | T-075 frontend tests | Genuinely lowest value for a 24h build; listed for completeness |

**The board is effectively complete.** The failure mode from here is not running
out of time — it is breaking something that already works. Prefer rehearsal over
refactoring.

## Phase 5 — Session 04: audit, rehearsal and correctness

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-080 | Re-audit PDF + mockup for missing features | `DONE` | Michael | all 16 modules present; nothing missing |
| T-081 | Fix stale refusal on the time-off request form | `DONE` | Michael | found by rehearsal; blocked Scenario B3 |
| T-082 | Label dashboard Remaining column scope | `DONE` | Michael | period-scoped vs all-period figures read as arithmetic |
| T-083 | Honour `is_employer_cost` / `appears_on_payslip` | `DONE` | Michael | were dead config; employer PF reduced net pay |
| T-084 | Embed a rupee-capable payslip PDF font | `DONE` | Michael | Helvetica has no U+20B9; every figure was wrong |
| T-085 | Draw PDF table cells in the embedded font | `DONE` | Michael | FONTNAME was header-only, body fell back to Helvetica |
| T-086 | Prorate mid-period joiners and leavers | `DONE` | Michael | 20 Feb joiner was paid a full month |
| T-087 | Seed attendance across Dec–Mar, skip holidays | `DONE` | Michael | Dec/Jan payslips read 0 worked days |
| T-088 | Full browser QA of all 18 routes and both flows | `DONE` | Michael | zero failed requests; state machine verified |
| T-089 | **Build a 200–300 employee dataset** | `DONE` | Franklin | `seed --employees N`. 250 seeds in 40s; payrun of 233 computes in 5.7s. Default 22-person seed byte-identical, pinned by `core/tests.py` |
| T-090 | Close PRD criterion 4 (two distinct warnings) | `DONE` | Trevor | **Met on the demo seed.** Seed leaves an off-cycle March payslip for Vikram Rao, so the operator's March run raises `AC_MISSING` x2 + `DUPLICATE` x1 — two distinct codes, all WARNING severity, `can_validate` still True. Dashboard now opens on the newest **paid** period so the correction run cannot hijack it. Three tests guard it. User was asked and said "decide urself"; option 1 chosen for the smallest blast radius on the rehearsed demo |

---

## Session 05 — the RBAC and UI commission

The user's brief is in `claude/handoff/prompt-history.md` §Session 05, and the
running diary is `claude/PROGRESS.md`.

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-091 | Capability matrix, `/api/me` navigation manifest, enforcement | `DONE` | Franklin | `accounts/capabilities.py`. Union over roles, not highest-wins |
| T-092 | Self-service: own password, own profile, approval-gated fields | `DONE` | Franklin | `accounts/selfservice.py` + `selfservice_api.py` |
| T-093 | Security: network policy, lockout, session expiry, audit log | `DONE` | Franklin | `accounts/security.py`, `authentication.py`. 31 tests |
| T-094 | Anti-gaming: punch scope, back-dating, self-approval, escalation | `DONE` | Franklin | Each control has a test named after the attack it closes |
| T-095 | Attendance in hours and minutes (API) | `DONE` | Franklin | `core/formatting.py`; `worked_hm` / `overtime_hm` / `elapsed_hm` |
| T-096 | Six design languages | `DONE` | Franklin | `themes.css`. **Only Ledger and Console rendered — four unverified** |
| T-097 | Role-aware navigation + profile menu + theme switcher | `DONE` | Franklin | Menu built server-side; verified for Employee, HR, Admin |
| T-098 | Four role dashboards behind four endpoints | `DONE` | Franklin | Employee and HR verified in a browser; Admin verified by API |
| T-099 | New screens: Profile, Security, Audit, My Payslips | `DONE` | Trevor | All walked, every flow driven. Five defects found and fixed — a refused security toggle that reverted silently, a missing `expected_days`, a route-guard regression on the employee's own payslip, two more decimal-hour renders, and a bank-specific hint shown on every field |
| T-100 | **Screen-by-screen pass over the pre-existing screens** | `DONE` | Trevor | T-101 to T-105 all closed and driven in a browser as all five roles |
| T-101 | Login screen to the mockup's exact copy | `DONE` | Trevor | Mockup copy verbatim + "Accounts are created by an administrator." Demo chips now compile out of a production build |
| T-102 | Attendance list + widget to hours-and-minutes | `DONE` | Trevor | List reads `8h 46m` / `16m`, widget reads `6h56`. Widget also surfaces `punch_blocked_reason` and disables the button — verified by planting a policy that excludes 127.0.0.1 |
| T-103 | Payroll dashboard overtime tile | `DONE` | Trevor | Reads **124h 38m carried by 22 employees** plus average day 8h 43m. The count survives as "Days with overtime", where a count is the right unit |
| T-104 | Users & Roles screen for the capability matrix | `DONE` | Trevor | Mockup's five columns, search, role filter, the Active switch (which was in form state but had no control), Reset password, and the capability grid. Every path driven in a browser |
| T-105 | Gate per-role action buttons on capabilities, not the four legacy booleans | `DONE` | Trevor | Last `auth.can()` gone. Create/Save/Approve gated per capability, plus a route guard read off the server's own navigation tree so a typed URL refuses in one clause instead of rendering a broken shell over a 403 |
| T-106 | Render and check the four unverified themes | `DONE` | Trevor | **None of the six had ever rendered** — a specificity bug made every theme resolve to Ledger. Fixed, all six driven, charts made theme-aware, Marigold's button contrast repaired |
| T-107 | Re-rehearse and update the demo script for the new UI | `TODO` | | **Still the last real task.** Its *figures* are now all verified correct (session 08) and the mechanics were walked; what is stale is the **prose about menus and roles**, which predates the permission rebuild. Four new facts to fold in are listed in `current-state.md` §HALF-DONE |

---

## Session 06 — finishing the commission, and what it turned up

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-108 | Charts follow the active theme | `DONE` | Trevor | Recharts palette was a hand copy of Ledger's tokens. `lib/theme.js::useChartPalette` reads the live tokens and a `MutationObserver` re-colours on switch — proven Marigold → Console repaints the trend line without a reload |
| T-109 | Route guard for screens reached by URL | `DONE` | Trevor | Reads the navigation tree the server already pruned, so it keeps no second copy of the capability table. Own-scoped detail routes (`/payslips/:id`) stay reachable where the list is not |
| T-110 | Copy pass on Profile and Security against the design language | `DONE` | Trevor | §5 forbids explaining the system to the user. Rule applied: **state the effect, do not argue for it.** The reasoning moved to the docstrings, where it was actually aimed |
| T-111 | Decide Ledger's 3.05:1 primary button | `TODO` | | **Needs the user.** White on Claude orange fails WCAG AA for 13px labels. Marigold had the same fault at 2.86:1 and was fixed because nobody had seen it; Ledger is the shipped signature look and is fixed by `ui-design-language.md` §2, so it was reported rather than changed. One token (`--on-primary` or `--primary-dark`) closes it |
| T-112 | Walk demo steps A3 → A10 in the browser | `DONE` | Franklin | Session 08 built the March payrun through the wizard as `aarav@oxp.com`: `DUPLICATE` on creation (19 payslips), then Compute added `AC_MISSING` ×2 — **3 warnings, two distinct codes, 0 errors**. Criterion 4 is now proven on screen, not only by test. Every figure in scenario A and B confirmed against the UI |

---

## Priorities for the time actually remaining (~11h at 22:50)

The board is complete apart from the demo. **The failure mode from here is not
running out of time — it is breaking something that works.**

| Order | What | Why |
|---|---|---|
| 1 | **T-112 then T-107** — walk A3 → A10, then correct the script in place | The only graded deliverable that is currently wrong. Four steps quote numbers that changed today |
| 2 | **T-111** — put Ledger's button contrast to the user | One token, one question. Cheap now, and it is the product's most-seen colour pair |
| 3 | Add the two new demo beats — the employee with no Payroll menu, and the theme switcher | Both are strong, both already work, neither needs code |
| 4 | Capability assertions in `smoke_api.py` | Cheap and valuable; the harness touches none of the new endpoints |
| 5 | T-075 frontend tests | Still the lowest value for a 24-hour build |

**Do not open new feature work.** Every graded requirement is built and proven.


---

## Session 07 — Michael · 2026-09-06

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-113 | Narrow the HR Payroll User to a read-only observer | `DONE` | Michael | Nine capabilities, all reads. 16 refusals and 6 preserved reads pinned in `audit_permissions.py` (D-041) |
| T-114 | Split HR and payroll authority into siblings | `DONE` | Michael | Neither manager role contains the other; `_ADMIN` is the explicit union so narrowing either side cannot orphan a capability (D-042) |
| T-115 | Move salary-rule writing to the Admin alone | `DONE` | Michael | Both payroll ranks read, neither writes — nobody can add a rule and then run the payrun applying it (D-043) |
| T-116 | Move every viewset onto the capability table | `DONE` | Michael | The model-flag classes gated most viewsets while the menu was built from the matrix, so a matrix change moved the menu and not the API — the failure PRD-3.1 names |
| T-117 | Retarget row scoping to read capabilities | `DONE` | Michael | Six querysets asked a write question to decide a read. Caught the payslip queryset narrowing a read-only role from 61 payslips to 3 (D-045) |
| T-118 | One account, one role | `DONE` | Michael | Radios in the form, `validate_role_ids` on create *and* update, three tests (D-044) |
| T-119 | Hide controls the signed-in role cannot use | `DONE` | Michael | New Payrun and the four payrun state buttons; Employees, Schedules, Reference, Holidays and Salary Rules open read-only with `Close` and a disabled fieldset |
| T-120 | Payroll Dashboard under Reports | `DONE` | Michael | The route already existed and `DashboardRouter` already documented it; only the menu entry was missing. Also fixed the menu landing a reload late |
| T-121 | Enlarge and fence the wordmark | `DONE` | Michael | 18px/700 against 13px nav, hairline divider on `--topbar-border`. No colour spent (D-049) |
| T-122 | Stop the harnesses dirtying the demo | `DONE` | Michael | `seed --flush` resets security settings; `audit_permissions.py` sweeps its probes (D-046) |
| T-123 | Attendance follows the contract's working schedule | `DONE` | Michael | Part-timer was seeded 5x8h against a 20h/4-day contract. Two invariant guards added to `core/tests.py` (D-047) |
| T-124 | Scope My Payslips to the signed-in employee | `DONE` | Michael | Three of five roles saw all 61 payslips under "My payslips". `useResource` gained a null path (D-048) |
| T-125 | Full robustness pass | `DONE` | Michael | 2,499 fuzzed requests (0 crashes, 0 anonymous leaks), 61 payslips x 12 invariants, 5 engine edge cases, 22 routes x 2 roles instrumented, idempotency, PDF, register |
| T-126 | Re-point `/api/attendance/status/` and `/api/me/profile/` off 400 | `TODO` | | B-032. Cosmetic — both UIs handle it well. A read whose answer is well defined should not be a client error |
| T-127 | Frontend test runner | `TODO` | | B-033, supersedes T-075 in urgency. Both bugs this session were frontend and both were found by hand |

### Re-prioritised for the time actually left

1. **T-107 / T-112** — rehearse the demo end to end. Still the only thing between
   the build and the grade. The script is corrected for session 07 but has **not**
   been walked since the RBAC rebuild.
2. **T-111** — Ledger's 3.05:1 primary button. Needs the user, one token.
3. **T-089** — the 300–10,000 employee dataset, if and only if rehearsal is done.
4. T-126, T-127 — only if everything above is closed.

**T-075** (frontend tests) is superseded by **T-127**: same subject, with real
evidence behind it now.


---

## Session 08 — Franklin · 2026-09-06

Opened on a request to hunt bugs, not to build. Everything here was found by
*using* the product; all five harnesses were green before this session and are
green after it, and none of these five defects was visible to any of them.

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-128 | Reset the audit trail on `seed --flush` | `DONE` | Franklin | `AuditLog` and `LoginAttempt` sat below everything in the dependency graph and survived every reseed. 10 of 16 rows were orphans naming deleted accounts, including harness probe users — on the Admin's landing screen. `LoginAttempt` also drives lockout, so a run of failed sign-ins could lock a demo account with no supported way to clear it (D-050) |
| T-129 | Open the payroll register on a finished run | `DONE` | Franklin | `Reports.jsx` defaulted to `payruns.rows[0]` under `-period_start` — "the newest run", which is the one-payslip off-cycle correction. Exactly the rule D-034 replaced on the dashboard. The screen now reads the server's `default_period` (D-051) |
| T-130 | Let the browser read the register's filename | `DONE` | Franklin | Server sent `Content-Disposition: filename="register-February-2026.csv"`; CORS never exposed the header, so every export fell through to `register.csv` and three months collided. One settings line (D-052) |
| T-131 | Make submitted leave requests reachable by approvers | `DONE` | Franklin | Requests were created as `DRAFT` and **nothing anywhere advanced them** — no submit action exists, and the screen acts only on `TO_APPROVE`. Every request raised through the UI was a dead end. Reported by the user (D-053) |
| T-132 | Stop an employee self-approving via the create payload | `DONE` | Franklin | `state` was a writable serializer field and create is the one write every employee has. `POST {"state": "APPROVED"}` returned 201 APPROVED — self-granted leave, consuming their own allocation and moving their own payslip. Confirmed over HTTP before and after (D-054) |
| T-133 | Fix and surface the profile-change approval queue | `DONE` | Franklin | A reviewer's own request appeared in their own "awaiting you" panel with an Approve button that could only 400; and the queue's only door was a tab inside "My profile". Both fixed; **Employees → Change Requests** added, gated on `profile.approve` (D-055, D-056) |
| T-134 | Add a self-approval guard to leave | `TODO` | | B-034. Leave approval checks only `can_approve_leave`, with no self-check — unlike profile changes, which refuse it at the write. Not reachable in the demo (Sara holds zero own pending requests, and she and the admin are the only approvers). Deliberately not fixed in FREEZE: it would change the seeded approval queue |

### Priorities for the time actually remaining (~6h 50m at 03:10)

| Order | What | Why |
|---|---|---|
| 1 | **T-107** — read the demo script aloud against the screen and fix the prose | The only graded deliverable still wrong, and the only task left |
| 2 | **T-111** — put Ledger's button contrast to the user | One token, one question. Carried unasked across three sessions |
| 3 | T-134 — the leave self-approval guard | Real, small, and unreachable in the demo. Only if the script is finished |
| 4 | T-089 — the 300–10,000 employee dataset | `seed --employees N` already exists. Deferred by the user three times |
| 5 | T-126 / T-127 | Cosmetic, and a FREEZE-phase decision respectively |

**Do not open new feature work.** The failure mode from here is breaking
something that works.

---

## Session 09 — Trevor · 2026-09-06

The board entered this session FREEZE with one open task (T-107). The user
instead commissioned a new feature area, so T-107 was **not** touched and is
now the top priority for session 10 — it has more to cover than before.

### Delivered

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-135 | Local model client with graceful degradation | `DONE` | Trevor | `intelligence/llm.py`. Ollama on 127.0.0.1, stdlib urllib only, `keep_alive: 30m`, JSON extraction that survives a fenced or prose-wrapped reply, one retry. `available()` gates the *label*, never the feature (D-059) |
| T-136 | Deterministic column profiler | `DONE` | Trevor | `intelligence/profiler.py`. Type, range, distinctness, date formats, blank ratio, and one ASCII evidence sentence per column used by both the UI and the prompt (D-058) |
| T-137 | Header-row detection | `DONE` | Trevor | `intelligence/readers.py`. Scores the first 15 rows; finds the header on line 4 of the hand-kept file and reports the three rows it skipped. Also drops a trailing TOTAL row and blank columns |
| T-138 | Synonym dictionary and lexical matcher | `DONE` | Trevor | `intelligence/schema.py`. 22 target fields with Indian-HR-aware synonyms. Maps 21 of 22 real headers with no model at all |
| T-139 | Three-voter reconciler | `DONE` | Trevor | `intelligence/mapper.py`. Keeps losing votes; hard evidence overrules the model; enforces one-column-per-field (D-057) |
| T-140 | Transform DSL | `DONE` | Trevor | `intelligence/transforms.py`. Named, composable, previewable steps. Proposes `scale(1/12)` when a money column's median says it is annual |
| T-141 | Row validation | `DONE` | Trevor | `intelligence/validators.py`. Error blocks a row, warning does not. A file with three bad rows imports the other 397 |
| T-142 | Streaming analyse endpoint | `DONE` | Trevor | `intelligence/api.py`. SSE consumed with `fetch` + reader because EventSource cannot send an auth header. Paced deliberately on the no-model path so the reasoning is still visible |
| T-143 | The Import Studio screen | `DONE` | Trevor | `screens/ImportStudio.jsx` + `components/SheetGrid.jsx`, `ai.jsx`, `intel.css`. Colour-coded columns, vote stacks, transform chips, before/after preview |
| T-144 | Second-file enrichment | `DONE` | Trevor | `intelligence/enrich.py` + `components/ImportGaps.jsx`. Join key found by measuring value overlap; 14 of 16 on the demo pair; fills blanks only, never overwrites |
| T-145 | Employee code assignment | `DONE` | Trevor | `intelligence/codes.py`. Always offered (D-063), previewed against real rows, sequences continue from what exists |
| T-146 | Workforce app: segments, bulk ops, bonds, playbooks | `DONE` | Trevor | `workforce/`. Increment opens a new contract rather than editing a wage — the graded rule from the other side |
| T-147 | Natural-language rule compiler | `DONE` | Trevor | `workforce/compiler.py`. Model output validated against the real vocabulary; anything invented is dropped *and reported*; keyword fallback with no model |
| T-148 | Workforce screens | `DONE` | Trevor | `Segments`, `MassActions`, `Bonds`, `Playbooks`, `AISetup`. NL-first on two of them, preview-before-commit on the third |
| T-149 | Restrict the smart features to the Admin | `DONE` | Trevor | D-060. Verified as enforcement: 9 endpoints x 4 roles all 403, menu group absent for all four |
| T-150 | Setup scripts and diagnostics | `DONE` | Trevor | `scripts/setup-ai.ps1`, `setup-ai.sh`, `manage.py ai_doctor`, `models_manifest.json`. All verify with a real round trip rather than assuming the pull worked |
| T-151 | AI setup documentation | `DONE` | Trevor | `docs/AI-SETUP.md` + a README section. Measured numbers, per-feature fallbacks, the privacy argument, four real failure modes |
| T-152 | Seven demo rosters | `DONE` | Trevor | `test-data/import/` + README. Each breaks differently; 06 carries 240 employees (D-064) |
| T-153 | 78 tests for the new code | `DONE` | Trevor | `intelligence/tests.py`, `workforce/tests.py`. Weighted at what fails silently: header detection, the overrule path, the mass increment not rewriting history |
| T-154 | Make `verify_rules.py` scale-independent | `DONE` | Trevor | It asserted `min(no_bank, 2)`, true only for the 22-person seed. Now compares against the employees actually in the payrun. 28/28 at 22 and at 200 |
| T-155 | Reorganise into four feature branches and merge to main | `DONE` | Trevor | Final integration tree asserted byte-identical to the original branch tip before pushing (B-039) |

### Open, in priority order for session 10

| ID | Task | Status | Owner | Notes |
|---|---|---|---|---|
| T-107 | Rewrite the demo script against the running product | `TODO` | | **The top task.** B-031 + B-036. Was stale before; now an entire menu group is unmentioned. Needs scenarios A and B corrected and a new scenario C for the import studio — `test-data/README.md` already contains the narration for C |
| T-156 | Walk the 240-row import in a browser | `TODO` | | B-037. The pipeline is proven at that size through the API; the studio UI has not been watched doing it. Low risk, 10 minutes |
| T-157 | Decide the demo seed size with the user | `TODO` | | D-066 keeps 22 as the default because the script's three-month narrative depends on those figures. `--employees 200` is verified. The user asked for 200; the answer chosen was to tell the scale story through the import instead. **Confirm this is what they want** |
| T-134 | Self-approval guard on leave approval | `TODO` | | B-034, unchanged. Real, small, not reachable in the demo |
| T-126 | Two reads answer 400 for an account with no employee | `TODO` | | B-032, unchanged. Cosmetic; both UIs handle it |
| T-127 | Frontend test runner | `TODO` | | B-033, unchanged — and this session is more evidence for it. Six of the nine defects found were frontend or frontend-adjacent and every one was found by hand |
| T-111 | Ledger primary button contrast is 3.05:1 | `TODO` | | Carried unasked across four sessions now. One token closes it, but Ledger is the shipped signature look and `ui-design-language.md` §2 fixes it, so it needs the user's decision rather than a fix |
