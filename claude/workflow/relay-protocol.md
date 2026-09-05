# The Relay Protocol

How three Claude sessions on three accounts build one project across 24 hours.

---

## 1. Why this exists

A single Claude account runs out of session capacity long before a 24-hour
hackathon finishes. The team's answer is a relay: three teammates, three Claude
Pro accounts, one session working at a time.

The hard constraint is that **each handoff is a cold start**. The next session
begins in a brand-new chat, possibly on a different account and a different
machine. It cannot read the previous session's transcript. There is no shared
context window, no conversation continuity, no memory.

**This repository is the only channel between sessions.** If a fact is not
committed to a file and pushed, the next session will never know it. This single
constraint explains every design choice below.

---

## 2. The rotation

```
MICHAEL  →  FRANKLIN  →  TREVOR  →  MICHAEL  →  ...
```

Each character corresponds to a teammate's Claude account, not to a person's
role in the code. Any character may work on any part of the system.

To find out who you are, read the last entry in `session-log.md`. If Franklin
closed the previous entry, you are Trevor. If the log is ambiguous or empty, ask
the user directly — identity is the one question always worth asking, because
getting it wrong corrupts the log for everyone after you.

---

## 3. Session lifecycle

### BOOT — first ten minutes

```bash
git pull --rebase
```

Then:

1. `CLAUDE.md` loads automatically — it points here.
2. Read `claude/START-HERE.md`.
3. Read `claude/state/current-state.md`. **Note the clock and the phase.**
4. Read `claude/state/task-board.md` and `claude/state/blockers.md`.
5. Skim `claude/context/decisions.md`.
6. Get the app running using `claude/state/runbook.md`. Do this *before* writing
   code — a broken environment discovered an hour in is an hour wasted.
7. Append an opening entry to `claude/workflow/session-log.md`.
8. Tell the user who you are and what you are picking up.

If `claude/handoff/NEXT-SESSION-PROMPT.md` exists and is current, read it in
place of steps 3–5. It is written specifically to replace them.

### WORK — the long middle

Continuously, as a matter of habit:

- Update `task-board.md` the moment a task changes status. Not at the end.
- Append decisions to `decisions.md` **with the reasoning**, not just the choice.
- Append the user's prompts verbatim to `handoff/prompt-history.md`.
- Record dead ends in `blockers.md` — what you tried, and why it failed.

**Heartbeat commit every 30–45 minutes:**

```bash
git add -A
git commit -m "chore(claude): heartbeat — <what changed>"
git push
```

This is the most important habit in the entire protocol. A session that dies
unexpectedly should cost the team forty minutes, not six hours.

### HANDOFF — on "MEGATRON LAUNCH"

The user types **MEGATRON LAUNCH** when the session reaches roughly 80–85% of
its usage limit. That remaining 15–20% is the packing budget.

Stop feature work immediately, even mid-task. Execute
`claude/workflow/megatron-checklist.md` end to end.

Do not argue for finishing the current task first. A half-finished task that is
*documented* is worth far more to the next session than a finished task that is
lost because the session ran out of capacity while writing the handoff.

---

## 4. What makes this robust

Five mechanisms, each guarding against a specific failure mode.

**① Stable context is separated from volatile state.**
`context/` changes rarely; `state/` changes constantly. Mixing them produces
documents where paragraph two is authoritative and paragraph seven is a lie from
six hours ago. Separated, a session knows immediately which files to distrust
when timestamps look stale.

**② Historical files are append-only.**
`session-log.md`, `decisions.md` and `prompt-history.md` are never edited, only
appended. No session can destroy another's record, and there is always an audit
trail. `decisions.md` in particular is the anti-relitigating device — without
it, each new session rediscovers from scratch why an earlier choice was made.

**③ One fact has exactly one home.**
Task status lives only in `task-board.md`. Everything else links to it. The
moment the same fact is written in two files, the two copies begin to diverge,
and the next session has no way to tell which one is lying.

**④ Heartbeat commits rather than a big-bang pack.**
If context were only written at MEGATRON LAUNCH, an unexpected session death
would take everything with it. Frequent small commits cap the worst case at
roughly forty minutes, and they turn the final pack into a tidy-up pass rather
than a scramble that can itself run out of capacity.

**⑤ The hackathon clock is a first-class field.**
`current-state.md` opens with elapsed time, remaining time, current phase and
explicit scope gates. Without it, a fresh session arriving at hour nineteen has
no idea it is hour nineteen, and will cheerfully start building something it
cannot possibly finish.

---

## 5. Git conventions

The relay is sequential, so no branching complexity is needed. Everyone works
`main`.

- `git pull --rebase` before the first edit of every session. No exceptions.
- **Never force-push. Never rewrite history.** Someone else's only copy of their
  work may be in the commits you would destroy.
- Commit message prefixes: `feat:` `fix:` `chore(claude):` `docs:` `test:`
- Identify yourself in commits touching product code:
  `feat(payroll): compute payslip lines [michael]`
- Tag each handoff so the next session can diff exactly what changed:
  `git tag handoff-michael-01 && git push --tags`

---

## 6. Repository layout

```
CLAUDE.md          auto-loaded failsafe — the next session cannot miss it
README.md          human-facing, also the judges' front door
claude/            the machine's brain (context, state, handoff)
project/           the actual application code
```

`claude/` and `project/` never mix. A session should be able to delete its
understanding of one without damaging the other.
