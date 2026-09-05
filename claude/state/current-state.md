# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:   2026-09-05   10:00 IST   ✅ confirmed by the user
Hackathon end:     2026-09-06   10:00 IST   ✅ confirmed by the user
Session 07 closed: 2026-09-06   01:05 IST   (wall clock, `date`)
Elapsed:           ~15h 05m  /  24h
REMAINING:         ~8h 55m
Phase:             BUILD by the gate — behave as FREEZE. See below.
```

**Run `date` yourself** and recompute before making any scope call.

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only. Touch nothing |

**The gate says BUILD by a few minutes. Behave as though it says FREEZE.**
There is no feature left that the graded deliverables need. The single thing
standing between this build and the grade is that **the demo has not been
walked end to end since the permission model was rebuilt**. Rehearse before you
build anything.

---

## THE ONE-LINE STATUS

The product is complete and verified; the *demo script* is corrected on paper
but unrehearsed against the new UI. **Go rehearse it.**

---

## ✅ WHAT WORKS — verified this session, with the proof

Everything below was run or clicked after the last commit. Nothing here is
inferred.

### The five harnesses, all green at 00:55 IST

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py test            # 231 tests OK
./.venv/Scripts/python.exe verify_rules.py           # 28/28 — the graded rules
./.venv/Scripts/python.exe audit_permissions.py      # every cell + 16 refusals
./.venv/Scripts/python.exe smoke_api.py              # 53/53 — the HTTP layer
./.venv/Scripts/python.exe manage.py seed --flush    # smoke_api dirties the DB
# probe_forms needs a live server in another terminal:
./.venv/Scripts/python.exe manage.py runserver
./.venv/Scripts/python.exe probe_forms.py            # 26/26
```

**The harnesses no longer dirty the demo** (D-046). Run the whole pass
immediately before presenting if you like; it now leaves 5 accounts, network
enforcement off and sessions not IP-bound.

### A robustness pass that found two real bugs

| Probe | Scale | Result |
|---|---|---|
| Route + query fuzz | 2,499 requests — every route × 5 roles × 19 malformed query strings, real/missing/nonsense ids, anonymous, forged token | **0 crashes, 0 anonymous leaks** |
| Payslip invariants | 61 payslips × 12 invariants | found the attendance/schedule bug |
| Engine edge cases | no contract, zero wage, ₹99,99,999 wage, mid-period join, mid-period leave | all handled |
| Frontend route walk | 22 routes × Admin and Employee, console + network instrumented | found the My Payslips bug; **0 console errors** |
| Idempotency / PDF / register | recompute twice, paid-run lock, 12 PDFs, register export | all clean |

The probe scripts were **deliberately not committed** — the two findings worth
keeping became real tests in `core/tests.py` and `accounts/tests.py`. The
technique is written up in the traps section of the next-session prompt; it is
worth twenty minutes to repeat if you change anything structural.

### The permission model, rebuilt and enforced

| Role | Authority |
|---|---|
| Employee | Own records only |
| **HR Manager** | **Owns people** — employee records, contracts and wages, leave decisions and allocations, attendance corrections, HR configuration |
| **HR Payroll User** | **Reads payroll, writes nothing.** Nine capabilities, all reads |
| **HR Payroll Manager** | **Runs the payrun, owns none of its inputs.** Create, compute, validate, pay, delete. On employees, contracts and attendance it is byte-for-byte the Payroll User |
| Admin | The only account holding both sides, plus users, security, audit |

Proven by `audit_permissions.py`: every matrix cell, **16 specific refusals**
across the two payroll ranks, **6 preserved reads**, a read-breadth check that
each role still sees everyone it should, and an identity check that the two
payroll ranks are indistinguishable on people data across 12 method/resource
cells.

### Verified in a browser this session

* All 22 routes render as Admin, zero console errors
* All 22 routes as an Employee — permitted ones render, the rest say *"Not
  available for this account."*, zero console errors, zero failed requests
* Payroll User: New Payrun absent, payrun action row absent, Export Register
  present, employee/schedule/reference forms open read-only with `Close`
