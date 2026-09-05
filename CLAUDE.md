# ⚠️ YOU ARE PART OF A RELAY. READ THIS BEFORE ANYTHING ELSE.

This project is built by **three Claude sessions working in relay**, on three
separate Claude accounts belonging to three teammates:

> **MICHAEL → FRANKLIN → TREVOR → (repeat)**

You are one of them. You have **no memory** of the sessions before you. Every
handoff is a cold start in a brand-new chat, possibly on a different account and
a different machine. **This repository is the only channel between sessions.**
Anything not written to a file and pushed is lost permanently.

---

## Boot sequence — do this before your first edit

```bash
git pull --rebase
```

1. Read `claude/START-HERE.md` in full.
2. **Set and verify your git identity** — see below. Do this before any commit.
3. Read `claude/state/current-state.md` — the clock, the phase, what is broken.
4. Read `claude/state/task-board.md` — pick up the next unblocked task.
5. Skim `claude/context/decisions.md` — do not relitigate settled choices.
6. Append your opening entry to `claude/workflow/session-log.md`.
7. Announce to the user which character you are and what you are picking up.

---

## ⚠️ Git identity — get this right before your first commit

**Each character commits under their own teammate's GitHub account.** All three
must appear as authors on this repository. Identity follows the session, not the
machine.

```bash
git config user.name  "<your GitHub username>"
git config user.email "<your GitHub commit email>"
git config user.name && git config user.email    # VERIFY. Do not assume.
```

The identity register is in `claude/workflow/git-strategy.md` §1. If your row is
marked TBC, fill it in and commit that change first.

Getting this wrong is **not silently recoverable** — fixing misattributed commits
requires rewriting history, which is forbidden here.

## Branching is required

Work on branches, merge with `--no-ff`, tag versions. `main` stays working at all
times. Read `claude/workflow/git-strategy.md` before your first commit.

```bash
git checkout -b feat/<area>-<thing>
# ... work ...
git checkout main && git merge --no-ff feat/<area>-<thing>
```

---

## The trigger phrase: "MEGATRON LAUNCH"

When the user types **MEGATRON LAUNCH**, the session is at ~80–85% of its usage
limit.

**STOP all feature work immediately** and execute
`claude/workflow/megatron-checklist.md` end to end. Packing takes priority over
everything, including a task that is nearly finished. Do not negotiate for "just
one more thing" — the remaining capacity is the packing budget, and running out
mid-pack loses the handoff entirely.

---

## Non-negotiables

- `git pull --rebase` before your first edit. Always.
- **Verify your git identity before your first commit.** Every session.
- **Heartbeat commit every 30–45 minutes.** Never batch context to the end — a
  session that dies without warning must lose minutes, not hours.
- Append-only files are **never edited, only appended**:
  `session-log.md`, `decisions.md`, `prompt-history.md`.
- Never force-push. Never rewrite history. Never fast-forward merge.
- Merge your branch into `main` before packing at MEGATRON LAUNCH — never hand
  off with work stranded on an unmerged branch.
- One fact, one home. Task status lives only in `task-board.md`. Do not
  duplicate state across files — duplicated state diverges and misleads.
- Respect the scope gates in `current-state.md`. If under 8h remain, you are in
  feature freeze regardless of how good your idea is.

---

## Where things live

| Path | What it holds |
|---|---|
| `claude/workflow/` | How the relay operates; the session log |
| `claude/context/` | Stable knowledge: problem statement, spec, PRD, data model, decisions |
| `claude/state/` | Volatile truth: clock, task board, blockers, runbook |
| `claude/handoff/` | The briefing for the next session; verbatim prompt history |
| `claude/deliverables/` | Demo script and future roadmap (graded deliverables) |
| `claude/source/` | Untouched originals: the problem-statement PDF and mockups |
| `project/` | The actual application code |

`claude/` is the machine's brain. `project/` is the product. Never mix them.
