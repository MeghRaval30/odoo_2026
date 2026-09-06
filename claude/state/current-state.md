# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> MEGATRON LAUNCH. Be honest — an optimistic status report is worse than
> useless, because the next session builds on top of something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:   2026-09-05   10:00 IST   ✅ confirmed by the user
Hackathon end:     2026-09-06   10:00 IST   ✅ confirmed by the user
Session 09 closed: 2026-09-06   06:20 IST   (wall clock, `date`)
Elapsed:           ~20h 20m  /  24h
REMAINING:         ~3h 40m
Phase:             POLISH — stop coding. Demo script, rehearsal, roadmap
```

**Run `date` yourself** and recompute before making any scope call. DEMO phase
begins at 08:00 IST.

| Remaining | Phase | What you may do |
|---|---|---|
| > 8h | BUILD | New features, per the task board |
| < 8h | FREEZE | Bugfix and polish only |
| < 4h | **POLISH** | **Stop coding. Seed data, demo rehearsal, roadmap** |
| < 2h | DEMO | Rehearse only. Touch nothing |

**You are in POLISH.** Do not start a feature. The product is larger than it
has ever been and the thing it now lacks is not code — it is a demo script that
describes what is actually on screen.

---

## THE ONE-LINE STATUS

Session 09 built an AI data-migration studio and a bulk workforce ecosystem to
the user's brief, all Admin-only, all tested — and **never touched the demo
script, which is now the single most valuable open task and is worse than when
the session began.**

---

## ⚠️ THE SINGLE NEXT ACTION

Open `claude/deliverables/demo-script.md`. It is stale in two ways: its prose
predates the permission rebuild (the old T-107 / B-031), **and** an entire
top-bar menu group now exists that it does not mention at all (B-036).

Concretely:

1. `cd project/backend && ./.venv/Scripts/python.exe manage.py seed --flush`
2. Start both servers (see `runbook.md`).
3. Sign in as `aarav@oxp.com` / `demo1234`. **Read scenario A aloud, A1 to A10,
   against the screen**, and correct the words wherever they no longer match.
4. Do the same for scenario B as `john@oxp.com` then `sara@oxp.com`.
5. **Add a scenario C for the Import Studio**, signed in as `admin@oxp.com`.
   The narration is already written — `test-data/README.md` describes what each
   file proves, and the step-by-step flow is in §14 below.

Fold in the five changes session 08 listed that were never applied: Reports
opens on February 2026 with 20 payslips; the register exports as
`register-February-2026.csv`; **Employees → Change Requests** is a menu entry;
a submitted leave request reads *To Approve*; the Administration dashboard
opens on an empty audit log after a reseed and fills as the demo signs in.

---

## ✅ WHAT WORKS — verified this session, with the proof

Everything below was run or clicked after the last commit.

### The harnesses, all green at 06:00 IST

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py test            # 314 tests OK  (was 236)
./.venv/Scripts/python.exe verify_rules.py           # 28/28 — the graded rules
./.venv/Scripts/python.exe audit_permissions.py      # every cell + 16 refusals
./.venv/Scripts/python.exe smoke_api.py              # 53/53 — the HTTP layer
./.venv/Scripts/python.exe manage.py seed --flush    # smoke_api dirties the DB
# probe_forms needs a live server in another terminal:
./.venv/Scripts/python.exe manage.py runserver
./.venv/Scripts/python.exe probe_forms.py            # 26/26
./.venv/Scripts/python.exe manage.py ai_doctor       # all pass, 711 ms warm
```

`npm run build` is clean (~835 kB JS, 35 kB CSS).

**`verify_rules.py` is now scale-independent** and passes 28/28 at both 22 and
200 employees. It previously asserted `min(no_bank, 2)` missing-account
warnings, which is true only of the 22-person seed; at 200 it failed and the
*product was right*.

### The everything that was already working still works

The five graded rules, the permission matrix, both approval workflows, criterion
4 through the wizard, 22 original screens. Nothing from sessions 01–08 was
changed except `verify_rules.py`, `seed.py` (additive), `capabilities.py`
(additive), `config/settings.py`, `config/urls.py` and `accounts/security.py`
(two new audit actions).

### New: the Import Studio — walked end to end in a browser

Sign in as `admin@oxp.com`, **Workforce → Data Import**, drag in
`test-data/import/04-fieldforce-incomplete.xlsx`:

* Header found, 7 columns colour-coded, *"Read 7 headers. Mapped 7
  automatically. qwen2.5:7b answered in 4.0s. Whole analysis 5.1s."*
* **Complete the data** checklist lists what the file lacks: Work email
  (blocking), Bank account, IFSC, PAN, and employee numbering.
