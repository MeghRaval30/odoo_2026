# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:   2026-09-05   10:00 IST   ✅ confirmed by the user
Hackathon end:     2026-09-06   10:00 IST   ✅ confirmed by the user
Session 05 closed: 2026-09-05   21:30 IST   (wall clock, `date`)
Elapsed:           ~11h 30m  /  24h
REMAINING:         ~12h 30m
Phase:             BUILD  (>8h)
```

**Run `date` yourself** and recompute before making any scope call.

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only. Touch nothing |

---

## WHERE WE ARE

Sessions: 01 Michael (backend) · 02 Franklin (frontend) · 03 Trevor (tests,
deliverables) · 04 Michael (audit, correctness fixes) · **05 Franklin (this
one — large dataset, then a full RBAC + UI overhaul the user commissioned
mid-session).**

The product was already complete and verified end to end at the start of this
session. Session 05 did two things:

1. **Finished the queued work** — `seed --employees N` (T-089) and its tests.
2. **Executed a large new commission** (see `claude/PROGRESS.md` for the running
   diary, and §"THE COMMISSION" below). Roughly **70% delivered**; the remaining
   30% is a screen-by-screen pass over the older screens, which is listed under
   HALF-DONE and is the next session's job.

**The commission is not finished.** Read `claude/handoff/NEXT-SESSION-PROMPT.md`
in full — it is written specifically for finishing it.

---

## ✅ WHAT WORKS — verified, with the command or click-path that proves it

### Harnesses

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py migrate          # 0003 + 0004 are new
./.venv/Scripts/python.exe manage.py test             # 216/216 OK  ✅ verified 21:50
./.venv/Scripts/python.exe verify_rules.py            # 28/28  ✅ re-run this session
./.venv/Scripts/python.exe smoke_api.py               # 51/51  ✅ re-run this session
./.venv/Scripts/python.exe manage.py seed --flush     # smoke_api dirties the DB
```

> **216/216 green**, confirmed at 21:50 IST after the seed-shape fix. That
> includes accounts 86 (31 of them new security tests), attendance 33 and core 9
> (new). Re-run it anyway as your first action — it is cheap and it is the only
> thing that proves the checkout you have is the one that was packed.

`npm run build` clean (742 kB bundle, 24 kB CSS).

### Driven by hand in a browser this session

| Signed in as | Observed |
|---|---|
| `john@oxp.com` (Employee) | Top bar is **Dashboard · Attendance · Time Off ▾ · My Payslips** and nothing else. Employee dashboard renders his contract `CON/2026/0002` ₹1,10,000, leave 18 of 20, three payslips, expected weekly **40h 00m** |
| `sara@oxp.com` (HR Manager) | Top bar is **Dashboard · Employees ▾ · Contracts ▾ · Attendance · Time Off ▾ · My Payslips** — **no Payroll, no Reports, no Administration**. Workforce dashboard: headcount 22, 4 waiting on her, coverage 100%, average day **8h 43m**, overtime **124h 38m carried by 22 employees**. No money anywhere on the screen |
| `admin@oxp.com` (Admin) | `/api/auth/me/` returns all eight menu groups: dashboard, employees, contracts, attendance, timeoff, payroll, reports, admin |

### The large dataset (T-089 — DONE)

```bash
./.venv/Scripts/python.exe manage.py seed --flush --employees 250
```

**Measured, 2026-09-05:**

| | |
|---|---|
| 250 employees seeded | **40 s** wall clock |
| Rows written | 278 contracts, 250 allocations, **19,045 attendance**, 680 payslips |
| Payrun of 20 (default seed) | **0.6–0.7 s** — PRD-7.2 asks for <5 s ✅ |
| Payrun of 225–230 (Dec/Jan/Feb) | **6.9 / 7.4 / 7.6 s** |
| Payrun of 233 (March, created live) | create 1.4 s, **compute 5.7 s** |
| Dashboard at 250 | `/api/dashboard/` 2.9 s · `/api/employees/` 0.6 s · `/api/payruns/` 2.8 s |

Scaling is linear: ~32 ms per payslip at both 20 and 233 employees.

**PRD success criterion 4 is now met.** A March 2026 payrun over the 250-person
roster raises **`NO_CONTRACT` ×8 and `AC_MISSING` ×13** — two distinct codes.
The default 22-person demo seed still raises only `AC_MISSING` ×2; see
"THE OPEN QUESTION" below.

