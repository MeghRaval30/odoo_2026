# CURRENT STATE

> **This is the first file the next session reads.** Rewrite it completely at
> every heartbeat and at MEGATRON LAUNCH. Be honest — an optimistic status
> report is worse than useless, because the next session will build on top of
> something that does not work.

---

## ⏱ CLOCK

```
Hackathon start:  2026-09-05  ~09:00 IST   ⚠️ ASSUMED — CONFIRM WITH USER
Now:              2026-09-05   10:15 IST
Elapsed:          ~1h 15m  /  24h
REMAINING:        ~22h 45m
Phase:            SETUP → PLANNING
```

### Scope gates — these are binding

| Remaining | Phase | What you are allowed to do |
|---|---|---|
| > 8h | **BUILD** | New features, per the task board |
| < 8h | **FREEZE** | Bugfix and polish only. No new features, no matter how good the idea. |
| < 4h | **POLISH** | Stop coding. Seed data, demo rehearsal, roadmap writeup. |
| < 2h | **DEMO** | Rehearse the demo only. Touch nothing. |

---

## WHERE WE ARE

Setup and planning. **No application code has been written yet.**

Michael's session so far has: researched the global HR/payroll feature landscape,
read and digested both source documents (the PDF problem statement and the
Excalidraw mockup), designed this relay system, and scaffolded the repository.

---

## ✅ WHAT WORKS (verified)

- Repository scaffolded at `D:\Btech\Odoo Hackathon 2026`
- `claude/` context system in place with the workflow spine written
- Source documents preserved untouched in `claude/source/`
- Remote confirmed reachable and **empty**:
  `https://github.com/MeghRaval30/odoo_2026`
  (verified via `git ls-remote` returning no refs)

## ❌ WHAT IS BROKEN

Nothing yet — nothing has been built.

## 🚧 WHAT IS HALF-DONE

- **The PRD** (`claude/context/prd.md`) — this is the active work item.
  Structure agreed with the user; content not yet written.
- **Data model** (`claude/context/data-model.md`) — entity and field list is
  fully derived from the mockups and captured in `product-spec.md`, but has not
  yet been turned into a normalised schema.

## ⬜ NOT STARTED

Everything in `project/`. No backend, no frontend, no database.

---

## ➡️ THE SINGLE NEXT ACTION

Write `claude/context/prd.md`, then `claude/context/data-model.md`, then
scaffold the Django project in `project/backend/`.

---

## LOCKED-IN CONTEXT

Settled with the user. Do not reopen — see `claude/context/decisions.md`.

| | |
|---|---|
| **Stack** | React + Python (Django / DRF) + PostgreSQL |
| **Team** | 3 people, relaying across 3 Claude accounts |
| **Scope posture** | Full spec **plus** three unrequired connections: attendance-driven worked days/LOP, overtime feeding a salary rule, leave reflected in payroll |
| **Locale** | India — ₹, with PF / ESIC / PT / LWF deduction rules, per the mockup |
| **Companies** | Single seeded company; `Company` field present and filterable |
| **Repo** | `https://github.com/MeghRaval30/odoo_2026` (owner: MeghRaval30) |

---

## ⚠️ OPEN QUESTIONS FOR THE USER

1. **Exact hackathon start and end time** — the clock above is assumed. Everything
   in the scope gates depends on this being right. Confirm early.
2. Whether a deployed/hosted demo is required, or a local walkthrough suffices.
