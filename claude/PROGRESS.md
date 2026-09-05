# PROGRESS — the RBAC + UI overhaul

Running log for the work the user commissioned on **2026-09-05 at 20:45 IST**.
Newest entry at the **bottom**. One short entry per commit. Append only.

> This file is a diary of *this* stretch of work. Task status still lives only in
> `claude/state/task-board.md`, and the clock in `claude/state/current-state.md`.

---

## The commission, in the user's words

Redo the UI completely against the excalidraw mockup. Build 4–6 full design
languages, not just palettes. Rework account types from the sources: what each
role may do, what each role *sees*, and what its dashboard looks like. Add a
profile menu with self-service settings, including changes that need approval.
Fix the attendance figures — overtime as a count is useless, and decimal hours
are the wrong unit. Add real security: network-restricted login and hardening
against gaming the system. Let a user change their own password.

---

## What the sources actually say

Two documents govern this, and where the user's examples and the sources
disagree the sources win — the user asked for that explicitly.

**`PeoplePay360 HR & Payroll.pdf` §3 — User Roles.** Five roles, quoted:

| Role | The PDF's words |
|---|---|
| **Employee** | View own employee details, attendance records, and leave balances. Create attendance entries and Time Off Requests, with **no payroll or HR administration access** |
| **HR Manager** | Full CRUD on Employees, Attendance, Contracts, Working Schedules and Time Off. Approve or refuse Time Off Requests, **with no access to payroll features** |
| **HR Payroll User** | All HR Manager permissions **plus Create, Read and Update** on Payruns and Payslips. **Read-only** on Salary Structures and Salary Rules |
| **HR Payroll Manager** | All HR Payroll User permissions with **full CRUD** on Payruns, Payslips, Salary Structures and Salary Rules |
| **Admin** | Full access to all modules. User management, role assignment, permission updates, system administration |

**The mockup's LOGIN / USER ACCESS NOTE.** Accounts are created by an Admin.
A user is linked to an employee and assigned **one or more roles** — so yes, one
account can hold several roles; the effective permission set is their union.
Roles control which modules, records and actions appear after login. **Users must
not be able to assign or elevate their own roles.**

**Two places the user's examples and the PDF disagree**, flagged rather than
silently resolved:

1. The user said an HR Manager *cannot* create an attendance record. The PDF
   gives HR Manager full CRUD on Attendance. Resolved in favour of the PDF, but
   split by intent: an employee's own check-in is a *punch*, an HR Manager's is a
   *correction* — a different action, on a different screen, flagged
   `is_manually_edited` and written to the audit log.
2. The user said a Payroll Manager sees only employee details and holidays. The
   PDF gives the Payroll Manager everything an HR Payroll User has plus full
   payroll configuration. Resolved in favour of the PDF.

---

## Plan

| # | Step | State |
|---|---|---|
| 1 | Capability matrix, `/api/me` manifest, server-side enforcement | planned |
| 2 | Self-service: own password, own profile, approval-gated field changes | planned |
| 3 | Security: network-restricted login, lockout, audit log, anti-gaming | planned |
| 4 | Attendance as hours and minutes, everywhere it is shown | planned |
| 5 | Design system: 6 complete themes — colour, type, shape, density | planned |
| 6 | Role-aware navigation and the profile menu | planned |
| 7 | A distinct dashboard per role | planned |
| 8 | Screen-by-screen pass against the mockup | planned |

---

## Log

### 20:45 — picked up, sources read end to end
Extracted all 1,187 text elements from the excalidraw board and the full text of
the problem-statement PDF; both are now transcribed in the scratchpad and the
role table above is quoted from the PDF rather than remembered. Branch
`feat/rbac-ui-overhaul` cut from `main`.

Before the pivot this session finished the previously-queued work: `seed
--employees N` (T-089) and its tests, merged and pushed. A 250-person roster
seeds in 40s and a 233-employee payrun computes in 5.7s; that run raises
`NO_CONTRACT` and `AC_MISSING` together, which closes PRD success criterion 4.

### 21:30 — the capability matrix, and what it replaced
`accounts/capabilities.py` is now the single home for "who may do what". Roles
are the five the PDF names; a user may hold several and the effective set is the
**union**, not the highest one — which is what the mockup's "one or more roles"
actually requires and what a real "HR Manager + Payroll User" needs.

The four old boolean flags (`is_admin`, `can_manage_hr`, `can_run_payroll`,
`can_configure_payroll`) still exist but are now *views* onto the matrix rather
than a second copy of the rules, so the 86 existing account tests kept passing
without edits.

