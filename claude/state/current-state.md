# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:  2026-09-05   10:00 IST   ✅ CONFIRMED BY USER (session 02)
Hackathon end:    2026-09-06   10:00 IST   ✅ CONFIRMED BY USER
Now:              2026-09-05   13:40 IST   (wall clock, `date`, not narrative)
Elapsed:          ~3h 40m  /  24h
REMAINING:        ~20h 20m
Phase:            BUILD
```

### Scope gates — binding

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap |
| < 2h | **DEMO** | Rehearse only. Touch nothing |

> **Run `date` yourself.** Session 01 recorded a handoff at "13:15 IST" that was
> ahead of the real wall clock. Session 03 (this one) opened the repo at 13:06
> and closed at 13:40. There is a great deal of time left — do not rush into
> freeze behaviour.

---

## WHERE WE ARE

**Backend and frontend are both complete and verified. Four harnesses are green.
Three documented product bugs were closed this session, and one screen that had
never worked at all was found and fixed.**

The remaining work is deliverables, rehearsal and optional polish — not features.

Sessions: 01 Michael (backend), 02 Franklin (frontend), 03 Trevor (tests,
deliverables, and this bug-fix pass).

---

## ✅ WHAT WORKS — verified, with the command or click-path that proves it

### Backend — four harnesses, all green as of 13:35 IST

```bash
cd project/backend
./.venv/Scripts/python.exe verify_rules.py   # 28/28 — the five graded rules
./.venv/Scripts/python.exe smoke_api.py      # 51/51 — the HTTP layer
./.venv/Scripts/python.exe manage.py test    # 158/158 — Django suite, 7 apps
# probe_forms.py needs a server running in another terminal:
./.venv/Scripts/python.exe manage.py runserver
./.venv/Scripts/python.exe probe_forms.py    # 26/26 — every UI create + update
```

**`probe_forms.py` needs a live server on :8000.** It drives real HTTP with
`urllib`, unlike `smoke_api.py` which uses Django's test client. Running it
without a server gives a `WinError 10061` traceback, not a clean message.

**Always `manage.py seed --flush` after `smoke_api.py`** — it writes an
`April 2026 (smoke)` payrun into the dev database and the dashboard then opens on
it (B-010).

### Frontend — verified by clicking, not by reading

Both servers, in two terminals:

```bash
cd project/backend  && ./.venv/Scripts/python.exe manage.py runserver
cd project/frontend && npm install && npm run dev      # http://localhost:5173
```

`npm run build` is clean (613 modules, ~5.8s). Sign in `admin@oxp.com` /
`demo1234`; the login card has one-click chips for all five roles.

**Payrun flow, driven end to end in a browser this session** (as admin, creating
a fresh March 2026 payrun):

| Step | Observed |
|---|---|
| Wizard step 1 | Scope only — no record created |
| Wizard step 2 | 20 employees, each with the contract **resolved for that period** — Aarav Mehta on his 01 Jan 2026 contract at ₹85,000 |
| Create Payrun | 20 payslips, Draft, all zeros |
| Compute | Gross ₹16,85,299.68 · Net ₹15,79,019.68 |
| Pre-validation | **0 errors, 2 warnings** — Anita Oliver and Meera Iyer, bank account missing — shown **before** Validate |
| Validate → Mark Paid | State machine advances; at PAID every action button is disabled |
| Payslip detail | "Contract resolved for this period" card (CON/2026/0001, ₹85,000) and "Salary computation — evaluated in sequence order" (seq 1, 10, 20, 30…) |

**Time Off self-service, driven as `john@oxp.com` (Employee):** the Payroll menu
is absent, the request list and attendance list are scoped to him alone, the New
Request form fills his name in read-only, the balance table loads on type
selection (Allocated 20 / Taken 2 / Remaining 18), a two-day Paid Time Off
request saves as Draft with duration **2.00**, and a same-day First-half Sick
Leave request saves with duration **0.50**.

### The five graded rules

All five are proven by `verify_rules.py` and the Django suite, and all five are
now visible in the UI:

1. **Period-based contract resolution** — payrun wizard step 2, the payslip's
   "Contract resolved for this period" card, and `Contracts → Resolve by period`.
2. **Derived weekly hours** — Working Schedules, no weekly-hours input exists.
3. **Allocation-gated leave** — the balance table on the request form, and the
   server's own refusal text when no allocation covers the request.
4. **Sequenced salary rules** — the payslip's computation table, ordered by
   sequence, gross and net derived from the lines.
5. **Pre-finalization warnings** — the payrun's pre-validation panel, populated
   before Validate is available.

### Seed evidence — live, not hardcoded

| Payrun | Net | Why it matters |
|---|---|---|
| Dec 2025 | ₹14,73,360 | Lower than Jan — two employees resolve to older, cheaper contracts |
| Jan 2026 | ₹14,82,320 | |
| Feb 2026 | ₹15,63,028 | Higher — February overtime reached payroll |

Feb filtered to Engineering alone: ₹5,03,998.

Counts: 22 employees, 24 contracts, 859 attendance, 11 leave requests, 3 payruns,
60 payslips, 840 lines, 6 warnings.

---

## ❌ WHAT IS BROKEN

**Nothing known.** All four harnesses green, `npm run build` clean, and the two
flows above were driven by hand in a browser after the last commit.

---

## 🚧 WHAT IS HALF-DONE

**Nothing is half-done in the code.** The working tree is clean, every branch is
merged into `main`, and `main` is pushed.

What is *unfinished* is rehearsal, and one specific risk:

### ⚠ The demo script has never been rehearsed against a running app

`claude/deliverables/demo-script.md` was written by session 03 partly from
source. **Scenario B steps B2–B3 are built on the New Time Off Request form,
which could not submit at all until this session fixed it** — the script's line
*"Submit, and it saves"* would have failed live on stage with
`half_day: "False" is not a valid choice`.

The form works now, and the fix is verified. But the script itself has not been
walked through, and two things in it are worth checking against the app:

- The form now has a **Half day** field (Full day / First half / Second half)
  between the date row and Reason. The script's click path does not mention it.
  The default is Full day, so the path still works — but a presenter reading the
  script will meet a field the script does not name.
- **B5 claims "Taken two. Remaining eighteen."** A newly submitted request is
  `DRAFT`, and `Allocation.taken` counts only **approved** requests — so the
  request submitted at B3 does not move the balance by itself. Check that B4
  actually approves it, or that the narration is talking about pre-existing
  seeded state. As written this is the step most likely to embarrass someone.

---

## ⬜ NOT STARTED

- **T-063 — demo rehearsal.** Nobody has walked the script end to end.
- **T-075 — frontend tests.** None exist. Lowest priority; the browser pass and
  `probe_forms.py` cover the same ground more cheaply for a 24h build.

---

## ➡️ THE SINGLE NEXT ACTION

Start both servers, sign in as `admin@oxp.com`, and **walk
`claude/deliverables/demo-script.md` from A1 to C2 with the script open beside
you**, correcting it in place wherever the app disagrees. Begin with Scenario B
steps B2–B5, which are the least trustworthy part of the document for the reasons
above.

That is a rehearsal *and* a correctness pass on a graded deliverable, and it is
the highest-value hour left in the project.

---

## LOCKED-IN CONTEXT

See `claude/context/decisions.md`. Do not reopen.

| | |
|---|---|
| **Stack** | React 19 + Vite, Django 6.1 + DRF 3.18. **SQLite, not Postgres** *(D-011)* |
| **Scope** | Full spec + 3 integration connections *(D-002)* — all three built |
| **Locale** | India, ₹, PF/ESIC/PT/LWF, single company *(D-003)* |
| **UI** | Anthropic warm palette, serif/sans pairing. **Binding:** `claude/context/ui-design-language.md` *(D-013)* |
| **Repo** | `https://github.com/MeghRaval30/odoo_2026` |
| **Git identity** | Each session commits as its own teammate *(D-009)* |
| **Commits** | No machine attribution *(D-010)*; **no character name in the subject either** *(D-018)* |
| **Context folder** | Updated **only** at MEGATRON LAUNCH *(D-012)* |

---

## ⚠️ OPEN QUESTIONS FOR THE USER

1. ~~Exact hackathon start and end time.~~ **ANSWERED:** 10:00 IST 05 Sep →
   10:00 IST 06 Sep.
2. Commit `12a632f` carries a Claude co-author trailer from before D-010. Fixing
   it needs a force-push, which is denied at settings level. Harmless; leave it.
3. **Still open, asked twice, never answered.** Is a deployed demo required, or
   does a local walkthrough suffice? It changes what the roadmap and the demo
   script should assume. Ask again early — it is cheap to ask and expensive to
   guess wrong at hour 22.
