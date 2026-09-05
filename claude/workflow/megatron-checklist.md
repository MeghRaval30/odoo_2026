# MEGATRON LAUNCH — Packing Checklist

**Trigger:** the user types `MEGATRON LAUNCH`.
**Meaning:** this session is at ~80–85% of its usage limit. The remaining
capacity is the packing budget.
**First action:** stop all feature work. Immediately. Even mid-task.

A half-finished task that is *documented* is worth more to the next session than
a finished task that is lost because capacity ran out while writing the handoff.
Do not ask to finish what you were doing. Pack first.

---

## Step 0 — Announce and orient

Tell the user: "MEGATRON LAUNCH acknowledged. Stopping work, packing now."

Note the wall-clock time. You need it for the clock block in Step 2.

---

## Step 1 — Save the code first, and merge your branch

Code before context. Losing working code is worse than losing notes.

```bash
git add -A
git commit -m "wip: <one line on where the code actually stands> [<yourname>]"
git push -u origin <your-branch>
```

**Then merge into `main`.** Never hand off with work stranded on an unmerged
branch — the next session may never find it.

```bash
git checkout main && git pull --rebase
git merge --no-ff <your-branch> -m "merge: <what> [<yourname>]"
git push
```

If a branch is a genuine dead end, **do not delete it** — push it, leave it, and
record what failed in `blockers.md`.

If the working tree is genuinely clean, say so and move on. If something is
broken and uncommitted, **still commit it** as `wip:` and describe the breakage
in the message. Never leave uncommitted work behind; the next session will never
see it.

---

## Step 2 — Refresh `claude/state/current-state.md`

Rewrite this file completely. It is the first thing the next session reads.

- [ ] **The clock block**: hackathon start, now, elapsed, remaining, phase
- [ ] Update the phase against the scope gates (BUILD / FREEZE / POLISH / DEMO)
- [ ] **What works** — only things you have actually verified running, with the
      command or click-path that proves it
- [ ] **What is broken** — precise symptom, not a vague gesture
- [ ] **What is half-done** — file path and line, what is missing, what the
      intended approach was
- [ ] **The single next action** — literal and concrete, so the next session can
      start without deciding anything

Be honest here. An optimistic status report is worse than useless: the next
session will build on top of something that does not work and lose hours.

---

## Step 3 — Reconcile `claude/state/task-board.md`

Reconcile against **reality**, not against intentions.

- [ ] Every task's status reflects what is actually true in the code right now
- [ ] Anything you started but did not finish is `IN PROGRESS`, never `DONE`
- [ ] New tasks discovered during the session have been added
- [ ] Tasks that are no longer relevant are struck out with a one-line reason
- [ ] Priorities re-ordered for the time actually remaining

---

## Step 4 — Flush the append-only logs

- [ ] `claude/handoff/prompt-history.md` — every user prompt from this session,
      verbatim, in order, under a clear session heading
- [ ] `claude/context/decisions.md` — every real choice made this session, each
      with its **rationale**, so nobody relitigates it
- [ ] `claude/state/blockers.md` — open problems, and crucially **what was
      already tried and failed**, so the next session does not repeat it

---

## Step 5 — Close the session log entry

Append to `claude/workflow/session-log.md`:

- [ ] Session close time and total duration
- [ ] What was accomplished, in plain terms
- [ ] What was attempted and abandoned, and why
- [ ] Handoff SHA and tag
- [ ] Who picks up next

---

## Step 6 — Regenerate `claude/handoff/NEXT-SESSION-PROMPT.md`

**Rewrite from scratch. Never append to it.** An appended briefing accumulates
contradictions; a rewritten one is always internally consistent.

Target roughly 4,000–5,000 words, structured under these fourteen headings:

| § | Content |
|---|---|
| 1 | Identity and orientation — who you are, who came before, relay rules |
| 2 | The clock — elapsed, remaining, phase, scope gates |
| 3 | The product in ~500 words — what PeoplePay360 is, why it is not CRUD |
| 4 | The five graded business rules, with acceptance criteria |
| 5 | Architecture as actually built — stack, layout, key modules, conventions |
| 6 | Data model walkthrough — entities and the relationships that matter |
| 7 | What is DONE — verified, with how to prove each item |
| 8 | What is HALF-DONE — file and line, what is missing, intended approach |
| 9 | What is NOT STARTED — in priority order |
| 10 | Decisions already made, with rationale, marked *do not relitigate* |
| 11 | Known bugs and blockers — **including what was already tried** |
| 12 | Your first three actions — literal, concrete, ordered |
| 13 | Traps — gotchas that cost this session time |
| 14 | Demo script status — which scenarios currently run end to end |

Sections 8, 11 and 13 carry the real value. Anyone can list what is done.
Recording what was *tried and failed* is what stops the next session burning an
hour on a dead end you already exhausted.

---

## Step 7 — Verify the runbook still works

- [ ] Open `claude/state/runbook.md`
- [ ] Confirm every command in it is still accurate after this session's changes
- [ ] If dependencies, env vars, ports or seed commands changed, update it

A stale runbook costs the next session its first hour. This check is cheap;
skipping it is not.

---

## Step 8 — Commit, tag, push, verify

```bash
git add -A
git commit -m "chore(claude): MEGATRON LAUNCH — handoff from <yourname> [<n>]"
git tag handoff-<yourname>-<nn>
git push && git push --tags
```

- [ ] Confirm the push actually landed — do not assume it did

```bash
git log --oneline -3
git status
```

---

## Step 9 — Report to the user

Give a short, factual closing report:

- Which character just packed
- The handoff commit SHA and tag
- One line on where the project stands
- Who is up next, and the literal first thing they will do

Example:

> Michael packed. Handoff commit `a1b2c3d`, tagged `handoff-michael-01`, pushed.
> Backend models and the payroll rule engine are done and tested; the payslip PDF
> is half-built. Franklin is up — his first action is finishing
> `project/backend/payroll/pdf.py`, which is stubbed at line 40.

---

## The one-line summary

**Code first, state second, logs third, briefing fourth, push and verify last.**