**The default seed is byte-identical to before.** 22 employees, 24 contracts,
1,746 attendance, 3 payruns, 60 payslips, 960 lines, 6 warnings; December
₹14,73,360 · January ₹14,82,320 · February ₹15,58,667.87. `core/tests.py` pins
all of it, so a change that moves the demo's numbers fails there first.

---

## ❌ WHAT IS BROKEN

**Nothing known to be broken.** But note two things:

1. **Two stale `runserver` processes were found on port 8000** at 20:50 IST, one
   serving pre-fix code and answering first. This wasted time — see B-021.
   Check `netstat -ano | grep ":8000.*LISTENING"` before debugging anything that
   looks like an edit not taking effect.

---

## 🚧 WHAT IS HALF-DONE

Working tree clean, `feat/rbac-ui-overhaul` merged into `main`, `main` pushed.
The *code* is not half-done; the **commission** is. What remains:

### 1. The screen-by-screen pass (the big one)

New screens are built to the new design language. **The pre-existing screens
were not revisited** and still assume the old world:

| File | What is stale |
|---|---|
| `project/frontend/src/screens/Login.jsx` | Says "Sign in to continue". The mockup says **"Welcome back" / "Sign in to continue to your workspace" / "Work Email" / "Password" / "Sign In" / "Forgot password?"**. Also still shows five demo-account shortcut buttons |
| `screens/Attendance.jsx` | Renders `worked_hours` as a decimal. The API now serves `worked_hm` / `overtime_hm` — switch the columns over |
| `screens/Dashboard.jsx` (payroll) | The Attendance Overview tile still shows an overtime **count**. The endpoint now returns `total_overtime_hm`, `overtime_employees` and `average_worked_hm` — use them |
| `screens/Users.jsx` | Pre-dates the capability matrix. Should show the multi-role checkbox set, the account-status switch, the **Reset password** action (`POST /api/users/{id}/reset-password/`) and the capability grid from `GET /api/users/capability-matrix/` |
| `screens/Employees.jsx`, `Contracts.jsx`, `TimeOff.jsx`, `Allocations.jsx`, `Payruns.jsx`, `Payslips.jsx`, `SalaryConfig.jsx`, `Schedules.jsx`, `Reference.jsx`, `Holidays.jsx`, `TimeOffTypes.jsx`, `Reports.jsx` | Work, and inherit the new tokens automatically, but were not re-checked against the mockup or against `auth.has(...)` for per-role action gating. **Action buttons are still gated on the four legacy booleans, not on capabilities** |
| `components/AttendanceWidget.jsx` | Should read `elapsed_hm` / `total_today_hm` (the mockup's `6h56` form) and must surface `punch_blocked_reason` when the network policy refuses a punch |

### 2. Not verified in a browser

Only Ledger and (briefly) Console were seen. **The other four themes —
Atrium, Blueprint, Marigold, Graphite — have never been rendered.** They are
plausible but unproven; check every one before claiming six work.

The Profile, Security, Audit, My Payslips and Admin-dashboard screens were
written but **only the Admin dashboard's data was confirmed**; none of the four
new screens has been clicked.

### 3. Not written

No tests for the four new frontend screens, and no test for
`hr_dashboard_view` / `my_dashboard_view` / `admin_dashboard_view` beyond the
capability gate. `verify_rules.py` and `smoke_api.py` do not touch any new
endpoint.

---

## ⬜ NOT STARTED

1. **`/profile` change-request approvals have never been exercised end to end**
   in the UI. The backend path is tested (`accounts/test_security.py`), the
   screens are not.
2. **The demo script has not been updated** for any of this. It still describes
   the old menu, and it never mentions roles, themes or the profile menu.
   Whoever finishes the UI must re-rehearse it — see `§14` of the briefing.
3. **T-075 frontend tests.** Still lowest priority.

---

## ➡️ YOUR FIRST ACTION

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py test 2>&1 | tail -20
```

If that is green, start the screen-by-screen pass at
`project/frontend/src/screens/Login.jsx` (smallest, most visible, and quoted
verbatim in the mockup), then `AttendanceWidget.jsx`, then `Attendance.jsx`,
then `Dashboard.jsx`'s overtime tile. Those four are the ones the user
explicitly complained about.

---

## THE COMMISSION — what the user actually asked for

Verbatim in `claude/handoff/prompt-history.md` under Session 05. In summary:

1. **Redo the UI completely**, strictly following the excalidraw mockup.
2. **4–6 themes** — "not just colours … fonts style and boxes style and all the
   stuff aswell full design language". ✅ **six built**, four unverified.
3. **Rework account types** from the sources: who exists, what each may do, what
   each *sees*, and what its dashboard looks like. ✅ **done**.
4. "**all buttons wont be there for every account type login**" — an employee
   gets only their own dashboard, with attendance and the rest as separate
   tabs. ✅ **done and verified in a browser**.
5. **A profile menu** with user settings and personal-detail changes, "some
   might require approval". ✅ **built**, not clicked.
6. "**can you add more than one account type?**" — **yes**, and the matrix takes
   the union. Confirmed by the mockup's own access note.
7. **Overtime as a count is useless, and decimal hours are wrong** — needs hours
   and minutes. ✅ backend done; **the payroll Dashboard tile still shows the
   count**.
8. **Security**: login only from selected networks, plus "super critical cyber
   security stuff … make sure no one can game the system". ✅ **done** — see the
   briefing §5.
9. **A user can change their own password.** ✅ **done**.
10. **Keep committing, and keep `claude/PROGRESS.md` updated.** ✅ done.

---

## ⚠️ TWO PLACES THE USER'S EXAMPLES CONTRADICT THE SOURCES

Both resolved **in favour of the PDF**, because the same message said to follow
the sources strictly. Both are written down rather than settled silently, and
**the next session should raise them with the user** if there is a chance to.

1. The user said an HR Manager **cannot create an attendance record**. PDF §3
   gives HR Manager *full CRUD on Attendance*. Resolved for the PDF, but split
   by intent: an employee's own check-in is a **punch** (own record, today only,
   network-gated); an HR Manager's is a **correction** (any record, any date,
   flagged `is_manually_edited` and written to the audit log).
2. The user said a **Payroll Manager sees only employee details and holidays**.
   PDF §3 gives the Payroll Manager everything an HR Payroll User has *plus*
   full CRUD on payruns, payslips, structures and rules. Resolved for the PDF.

---

## THE OPEN QUESTION — PRD criterion 4 in the *default* seed

Criterion 4 wants "at least two distinct warnings before validation". It is met
on the 250-person roster. On the **22-person demo seed only `AC_MISSING` fires**.

Session 05 investigated and **deliberately did not fix it**, because every fix
damages the rehearsed demo:

- `NO_CONTRACT`, `NEGATIVE_NET` and `NO_STRUCTURE` are **ERROR** severity and
  block Validate. Seeding one breaks demo steps A8/A9.
- `DUPLICATE` is warning-severity and is the problem statement's own named
  example — but it needs a pre-existing payslip for March 2026, and
  `dashboard/api.py:49` defaults the dashboard period to `Payrun.objects
  .order_by("-period_start").first()`. Seeding a March payrun would make the
  dashboard open on March with one payslip, wrecking demo step C1.

**Options for the next session**, in preference order:
1. Demo on `--employees 250`, where both codes fire naturally. Costs: every
   figure quoted in `demo-script.md` changes and must be re-measured.
2. Seed the March off-cycle payrun anyway and change the dashboard's default
   period to the newest **PAID** payrun rather than the newest one.
3. Leave it and say so — one criterion of six, and the engine demonstrably
   supports all six codes.

**Ask the user.** Do not pick silently.

---

## LOCKED-IN CONTEXT

See `claude/context/decisions.md`. Do not reopen.

| | |
|---|---|
| **Stack** | React 19 + Vite · Django 6.1 + DRF 3.18 · **SQLite** *(D-011)* |
| **Scope** | Full spec + 3 integrations *(D-002)* — all built |
| **Locale** | India, ₹, PF / ESIC / PT / LWF, single company *(D-003)* |
| **Repo** | `https://github.com/MeghRaval30/odoo_2026` |
| **Git identity** | Each session commits as its own teammate *(D-009)* |
| **Commits** | No machine attribution *(D-010)*, no character tag *(D-018)* |
| **Roles** | Five, from PDF §3; an account may hold several and gets the union *(D-025)* |
| **Themes** | Six, per browser not per account *(D-027)* |
| **Context folder** | Updated **only** at MEGATRON LAUNCH *(D-012)* |

---

## STILL UNRESOLVED FROM SESSION 04 — "remove your commits"

Untouched, because it needs the user. Every commit in the repository is authored
by one of the three teammates; exactly one (`12a632f`, the root scaffold commit)
carries a Claude co-author trailer, and that trailer is why `claude` appears in
GitHub's contributor list. Removing it means rewriting ~120 commits and
force-pushing, which would break the other teammates' clones. Force-push and
`filter-branch` are denied in `.claude/settings.json` by design.

**Ask before touching history.**