* **Build from names** → work email resolved, ticks green, Preview unlocks.
* **Fetch from a file** → drop `04b-fieldforce-bank-details.xlsx` → joins itself:
  *"14 of the 16 values in 'Staff ID' also appear in 'Staff ID'"*, and it names
  the two people finance never sent (Anita Kumari, Pushpa Sharma).
* **Choose numbering** → live preview `EMP/2021/0023 …`, continuing from the 22
  codes already issued rather than colliding.
* **Preview** → before/after per cell, values from the second file tinted and
  captioned *"from 04b…"*, generated codes marked, five unimportable rows greyed
  with reasons.
* **Import 11 employees** → 11 employees + 11 contracts + 2 departments.

`01-meridian-complete.xlsx` imports 22/22 with zero issues (the control case).
`03-northgate-legacy-export.xlsx` proposes `scale ÷12` on `ANNUAL_CTC` and shows
~~1080000~~ → **90000.00**.

### New: the workforce screens — walked in a browser

**Segments**: typed *"interns who have been here more than 6 months"* → badge
reads **LOCAL MODEL**, the model's reading types out, the compiled rule renders
in English, editable fields beneath, and *"Matches 2 people — Dev Malhotra,
Tanya Shah"*.

**Playbooks**: `manage.py run_playbooks --dry-run` reports *"Bond ends 06 Oct
2026, 2 months left"* and *"12 months served as of 06 Sep 2026"* against the
seeded data.

### New: Admin-only enforcement — verified as enforcement, not decoration

All nine `intel/` and `workforce/` endpoints answer **403** to the HR Manager,
both payroll ranks and the Employee, on reads *and* writes. The **Workforce**
menu group is absent for all four. `admin@oxp.com` gets 200/201 throughout.

---

## ❌ WHAT IS BROKEN

**Nothing is broken.** No known failing test, no known broken screen, no
regression from this session's work.

That is not the same as "nothing is wrong" — see below.

---

## 🟡 WHAT IS HALF-DONE

### The demo script — `claude/deliverables/demo-script.md`

**Not started this session, and now further behind.** This is B-036 and it is
the top task. Detail in *The single next action* above.

### The 240-row import has not been watched in a browser — B-037

`test-data/import/06-vantage-240-headcount.xlsx` was generated and the pipeline
is proven at that size **through the API only**. The studio UI has not been seen
doing it.

Low risk: the render is bounded (the grid shows 14 rows, the preview 25 records,
the issues list 40) and the code path is identical to the files that were
walked. But it has not been watched, and it is the file you would want to show
for scale. **Ten minutes to check.**

### Seed size is an open question with the user — T-157

The user asked for "at least 200 employees" for the non-AI features.
`--employees 200` is verified working, and D-066 chose **not** to make it the
default, because the demo script's whole three-month narrative quotes figures
that only hold for the 22-person roster. The scale story is told through the
240-row import instead.

**This choice was made without the user confirming it.** Ask.

---

## 📋 WHAT IS NOT STARTED

In priority order — the full list is in `task-board.md`.

1. **T-107 / B-036 — the demo script.** Everything else is optional.
2. **T-156 / B-037** — walk the 240-row import in a browser. Ten minutes.
3. **T-157** — confirm the seed size decision with the user.
4. **T-134 / B-034** — the leave self-approval guard. Real, small, unreachable
   in the demo.
5. **T-126 / B-032** — two reads answer 400 for an account with no employee.
   Cosmetic; deliberately left alone four times now.
6. **T-127 / B-033** — a frontend test runner. This session is more evidence for
   it: six of the nine defects found were frontend or frontend-adjacent, and
   every one was found by hand.
7. **T-111** — Ledger's primary button is 3.05:1, failing WCAG AA at 13px. One
   token closes it, but Ledger is the shipped signature look and is fixed by
   `ui-design-language.md` §2, so it needs the user's decision. **Carried
   unasked across four sessions.**

### Dead — do not resurrect without the user asking

Nothing new is dead. Note that the "AI features are dead" entry in session 08's
briefing is **superseded**: the user re-commissioned them in session 09 and they
are now built, tested and shipped on `main`.

---

## 🔒 SCOPE GATES

You are in **POLISH**. The build is done. The risk from here is breaking
something that works.

If you are about to write a new feature, stop and ask whether the demo script is
finished first. It is not.

---

## GIT

`main` is at the session 09 handoff commit — see the closing report in
`session-log.md` for the SHA and tag.

Four feature branches from this session are pushed and preserved:
`feat/ai-import-studio`, `feat/workforce-operations`,
`feat/ai-setup-and-test-data`, `feat/import-enrichment`, plus the original
working branch `feat/intelligence-layer`.

**`main` cannot be checked out here** (B-029, confirmed and characterised as
B-038). It is held by `.claude/worktrees/frontend-routing-setup-e9a159` at a ref
**41 commits behind `origin/main`**. Base new work on `origin/main` and push
with `git push origin HEAD:main`. Do not try to repair the other worktree.