* Payroll Manager: the full payrun action row present, Time Off Types gone from
  the menu, Working Schedules read-only (29 controls inert, derived
  *40.00 hours / 5 days* still readable)
* Admin: Reports → Payroll Dashboard opens the money view; New User shows radios
  and a second pick replaces the first

---

## 🐞 WHAT IS BROKEN

**Nothing is broken.** All five harnesses are green, the build is clean, and
every flow above was driven by hand after the last commit.

Three things are *imperfect* and are recorded as blockers, not breakage:

* **B-031** — the demo script's February figure moved (corrected in this pack,
  but anyone who memorised ₹15,58,667.87 must be told it is now ₹15,58,320.41)
* **B-032** — `/api/attendance/status/` and `/api/me/profile/` answer 400 for an
  account with no employee record. Cosmetic; both screens handle it well
* **B-033** — the frontend has no automated tests, and both bugs found this
  session were frontend

---

## 🚧 WHAT IS HALF-DONE

### The demo script — corrected on paper, unrehearsed in the browser

`claude/deliverables/demo-script.md` now carries a **"Session 07 corrections"**
section at the end and three inline figure fixes. What it has *not* had is a
person walking it against the current UI. Since it was last rehearsed:

* the whole permission model changed (D-041 to D-044)
* the menus changed for three of five roles
* **Reports → Payroll Dashboard** is new
* the New User dialog uses radios
* the wordmark is larger

**This is T-107 + T-112 and it is the top of the board.** Do not assume a step
still works because it is written down.

### T-111 — Ledger's primary button is 3.05:1

White on Claude orange fails WCAG AA for 13px labels. Marigold had the same
fault at 2.86:1 and was fixed because nobody had seen it; Ledger is the shipped
signature look and is fixed by `ui-design-language.md` §2, so session 06
reported it rather than changing it. **One token closes it** (`--on-primary` or
a darker `--primary`). It needs the user's call, not a session's.

---

## ⛔ NOT STARTED

* **T-089 — the 300–10,000 employee dataset.** The user deferred it twice and
  re-sequenced it behind AI work, which is itself now dead (see below). The seed
  already takes `--employees N` and generates above 22, so this is a run of that
  flag plus checking the dashboard survives the row count. Only after rehearsal.
* **T-126 / T-127** — see blockers B-032 and B-033.

### Dead: the AI features

The user asked for AI to manage a large dataset, chose **local Ollama models**,
then asked for **Ollama to be uninstalled** — which was done at the start of
this session. Nothing was built and no code references it. Do not resurrect this
without the user asking: the remaining route is the Anthropic API, which sends
salary data off the machine, and that was the exact thing local models were
chosen to avoid.

---

## ▶️ THE SINGLE NEXT ACTION

Start both servers, sign in as `aarav@oxp.com`, and walk demo scenario A from
step A1 to A10, writing down **the number actually on screen** at every step.

```bash
cd project/backend && ./.venv/Scripts/python.exe manage.py seed --flush
./.venv/Scripts/python.exe manage.py runserver          # terminal 1
cd project/frontend && npm run dev                      # terminal 2
```

Then open `claude/deliverables/demo-script.md`, read the **"Session 07
corrections"** section at the bottom first, and fix every figure that disagrees
with what you saw. Trust the screen over the document.

---

## ⚠️ TRAPS THAT COST TIME THIS SESSION

1. **Any login rotates that account's token.** `accounts/api.py:186` deletes
   every existing token for a user before issuing a new one. Running any harness
   signs out a browser logged in as one of the five demo accounts. This looks
   exactly like a session timeout and is not one — it cost ~30 minutes and a
   background poller to prove.
2. **Never print non-ASCII from a management command or a script** (B-006). It
   killed a packing script mid-run tonight, after the first file was already
   edited in memory but before it was written.
3. **Heredocs mangle escapes.** `\n` inside a `python - <<'PYEOF'` heredoc
   became a real newline and produced an unterminated string. Write the script
   to the scratchpad with the Write tool and run it (B-020).
4. **`worked_days > expected_days` is a real signal, not noise.** Twice now it
   has meant the seed generated attendance the contract does not allow.
