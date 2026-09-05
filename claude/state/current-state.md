# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:   2026-09-05   10:00 IST   ✅ confirmed by the user
Hackathon end:     2026-09-06   10:00 IST   ✅ confirmed by the user
Session 06 closed: 2026-09-05   22:50 IST   (wall clock, `date`)
Elapsed:           ~12h 50m  /  24h
REMAINING:         ~11h 10m
Phase:             BUILD  (>8h) — but see the note below
```

**Run `date` yourself** and recompute before making any scope call.

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only. Touch nothing |

**The gate says BUILD, and you should behave as though it says FREEZE.** There
is no feature left on the board that the graded deliverables need. The board is
complete apart from the demo script, and the one remaining risk is breaking
something that works. Prefer rehearsal over refactoring.

---

## ⚠️ TWO SESSIONS ARE RUNNING IN PARALLEL — read this first

`origin/main` picked up two commits during this session from **another live
session that also calls itself session 06, as Michael** (`a7c4d3d`, `a1ae6a7` —
"open session 06 (Michael) — boot, rebase resolution, startup verification").
They touched only `claude/state/runbook.md` and
`claude/workflow/session-log.md`; this session touched neither, so the merge was
clean.

**But the relay is no longer a single file.** Before you write anything:

```bash
git fetch origin && git log --oneline -5 origin/main
```

and expect `claude/` files — especially `session-log.md`, `PROGRESS.md` and this
one — to have been edited by somebody who is not you. Merge, do not overwrite.

**A second, related trap.** `main` cannot be checked out in this worktree: it is
held by an abandoned worktree at `.claude/worktrees/frontend-routing-setup-e9a159`,
whose local `main` ref is stale at `ba294be`, far behind the real one. Do not
trust the local `main` ref. Work against `origin/main`:

```bash
git checkout -b integrate/<something> origin/main
git merge --no-ff <your-branch> -m "merge: ..."
git push origin HEAD:main
```

That is how this session's work reached `main` at `1437c25`.

---

## WHERE WE ARE

Sessions: 01 Michael (backend) · 02 Franklin (frontend) · 03 Trevor (tests,
deliverables) · 04 Michael (audit, correctness) · 05 Franklin (RBAC + UI
commission, ~70%) · **06 Trevor (this one — finished the commission).**

**The commission the user gave in session 05 is now complete.** Every task on the
board is `DONE` except the demo script (T-107). The product works end to end and
has been driven by hand, as all five roles, this session.

---

## ✅ WHAT WORKS — verified, with the command or click-path that proves it

### Harnesses — all green at 22:45 IST

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py test              # 218/218 OK   ← 2 new
./.venv/Scripts/python.exe verify_rules.py             # 28/28
./.venv/Scripts/python.exe smoke_api.py                # 51/51  (needs the server)
./.venv/Scripts/python.exe probe_forms.py              # 26/26  (needs the server)
./.venv/Scripts/python.exe manage.py seed --flush      # the harnesses dirty the DB
```

`npm run build` clean, 748 kB JS.

> **The venv is not in this worktree.** It lives in the main checkout at
> `C:/Users/raval/Desktop/odoo_2026/project/backend/.venv/Scripts/python.exe`.
> Run that interpreter against this worktree's `manage.py`; the SQLite file is
> created per worktree from `BASE_DIR`, so each worktree has its own database.
> `npm install` is also needed once per worktree.

### The seed, after this session's change

```
22 employees | 24 contracts | 1746 attendance | 11 leave requests
4 payruns | 61 payslips | 976 lines | 6 warnings
December ₹14,73,360 · January ₹14,82,320 · February ₹15,58,667.87   (unchanged)
```

The fourth payrun is new and deliberate: `March 2026 (off-cycle correction)`,
one payslip for **Vikram Rao**, left at **Computed**. See PRD criterion 4 below.

### Driven by hand in a browser this session

| Signed in as | Observed |
|---|---|
| `john@oxp.com` Employee | Menu is exactly Dashboard · Attendance · Time Off · My Payslips. `/employees`, `/payroll`, `/users`, `/security`, `/salary-rules` all answer **"Not available for this account."** Attendance shows his own 80 rows and no New Record. Allocations shows his one row, no New Allocation. My Payslips lists three, opens his own detail, and the PDF is 76 kB of real `%PDF-1.4` |
| `sara@oxp.com` HR Manager | All 13 of her routes render; every payroll and admin route refuses. Sees Approve/Refuse on ten of eleven leave requests |
| `rahul@oxp.com` Payroll User | Reaches payroll. Salary Rules opens **read-only** — no New Rule, and the rule form offers Close with no Save. `/users`, `/security`, `/audit` refuse |
| `aarav@oxp.com` Payroll Manager | Same screen with New Rule and Save present |
| `admin@oxp.com` Admin | All 18 routes render |

### The four screens session 05 never clicked — now all walked

Profile (all three tabs), Security, Audit log, My Payslips, Admin dashboard.
Proven end to end, each with the state restored afterwards:

- Direct profile field edited and saved; approval-gated bank change raised by
  John, **approved by Sara, and the value landed on the employee record**; a
  second request refused, and it did not.
- **Nobody decides their own** — Sara raising a request against her own record is
  refused with the server's sentence.
- **Password change** rotates the token, stores the new one and keeps the session
  alive; a subsequent `/api/employees/` call on the rotated token succeeds.
- **Security** — a network policy added through the UI; switching enforcement on
  from an address it does not cover is refused **and now says why**; adding a
  policy that covers the address then succeeds.