`/api/auth/me/` now returns capabilities, a **server-built navigation tree** and
which dashboard the account lands on. A menu a role cannot use is absent, not
greyed out. Hiding is presentation; the permission classes still enforce.

### 21:55 — security: sign-in, sessions, self-service, audit
Six things, each closing a named attack rather than ticking a box.

**Network-restricted sign-in.** `NetworkPolicy` rows hold CIDRs and can be
scoped to a single role — the realistic shape being "pin payroll staff to the
office because they can move money, leave everyone else alone". The check runs
on **every request**, not only at sign-in: checking once would mean you
authenticate at the office and then use the token from anywhere.
`X-Forwarded-For` is ignored unless `TRUSTED_PROXY_COUNT` says a proxy is real,
because otherwise anyone claims to be on the office Wi-Fi with one header.

**Sessions that end.** DRF's token never expires. `ExpiringTokenAuthentication`
adds an idle timeout, an absolute lifetime and optional address binding.
Deactivating a user now kills their live sessions instead of waiting for the
token to lapse — which is exactly the window someone being walked out uses.

**Lockout.** Failures counted per email and per address; the streak resets on
success. A locked account is rejected *before* the password is checked, so it
leaks nothing. A wrong email and a wrong password return the identical message.

**Self-service, split by blast radius.** Phone and address are the employee's
own business and apply immediately. Name, date of birth, PAN and **bank account**
go through an HR approval queue — repointing a salary the day before a payrun is
the single most attacked field in any payroll system. Nobody can approve a change
to their own record, HR rights or not, or the control would be decorative.

**Password change.** Requires the current password (a borrowed unlocked laptop
must not become a permanent takeover) and signs out every other session.

**Audit log.** Append-only, and deliberately not a generic history table — it
records the handful of actions that matter in a dispute: who approved what, who
changed whose bank account, who granted which role, whose attendance was
corrected by hand.

Plus the escalation guards: you cannot change your own roles, deactivate
yourself, or remove the last active administrator.

### 22:05 — attendance reads in hours and minutes
The user was right twice. `8.45` is eight hours and *twenty-seven* minutes, and
a dashboard tile that counts how many times overtime happened tells you nothing.
`core/formatting.py` holds the conversion; the API now serves `worked_hm`,
`elapsed_hm` and `overtime_hm` beside the decimals, which payroll still needs to
multiply. The widget's compact form matches the mockup exactly: `6h56`.

Anti-gaming on the same surface: an employee may punch **only for themselves**
and **only for today** — worked days feed pay, so a back-dated record is a
self-service raise. Posting a colleague's id used to be silently rewritten; it
is now refused and logged, because nobody does that by accident. Check-in can be
required to come from a permitted network, on its own switch, since a clock you
can punch from your sofa is not attendance.

**119 backend tests green** (86 accounts including 31 new security tests, 33
attendance).

### 22:45 — six design languages, and a UI that differs by role
**`themes.css`** holds six complete design languages. Each one sets its own
type pairing, corner geometry, border weight, shadow behaviour, density and
label treatment — not just a palette. Switching theme changes how the product
*reads*.

| | Character |
|---|---|
| **Ledger** | Warm paper, serif figures, hairline rules, dense. A printed register. |
| **Console** | Dark slate, cyan signal, monospaced numbers, caps micro-labels. An ops tool. |
| **Atrium** | Cool white, indigo, 14px corners, layered shadows, roomy. Modern SaaS. |
| **Blueprint** | Square corners, 2px rules, electric blue, maximum contrast. Reads from the back of a room. |
| **Marigold** | Cream and cocoa, marigold, rounded, humanist serif. The friendliest. |
| **Graphite** | Neutral dark, amber accent, grotesk display. Puts status colours in relief. |

`index.css` was rewritten so that **nothing hard-codes a colour, radius, shadow
or padding** — otherwise six languages would only be six palettes. Every theme's
font stack ends in a real system fallback of the same class, so an offline demo
machine still gets six distinguishable looks rather than six copies of Arial.
The choice is per browser, not per account: it depends on where you are sitting.

**The navigation is now built by the server.** `/api/auth/me/` returns a tree
pruned to the account's capabilities and the shell renders whatever it is given.
A menu a role cannot use is absent, exactly as the mockup's access note asks.

**Four dashboards, four endpoints — not one endpoint with cards hidden.**
Hiding a card in the browser leaks its numbers to anyone who opens the network
tab, and the HR Manager role is defined as having *no access to payroll
features*. So the payroll figures never leave the server for a role that may not
see them. This also closed a real leak: `/api/dashboard/` had only been gated on
being signed in, so an HR Manager could read total net paid.

