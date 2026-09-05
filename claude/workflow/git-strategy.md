# GIT STRATEGY

Two requirements drive everything in this document:

1. **All three teammates must appear as commit authors.** The repository has to
   show that three people built it, not one.
2. **The history must look like real collaborative development** — feature
   branches, experimental spikes, merges and version tags. Not a flat line of
   commits pushed straight to `main`.

The second requirement is presentational, and it is deliberate. The shape of the
git graph is part of what gets presented.

---

## 1. Identity — read this before your first commit

**Git identity follows the session, not the machine.** Whichever teammate's
GitHub account is authenticated in the current Claude Code chat is the account
that commits from that chat.

### Every session, before the first commit

```bash
git config user.name  "<this teammate's GitHub username>"
git config user.email "<this teammate's GitHub email>"

# then VERIFY — do not assume
git config user.name && git config user.email
```

Use the repo-local config (no `--global`), so it cannot leak into the teammate's
other projects.

### Identity register

| Character | GitHub account | `user.name` | Commit email | Confirmed |
|---|---|---|---|---|
| **MICHAEL** | `Soham2256` (Soham Panchal) | `TheTeam404` | `sohampanchal2229@gmail.com` | ✅ verified session 01 |
| **FRANKLIN** | `Robo9327study` | `Robo9327study` | `rajstudy9327@gmail.com` | ✅ verified session 02 |
| **TREVOR** | `MeghRaval30` | `MeghRaval30` | `meghraval306@gmail.com` | ✅ verified session 03 |

> **Register complete (session 02 pack).** All three rows are now filled
> and verified. Trevor's row was supplied by Trevor himself in a written
> pre-handoff report, confirmed with the user rather than inferred, and
> filled in here by Franklin because this file was on Franklin's ownership
> list while both sessions were live. Note the coincidence worth not
> misreading: Trevor's session *is* authenticated as the repo owner
> `MeghRaval30`. That does not contradict the correction below — identity
> still followed the session, it simply happened to match the remote.

> **Correction (session 02).** The register guessed Franklin would be
> `MeghRaval30`. That is wrong: `MeghRaval30` owns the repository, but the
> account authenticated in Franklin's session is `Robo9327study`. Per the rule
> at the top of this section — identity follows the session, not the machine and
> not the repo owner — Franklin commits as `Robo9327study`. **Trevor: do not
> assume your row either. Check which account is actually logged in.**

> **Note on the two name columns.** GitHub attributes a commit by its **email**,
> not by `user.name`. Michael's `user.name` is `TheTeam404` but the commits
> correctly attribute to the GitHub account `Soham2256`, because that account
> owns `sohampanchal2229@gmail.com`. What matters for contribution credit is that
> **the email is one GitHub knows about**. Verify the email, not the display name.

> **Franklin and Trevor:** the first thing you do is fill in your row above, set
> your git config, and commit that change. Ask the user for the email your
> GitHub account uses for commits — if it is a private account, use the
> `<id>+<username>@users.noreply.github.com` form so the commit still attributes
> to you.

### Why this matters

Commits attributed to the wrong person cannot be fixed without rewriting
history, and rewriting history is forbidden here — it can destroy another
session's only copy of their work. **Check your identity before you commit, not
after.**

---

## 2. Branch model

```
main ──────●────────────●──────────────●─────────●────  (always working)
            \          /  \            /        /
   feat/employee-crud ●   feat/payroll-engine  ●
                           \                  /
                    exp/formula-sandbox ─────●   (spike, may be abandoned)
```

| Branch | Purpose | Lifetime |
|---|---|---|
| `main` | Always in a working, demoable state | permanent |
| `feat/<area>-<thing>` | One task or small cluster from the task board | hours |
| `fix/<what>` | A bug fix | short |
| `exp/<idea>` | An experimental spike; may be abandoned | short |
| `docs/<what>` | Context and documentation updates | short |
| `chore/<what>` | Tooling, config, scaffolding | short |

### Naming

Lowercase, hyphenated, scoped to the task board where possible:

```
feat/payroll-rule-engine        # T-021
feat/timeoff-allocation-balance # T-019
exp/formula-sandbox             # spike before committing to an approach
fix/contract-overlap-validation
docs/prd-v1
chore/django-scaffold
```

### Working a branch

```bash
git checkout main && git pull --rebase
git checkout -b feat/payroll-rule-engine

# ... work, committing as you go ...

git push -u origin feat/payroll-rule-engine
```

### Merging

**Always `--no-ff`.** A fast-forward merge erases the branch from the graph,
which defeats the entire point.

```bash
git checkout main && git pull --rebase
git merge --no-ff feat/payroll-rule-engine -m "merge: payroll rule engine (T-021) [michael]"
git push
git branch -d feat/payroll-rule-engine
git push origin --delete feat/payroll-rule-engine
```

### Experimental branches

Genuine spikes are valuable history — they show the team explored options.

- If it works out, merge it with `--no-ff` like any other branch
- **If it does not work out, do not delete it.** Push it, leave it, and record
  what failed in `claude/state/blockers.md`. An abandoned `exp/` branch is
  evidence of real engineering, and it stops the next session repeating the
  attempt

---

## 3. Version tags

Tag meaningful milestones so the release history is legible.