- **Audit log** captured every one of those actions, and its filter and search
  both work.

### Six design languages — now actually applied

**They had never worked.** All six resolved to Ledger (see WHAT WAS BROKEN
below). Fixed, and every one opened on a dashboard, a kanban, a table and a
modal: Ledger, Console, Atrium, Blueprint, Marigold, Graphite. No horizontal
page overflow in any of them, measured. Charts follow the theme and re-colour
live when it is switched.

### PRD success criterion 4 — met on the demo seed

```
March payrun over the eligible 20 →  19 payslips
  AC_MISSING x2   (Anita Oliver, Meera Iyer)
  DUPLICATE  x1   (Vikram Rao — already has a March payslip, skipped)
  severities: all WARNING       can_validate: True
```

Two distinct codes, and `[Validate]` still available so demo steps A8/A9 survive.

---

## ❌ WHAT WAS BROKEN, AND IS NOW FIXED

Recorded because each was invisible from the code and only fell out of clicking.

1. **All six themes resolved to Ledger.** `index.css` must `@import themes.css`
   at the top and then declares Ledger's defaults on a bare `:root`. `:root` and
   `[data-theme="x"]` have identical specificity, so the *fallback* won every
   time. The switcher highlighted the right swatch and stored the choice, and not
   one token changed. Fixed by `:root[data-theme="x"]`.
2. **An employee saw Approve and Refuse on their own pending leave request.**
   The server refused, so nothing could be approved — but the screen advertised
   the opposite of the rule.
3. **A refused security toggle flipped back in silence.** `patch()` set the error
   then called `load()`, which cleared it on success. The best guard on the
   screen — the one that stops an admin locking everybody out — rendered as a
   broken checkbox.
4. **My Payslips printed `18.00 /`** — `expected_days` was on the detail
   serializer only and the screen reads the list.
5. **The chart palette was a hand copy of Ledger's tokens** — a terracotta line
   on Blueprint's electric blue, and invisible axes on both dark themes.
6. **Marigold's button labels measured 2.86:1**, below AA and below the 3:1
   large-text floor. Now 5.28:1.
7. **Typing `#/payroll` as an HR Manager rendered the Payruns screen** — empty
   table, "0 records", a permission error underneath. It looked broken rather
   than refused.

---

## ❌ WHAT IS BROKEN NOW

**Nothing known to be broken.** Two things are true and worth knowing:

1. **One account cannot hold two live sessions.** Every sign-in deletes that
   account's token and issues a fresh one, deliberately, so `token.created` is
   the start of *this* session. Signing in as `admin@oxp.com` in a second tab
   silently kills the first, which lands on the login screen. It caught this
   session twice while driving the app. **Use one tab per account.**
2. **Ledger's primary button is 3.05:1** — white on Claude orange, below WCAG AA
   for 13px labels. This is inherited, is fixed by `ui-design-language.md` §2,
   and is the product's signature look, so it was **reported rather than changed
   at hour 13**. It is the user's call. Marigold had the same failure at 2.86:1
   and was fixed, because nobody had ever seen Marigold.

---

## 🔶 WHAT IS HALF-DONE

### T-107 — the demo script is stale, and this session made it staler

`claude/deliverables/demo-script.md`, 257 lines. It was rehearsed and stamped in
session 04 and describes the pre-RBAC menu. **Four steps now quote wrong
numbers**, all because of the criterion-4 change:

| Step | Line says | Reality |
|---|---|---|
| **A3** | "Three payruns, all paid." | **Four** — three paid plus `March 2026 (off-cycle correction)` at Computed |
| **A5** | "Twenty payslip shells" | **Nineteen.** The button still reads `Create payrun (20)`: twenty are selected, Vikram Rao is skipped |
| **A7** | "0 error(s), **2** warning(s)" | "0 error(s), **3** warning(s)" — and now **two kinds**, which is the improvement |
| **C1** | "It opens on March 2026" | Still true. After A9 the demo's March run is paid, and the dashboard opens on the newest **paid** period |

A8, A9, A10, all of Scenario B, and C2/C3 are untouched. December ₹14,73,360,
January ₹14,82,320 and February ₹15,58,667.87 are unchanged.

**Three things to add**, in value order:

1. A new beat at A7: *"and it found a second kind of problem — somebody was
   already paid for March off-cycle, so it skipped him and told me why."* That is
   the problem statement's own named example, live.
2. A third scenario: sign in as `john@oxp.com` and show the Payroll menu is
   **absent**, not greyed out. Stronger than any permissions table.
3. The theme switcher in the avatar menu — six complete design languages, one
   click apart. It now actually works.

### The wizard rehearsal was interrupted mid-step

MEGATRON LAUNCH arrived with the New Payrun wizard open at step 1. The criterion-4
numbers above are proven by test and by a direct engine run, **not** by walking
the wizard in the browser. Walking A3 → A10 once is the first thing to do.

---

## 🎯 THE SINGLE NEXT ACTION

```bash
git fetch origin && git log --oneline -5 origin/main     # another session is live
cd project/backend
netstat -ano | grep -E ":(8000|5173).*LISTENING"          # B-021 and B-027
./.venv/Scripts/python.exe manage.py seed --flush
./.venv/Scripts/python.exe manage.py runserver            # terminal 1
cd ../frontend && npm install && npm run dev              # terminal 2
```

Then sign in at `http://localhost:5173` as `aarav@oxp.com` / `demo1234` and
**walk demo steps A3 → A10 once**, writing the real numbers into
`claude/deliverables/demo-script.md` as you go. That is T-107 and it is the only
task left on the board.