* **Employee** — am I clocked in, hours worked this month, leave balance with a
  used-bar, my contract, my payslips. Everything scoped in the query itself.
* **HR Manager** — leads with the queue: leave, allocations and personal-detail
  changes waiting on *this person's* decision, approvable inline. Then
  attendance quality, then contracts about to lapse. No money anywhere.
* **Payroll** — the mockup's dashboard, unchanged in shape.
* **Admin** — accounts by role, live sessions, and the security posture written
  as sentences rather than booleans, because a false checkbox is easy to read
  past. Plus the audit tail.

New screens: **My profile** (details / change requests / password & sessions),
**My payslips**, **Security**, **Audit log**. `npm run build` clean.

### 21:25 — MEGATRON LAUNCH
Feature work stopped mid-sentence, on the fourth of the six themes being checked
in a browser. `claude/workflow/megatron-checklist.md` executed end to end.

Two real fixes landed on the way out rather than being left for the next
session, because both would have handed over a red suite or a misleading demo:

* The employee dashboard windowed on the **current calendar month**. Seeded
  attendance ends March 2026 and the machine clock reads September, so every
  employee opened on a screen of zeroes — which reads as "the system is broken",
  not "you have not clocked in yet". It now falls back to the month of their
  most recent record and labels which month is on screen.
* `core/tests.py::test_a_mid_period_joiner_is_prorated` failed in the full run
  after passing standalone. The cause was real and worth fixing at the source:
  the generated roster picked its four contract shapes by random draw, so at a
  small N it could produce **no joiner at all**. A large-roster generator whose
  interesting cases may simply be absent demonstrates nothing. The first three
  generated people are now dealt one of each shape deterministically, and the
  test builds its payrun around whichever month the joiner actually landed in
  rather than a hard-coded March.

**Where the commission stands: about 70% delivered.** Access control, security,
self-service, the four dashboards, the six theme definitions and the new screens
are done and merged. What remains is a screen-by-screen pass over the older
frontend — Login, the attendance widget, the attendance list, the payroll
dashboard's overtime tile, Users & Roles, and moving action-button gating from
the four legacy booleans onto capabilities. Every one of those is itemised, with
the file and the exact change, in `current-state.md` §HALF-DONE and in the
briefing §8.1.

Four of the six themes have never been rendered. That is written down twice, in
capitals, because "six themes" is the kind of claim that is easy to inherit and
repeat without checking.

---

## Session 06 — Trevor — finishing the commission

### 21:45 — booted, harnesses re-run before touching anything
Inherited checkout proven green from a cold start: `manage.py test` **216/216**,
`verify_rules.py` **28/28**, `smoke_api.py` **51/51**, `probe_forms.py` **26/26**,
seed reproduces the pinned demo figures (22 employees, 60 payslips, December
INR 14,73,360 / January 14,82,320 / February 15,58,667.87).

B-021 caught something on the way in. Port 8000 was clear, but **port 5173 was
held by a Vite from a different worktree** (`frontend-routing-setup-e9a159`),
which would have served an older frontend under the right URL — the exact
failure mode the blocker describes, one directory over. Killed it and started
this worktree's own pair. Worth writing down: the check is worth running on the
frontend port too, not just 8000.

### 21:50 — T-101 login screen to the mockup's copy
Branch `feat/ui-screen-pass`. "Welcome back", "Sign in to continue to your
workspace", **Work Email** with a `name@company.com` placeholder, **Sign In**,
and the access note the mockup carries: *Accounts are created by an
administrator.*

Two judgement calls:

* **Forgot password?** — the mockup has the link and there is no anonymous reset
  endpoint, deliberately: `POST /api/users/{id}/reset-password/` is admin-only
  because the mockup's access note says accounts are administered. So the link
  says the true thing in one clause rather than pretending at a flow that does
  not exist.
* **The five demo chips** are gated on `import.meta.env.DEV`. They are the
  fastest way to switch persona in a live demo and wrong in a shipped product;
  `npm run dev` keeps them, `npm run build` compiles them out. The email/password
  prefill is gated the same way, so a production build opens on empty fields.

### 21:55 — T-102 attendance in hours and minutes, T-103 the overtime tile
The API had served both forms since session 05; these two screens were still
printing the decimal. Now:

* **Attendance list** — `8h 46m` worked, `16m` overtime, straight off the
  serializer's `worked_hm` / `overtime_hm`. The decimal stays on the payload
  because payroll multiplies it.
