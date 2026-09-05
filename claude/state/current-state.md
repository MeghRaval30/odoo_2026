# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:   2026-09-05   10:00 IST   ✅ confirmed by the user
Hackathon end:     2026-09-06   10:00 IST   ✅ confirmed by the user
Session 08 closed: 2026-09-06   03:10 IST   (wall clock, `date`)
Elapsed:           ~17h 10m  /  24h
REMAINING:         ~6h 50m
Phase:             FREEZE — bugfix and polish only
```

**Run `date` yourself** and recompute before making any scope call. POLISH
begins at 06:00 IST; DEMO at 08:00 IST.

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | BUILD | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | POLISH | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | DEMO | Rehearse only. Touch nothing |

**There is no feature left that the graded deliverables need.** The board has
been feature-complete since session 06. Everything since has been finding and
repairing defects.

---

## THE ONE-LINE STATUS

Five real bugs were found and fixed this session by *using* the product rather
than running the harnesses; the build is green and the demo script is still
unrehearsed on paper. **T-107 is the last real task.**

---

## ✅ WHAT WORKS — verified this session, with the proof

Everything below was run or clicked after the last commit. Nothing is inferred.

### The five harnesses, all green at 03:00 IST

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py test            # 236 tests OK
./.venv/Scripts/python.exe verify_rules.py           # 28/28 — the graded rules
./.venv/Scripts/python.exe audit_permissions.py      # every cell + 16 refusals
./.venv/Scripts/python.exe smoke_api.py              # 53/53 — the HTTP layer
./.venv/Scripts/python.exe manage.py seed --flush    # smoke_api dirties the DB
# probe_forms needs a live server in another terminal:
./.venv/Scripts/python.exe manage.py runserver
./.venv/Scripts/python.exe probe_forms.py            # 26/26
```

Frontend `npm run build` is clean (~750 kB JS).

### Both approval workflows now run end to end — walked in a browser

This is new, and it is the important half of the session.

* **Leave.** Sign in as `john@oxp.com`, Time Off → New Request, pick *Sick
  Leave*, submit. It now reads **To Approve** with no action offered to John
  himself. Sign in as `sara@oxp.com` → the same row carries **Approve** and
  **Refuse**; approving moves it to **Approved**.
* **Profile changes.** As `john@oxp.com`, Profile → *Needs HR approval* →
  Request on a sensitive field. As `sara@oxp.com` it appears under
  **Employees → Change Requests** and in the HR dashboard's *Personal detail
  changes* panel, both with Approve/Refuse.

### Criterion 4 proven by clicking, not only by test

As `aarav@oxp.com`, New Payrun → name *March 2026*, 01–31 Mar 2026, Regular
Salary → Next → Create payrun (20):

| Step | What is on screen |
|---|---|
| On creation | 19 payslips, **1 warning** — `DUPLICATE`, Vikram Rao skipped |
| After Compute | **3 warnings, two distinct codes** — `AC_MISSING` ×2 (Anita Oliver, Meera Iyer) + `DUPLICATE` ×1, **0 errors** |

PRD success criterion 4 is therefore met on stage, not just in `core/tests.py`.

### Demo figures confirmed on screen

| Payrun | Net | State |
|---|---|---|
| December 2025 | **₹14,73,360.00** | Paid |
| January 2026 | **₹14,82,320.00** | Paid |
| February 2026 | **₹15,58,320.41** | Paid |
| March 2026 (off-cycle) | ₹84,684.37 | **Computed** — leave it |

Scenario B reads **Allocated 20.00 · Taken 2.00 · Remaining 18.00**, as the
script says. The allocation gate refuses with real wording: *"No approved Comp
Off allocation covering 2026-09-10 – 2026-09-11. An allocation must be created
and approved before this request can be submitted."*

### All 22 routes, all five roles, instrumented

`console.error`, `window.onerror`, unhandled rejections and `window.fetch` were
patched to collect `{route, message}`, then every route visited as each of the
five demo accounts. **Zero console errors, zero unexpected responses, correct
refusals everywhere.** The only 4xx observed is B-032, which is known and
deliberate.

Also verified by hand: paid-run lifecycle buttons are correctly disabled;
payslip PDF renders (76 kB, valid `%PDF-1.4`); check in / check out flips the
dot and updates the session; the register CSV refuses for an Employee (403).

---

## 🐞 WHAT IS BROKEN

**Nothing is broken.** All five harnesses are green, the build is clean, and
every flow above was driven by hand after the last commit.

Three things are *imperfect* and are recorded as blockers, not breakage:

* **B-032** — `/api/attendance/status/` and `/api/me/profile/` answer 400 for an
  account with no employee. Left alone deliberately three times now; both UIs
  handle it correctly and the change touches a demo path.
* **B-033** — no frontend tests. Every bug found in sessions 07 and 08 was found
  by driving a browser by hand. The instrumented route walk is the cheap
  substitute and is written up in the traps section of the handoff.
* **B-034** — leave approval has **no self-approval guard**, unlike profile
  changes. Not reachable in the demo. See blockers for why it was not fixed.

---

## 🔶 WHAT IS HALF-DONE

### T-107 — the demo script, corrected on paper, still unrehearsed as prose

**This is the last real task.** `claude/deliverables/demo-script.md` carries a
"Session 07 corrections" section and three inline figure fixes. Session 08
verified every *number* it quotes and walked the mechanics of scenario A and B
in a browser — but nobody has read the script aloud against the current screens,
and its **menu and role descriptions still predate the permission rebuild**.

What is now known to be true and should be folded in:

* Reports opens on **February 2026, 20 payslips** (it used to open on March)
* The register exports as `register-February-2026.csv`, one file per month
* **Employees → Change Requests** is a new menu entry (Admin and HR Manager only)
* An employee's leave request reads **To Approve**, not Draft
* The Administration dashboard opens on an empty audit log after a reseed, and
  fills as the demo signs in — every row a judge sees is something that just
  happened in front of them

### T-111 — Ledger's primary button is 3.05:1

White on Claude orange fails WCAG AA at 13px. One token (`--on-primary`, or a
darker `--primary`) closes it. **It needs the user's decision**, because Ledger
is the shipped signature look and is fixed by `ui-design-language.md` §2. It has
now been carried across three sessions unasked; if you have the user's
attention, ask.

---

## ▶️ THE SINGLE NEXT ACTION

```bash
git pull --rebase
cd project/backend
./.venv/Scripts/python.exe manage.py seed --flush
./.venv/Scripts/python.exe manage.py runserver     # terminal 1
cd ../frontend && npm run dev                      # terminal 2
```

Then open `claude/deliverables/demo-script.md`, sign in as `aarav@oxp.com` /
`demo1234`, and **read scenario A out loud from A1 to A10 against the screen**,
editing the script wherever the words no longer match what is in front of you.
The figures are already right — what is stale is the prose about menus and
roles.

Do that before anything else. Do not open new feature work.