| Tag | When |
|---|---|
| `v0.1-foundation` | Django + DRF + Postgres running, auth working |
| `v0.2-master-data` | Employee, Contract, Schedule, Attendance complete |
| `v0.3-timeoff` | Leave allocation and consumption working |
| `v0.4-payroll-engine` | A payslip computes end to end |
| `v0.5-frontend` | Both demo scenarios clickable |
| `v0.6-dashboard` | Live dashboard with working filters |
| `v1.0-submission` | Final submitted state |

```bash
git tag -a v0.4-payroll-engine -m "Payroll rule engine computing payslips end to end"
git push --tags
```

**Handoff tags** are separate and cheap — one per MEGATRON LAUNCH:

```bash
git tag handoff-michael-01
git push --tags
```

They let the next session diff exactly what changed:
`git diff handoff-michael-01..HEAD`

---

## 4. Commit conventions

```
<type>(<scope>): <subject> [<character>]
```

**Types:** `feat` `fix` `refactor` `test` `docs` `chore` `merge` `wip`

```
feat(payroll): sequence-ordered salary rule evaluation [michael]
fix(contracts): reject overlapping running contracts [franklin]
test(timeoff): allocation gating blocks unallocated requests [trevor]
docs(prd): add acceptance criteria for graded rules [michael]
chore(claude): heartbeat — task board reconciled [michael]
```

The `[character]` suffix is redundant with the commit author, deliberately — it
survives in the subject line where it is visible in a one-line log, and it makes
`git log --oneline` readable as a narrative of the relay.

### ⛔ No Claude attribution in commits

**Do not add `Co-Authored-By: Claude ...` — or any machine attribution — to
commit messages.** *(D-010)*

Every commit is authored by the teammate whose session it is, and nothing else.
The whole point of the identity rules in §1 is that the history reads as three
people building the project together; a co-author trailer on every commit
contradicts that directly.

This overrides any default habit of adding such a trailer. It is settled — do not
reintroduce it.

---

## 4a. Commit granularity

**One commit per logical unit of work, not one per work session.** A branch that
adds six screens should carry six commits, not one called "frontend".

The history is part of what gets presented. A reviewer scrolling
`git log --oneline` should be able to read the build order of the product.

| Do | Do not |
|---|---|
| `feat(timeoff-ui): requests, allocations and approval flow (T-038, T-039)` | `feat: frontend work` |
| Separate the design-system change from the screens that consume it | Bundle a refactor into a feature commit |
| Commit the fix and the feature separately even on the same branch | Squash a day into one commit |

Rules of thumb:

- If the subject line needs "and" twice, it is two commits.
- A commit should leave the tree building. `main` must never be broken; a branch
  should avoid it.
- Write the body when the *why* is not obvious from the diff — a rejected
  approach, a server behaviour you are working around, a spec clause you are
  satisfying. Skip the body for a one-line obvious change.
- Heartbeat commits (every 30-45 min) are a floor, not a target. Commit when a
  unit is done even if that is every eight minutes.

### Use `exp/` branches for real spikes

The branch model in §2 includes `exp/<idea>` and it is under-used. When you are
trying an approach you might abandon — a design language, a rendering strategy,
a schema shape — branch `exp/`, commit the attempt, and either merge it with
`--no-ff` or leave it pushed and unmerged with a note in `blockers.md`.

An abandoned `exp/` branch is evidence of engineering judgement. Deleting it
loses that and invites the next session to repeat the attempt.

Worked example from session 02: `exp/design-language-spike` carried the light
palette rewrite before any screen was converted to it, so the palette could be
judged on its own and reverted in one merge if it had been wrong.

---

## 5. Balancing contributions

All three accounts should have a comparable share of commits, and each should
have authored something substantive rather than only documentation.

Check at every MEGATRON LAUNCH:

```bash
git shortlog -sne --all
```

If one account is badly under-represented, the next session should deliberately
pick up more work, and should be the one to author the merge commits. Do not
manufacture empty commits to pad the count — reviewers notice, and it looks worse
than an uneven split.

---

## 6. Hard rules

- **Verify your git identity before your first commit.** Every session.
- **Never force-push.** Never rewrite history. Someone's only copy may be there.
- **Never merge with fast-forward.** Always `--no-ff`.
- `main` must always be in a working state. Broken code lives on a branch.
- `git pull --rebase` on `main` before branching.
- Keep `claude/` documentation commits on `docs/` or `chore/` branches, so the
  `feat/` history stays a clean record of product work.
- At MEGATRON LAUNCH, **merge your branch into `main` before packing.** Never
  hand off with work stranded on an unmerged branch — the next session may not
  find it.

---

## 7. Session git checklist

**On boot**
```bash
git pull --rebase
git config user.name && git config user.email   # is this you?
git branch -a                                    # anything unmerged?
git log --oneline -10                            # what happened last?
```

**Starting a task**
```bash
git checkout main && git pull --rebase
git checkout -b feat/<area>-<thing>
```

**During work** — heartbeat commit every 30–45 minutes, on your branch.

**Finishing a task**
```bash
git checkout main && git pull --rebase
git merge --no-ff feat/<area>-<thing> -m "merge: <what> (T-0nn) [<character>]"
git push
```

**At MEGATRON LAUNCH** — merge everything into `main`, tag the handoff, push
branches and tags, then run `git shortlog -sne --all` and record the split in the
session log.