* **Check-in widget** — `elapsed_hm` and `total_today_hm`, the mockup's `6h56`.
  It also surfaces `punch_blocked_reason` and disables the button when
  `can_punch` is false. Proven by planting a policy for `10.20.30.0/24`,
  switching `enforce_network_on_punch` on, and watching the widget refuse from
  127.0.0.1 with the server's own sentence. Both the policy and the settings
  flag were reverted afterwards, and the punch made during the test deleted —
  attendance is back to the seeded 1,746 rows.
* **Payroll dashboard, Attendance Overview** — the tile the user called out.
  It read `Overtime  262` and `Overtime hours  124.63`. It now leads with
  **124h 38m carried by 22 employees** and **average day worked 8h 43m**, the
  same phrasing the HR dashboard already used. The count is not deleted, it is
  relabelled **Days with overtime**, where a count is the honest unit — ten
  six-minute overruns and one nine-hour one are the same count and a very
  different payroll problem, which is exactly why the bare count was useless.

One server-side copy fix went with it: a punch refused by the network policy
said *"Sign-in from 127.0.0.1 is not permitted"*, which reads as though the
session is about to be cut. `network_allows` now names the action it actually
refused. `accounts` + `attendance` 119/119 still green.

### 22:15 — T-104 Users & Roles
The screen pre-dated the matrix. It now carries the mockup's five columns —
**User · Employee · Work Email · Role · Status** — a search box and a role
filter, and three things it was missing:

* **The account-status switch.** `is_active` was already in the form's state and
  posted on every save, but nothing rendered it, so an administrator could not
  actually deactivate anyone from this screen. That is now a checkbox.
* **Reset password.** `POST /api/users/{id}/reset-password/` sets a temporary
  password and ends every session that account holds. It is a separate action
  from Save rather than a field on the form, because it is not an edit — it
  logs the person out everywhere and writes to the audit log.
* **The capability grid**, from `GET /api/users/capability-matrix/`, grouped by
  resource. It is served from the same module the permission classes enforce
  with, so the grid an administrator reads cannot drift from what the server
  does — which is the whole reason it is worth showing.

`UserSerializer` gained `employee_code` and `employee_work_email`, because the
mockup gives the sign-in address and the employee's work address two separate
columns and the interesting rows are the ones where they differ.

Driven in the browser, all four paths: role filter 5 → 1, search "rahul" → 1,
reset password (accepted at 8 characters, refused at 3 with the server's own
sentence), and the escalation guard — unticking Admin on your own account
surfaces **"You cannot change your own roles. Ask another administrator to do
it."** and changes nothing. Rahul's password was reset back to `demo1234`, so
every demo account still signs in. `npm run build` clean.

### 22:45 — T-105 controls follow capabilities, and a route guard
The last `auth.can()` in the codebase is gone. Create and Save buttons now read
`auth.has("<capability>")`: `employee.write`, `contract.write`,
`attendance.correct`, `schedule.write`, `reference.write`,
`timeoff.type.write`, `allocation.write`, `salaryconfig.write`.

The worst one found by walking it: **an employee looking at their own pending
leave request was shown Approve and Refuse buttons on it.** The server refuses
(`timeoff.approve`), so nothing could be approved — but a screen that offers
someone the power to approve their own leave is making a claim about the system
that is exactly backwards. Now gated; HR still sees ten of them across eleven
requests.

Also closed a whole class of the same problem. Typing `#/payroll` as an HR
Manager rendered the Payruns screen — empty table, "0 records", a permission
error underneath. It looked broken rather than refused. There is now one route
guard in `App.jsx`, and it does **not** keep a second copy of the capability
table: it reads the navigation tree `/api/auth/me/` already pruned for this
account. A menu the account cannot use is absent (D-028), so a route absent from
that tree is a route it may not open — typed, bookmarked, or otherwise. Refused
routes say *"Not available for this account."* and nothing else.

Verified by walking every route as all five accounts:

| Signed in as | Result |
|---|---|
| `john@oxp.com` Employee | Menu is Dashboard · Attendance · Time Off · My Payslips. `/employees`, `/payroll`, `/users`, `/security`, `/salary-rules` all refuse. Attendance shows his own 80 rows and no New Record; Allocations shows his one row and no New Allocation |
| `sara@oxp.com` HR Manager | Every payroll and admin route refuses. All 13 of her own routes render |
| `rahul@oxp.com` Payroll User | Reaches payroll; `/users`, `/security`, `/audit` refuse. Salary Rules opens **read-only** — no New Rule, and the rule form offers Close with no Save, which is exactly the PDF's "read-only access to Salary Structures and Salary Rules" |
| `aarav@oxp.com` Payroll Manager | Same screen, New Rule present and Save present |
| `admin@oxp.com` Admin | All 18 routes render |

One copy fix on the way past: the HR dashboard's subtitle read "live from
Employee, Contract, Attendance, Time Off". The design language forbids narrating
the architecture to the user (§5) — the period alone is the honest sub-heading.

**A trap worth recording (new, B-026).** Two writes to the same `.jsx` inside
one second left Vite serving a transform from *between* them: the JSX referenced
`canApprove` and the declaration was missing, so the screen threw
"canApprove is not defined" and survived a hard browser reload, because the
stale copy was on the **server** side of the module graph. `curl
localhost:5173/src/screens/TimeOff.jsx` showed the truth in one command, and
`touch` on the file fixed it. Same shape as B-021: the thing serving you is not
the thing you edited.

### 23:20 — T-106 the six themes, and the reason none of them worked

The briefing said four themes had never been rendered. The truth was worse:
**not one of the six had ever rendered.** Every theme resolved to Ledger.

`index.css` must `@import "./themes.css"` at the top — CSS allows `@import`
nowhere else — and then declares the Ledger defaults on a bare `:root`, as a
graceful fallback for a theme that forgets a token. But `:root` and
`[data-theme="x"]` have **identical specificity** (0,1,0), so the later
declaration wins, and the later declaration is always the fallback. The
attribute was being set on `<html>`, the choice was being stored, the swatch was
highlighting — and not one token changed. Measured, before the fix:

```
ledger    bg #f4efe9  primary #d97757  radius 8px
console   bg #f4efe9  primary #d97757  radius 8px     ← Ledger
atrium    bg #f4efe9  primary #d97757  radius 8px     ← Ledger
blueprint bg #f4efe9  primary #d97757  radius 8px     ← Ledger
marigold  bg #f4efe9  primary #d97757  radius 8px     ← Ledger
graphite  bg #f4efe9  primary #d97757  radius 8px     ← Ledger
```

The fix is one character class per selector: `[data-theme="x"]` →
`:root[data-theme="x"]`, which is (0,2,0) and beats the fallback. That is the
behaviour the fallback was always meant to have, and the reasoning is now
written into the top of `themes.css` so nobody re-flattens it.

This is worth dwelling on for a moment. Session 05 wrote in capitals, twice,
that four themes were unverified — and that instinct was right. But the two it
believed *were* verified were verified by looking at a switcher that highlighted
the right swatch. **A control that visibly responds is not evidence that
anything downstream of it happened.** The check that actually settles it is four
lines of `getComputedStyle`, and it now exists as a habit rather than a
screenshot.

Then all six were driven for real — the payroll dashboard, a kanban, a table and
a modal in each:

| Theme | Verified |
|---|---|
| **Ledger** | Warm paper, terracotta, hairlines, serif figures |
| **Console** | Dark slate, teal, JetBrains Mono, caps labels |
| **Atrium** | White topbar, indigo, 14px radius, soft shadows, Outfit |
| **Blueprint** | Square corners, 2px rules, electric blue on white, IBM Plex. The contracts table holds up — **no layout break at `--radius: 0`** |
| **Marigold** | Cream and cocoa, Fraunces, rounded |
| **Graphite** | Neutral dark, amber, Space Grotesk |

No horizontal page overflow in any of the six, measured rather than eyeballed.

**Two real defects fell out of finally seeing them.**

**The charts belonged to one theme.** Recharts cannot read CSS custom
properties, so its palette was a hand copy of Ledger's tokens at the top of
`Dashboard.jsx`. Harmless with one theme; wrong with six. On Blueprint it drew a
terracotta line across electric blue, and on both dark themes the axes were a
light-theme grey that disappeared into the card — the trend line was effectively
invisible. `lib/theme.js` now exposes `chartPalette()` and a `useChartPalette()`
hook that reads the tokens back out of the document, with a `MutationObserver`
on `data-theme` so the charts re-colour **live** when the theme is switched with
a dashboard open, which is exactly what a demo does. Confirmed: switching
Marigold → Console repaints the trend line `#d98324` → `#3fd0c9` without a
reload.

**Marigold's buttons failed contrast.** Cream `#fffdf8` on marigold `#d98324`
measures **2.86:1** — below WCAG AA for 13px labels and below even the 3:1
large-text floor. Now cocoa `#2e2317` at **5.28:1**, which also suits the
theme's printed feel better.

Contrast was measured across all six for text, dim text, faint text, primary,
button labels and the topbar. Everything else clears AA, with one **inherited**
exception worth flagging rather than silently changing: Ledger's white-on-
terracotta button is **3.05:1**, the same failure Marigold had. That colour pair
is fixed by `ui-design-language.md` §2 and is the product's signature look, so
it is being reported rather than altered at hour 13 — see the note in
`current-state.md`.
