# BLOCKERS & DEAD ENDS

**Read this before debugging anything.** A previous session may have already
burned an hour on exactly what you are about to try.

Record not just what is broken, but **what was tried and why it failed**. That
negative information is the most valuable thing in this file.

---

## OPEN BLOCKERS

**No blocker is stopping work.** The three items still marked open below are
accepted risks or environment facts, not obstacles:

| | |
|---|---|
| **B-009** | Large fan-out subagent workflows can exhaust the account session limit. Check capacity first |
| **B-011** | The formula sandbox blocks tokens, not capabilities. Accepted — rule authoring is Payroll-Manager-only |
| **B-014** | The main checkout is parked on a stale branch. **Read this before your first command** |

The one open *question* — whether a deployed demo is required — is in
`current-state.md`, not here, because it needs the user rather than a fix.

### B-001 — Hackathon start time — **RESOLVED**
**Status:** resolved · session 02 (Franklin), confirmed by user

Start **10:00 IST 2026-09-05**, end **10:00 IST 2026-09-06**. Session 01 had
inferred 09:00 from file timestamps; that was an hour early. The clock block in
`current-state.md` is correct and every scope gate now derives from a confirmed
time. Nothing further to do.

---

## OPEN — session 03

### B-014 — The main checkout is parked on `test/backend-suite`, behind `main`
**Severity:** high if unnoticed · **Opened:** session 03 (Trevor)

`C:\Users\raval\Desktop\odoo_2026` — the main working copy on the build machine —
is checked out on branch `test/backend-suite` at `b8b65ca`. That branch is fully
merged into `main`, but it is **seven commits behind it** and does not contain
any of session 03's bug fixes.

Session 03's second half ran in a git worktree at
`.claude/worktrees/frontend-routing-setup-e9a159`, which is why the main checkout
was never switched back.

**Before doing anything in the main checkout:**

```bash
cd C:/Users/raval/Desktop/odoo_2026
git checkout main && git pull
git log --oneline -1     # expect the session-03 handoff commit
```

If you skip this you will read stale source, "rediscover" bugs that are already
fixed, and possibly commit on top of a merged branch. Do not delete
`test/backend-suite` — it is merged history and the tag chain refers to it.

**Note also:** `project/backend/.venv` and `db.sqlite3` live in the main checkout
only, and are gitignored. A fresh worktree has neither. Session 03 ran the
worktree's code against the main checkout's interpreter by absolute path, which
works because a venv's `site-packages` are absolute:

```bash
cd <worktree>/project/backend
PY="C:/Users/raval/Desktop/odoo_2026/project/backend/.venv/Scripts/python.exe"
"$PY" manage.py migrate && "$PY" manage.py seed --flush
```

---

## RESOLVED / DEAD ENDS

### B-002 — `gh` CLI is not installed
**Status:** worked around · session 01 (Michael)

`gh --version` → `command not found`. Installing it was rejected as not worth the
time.

**Workaround in use:** plain `git` over HTTPS. On Windows, Git Credential Manager
opens a browser window on the first push, the user signs in once, and credentials
are cached for every push afterwards. No CLI install needed.

Do not spend time trying to install `gh`.

### B-003 — PDF tooling on this machine
**Status:** resolved · session 01 (Michael)

`pdftoppm` is not available, so the Read tool cannot render PDF pages. `pypdf`
and `PyPDF2` are not installed in the system Python either.

**What works:** `pdftotext` **is** available at `/mingw64/bin/pdftotext`.

```bash
pdftotext -layout "claude/source/PeoplePay360 HR & Payroll.pdf" out.txt
```

That recovered the entire problem statement cleanly. Use it rather than trying to
install a Python PDF library.

### B-004 — Reading the Excalidraw mockup
**Status:** resolved · session 01 (Michael)

The PNG export is 6073×8818 and unreadable when scaled to fit. The `.excalidraw`
file is JSON and contains all 3,459 text elements with coordinates, which is a far
better source.

**Working approach** — sort by position to reconstruct reading order, and write
to a file rather than stdout, because the Windows console is cp1252 and will
crash on the arrows and bullets in the text:

```python
import json, io
d = json.load(open('claude/source/HRMS OXP - 24 hours.excalidraw', encoding='utf-8'))
els = d.get('elements', d)
txt = [e for e in els if e.get('type') == 'text' and e.get('text')]
txt.sort(key=lambda e: (round(e.get('y', 0) / 40), e.get('x', 0)))
out = io.open('excal.txt', 'w', encoding='utf-8')
for e in txt:
    out.write('---[y=%d x=%d fs=%s]\n%s\n' % (
        e.get('y', 0), e.get('x', 0), round(e.get('fontSize', 0)), e['text']))
out.close()
```

Filter to `len(text) > 90 or fontSize >= 16` to get just the headings and the
participant notes, which is where the actual requirements are. Everything already
recovered this way is written up in `claude/context/product-spec.md` — check
there first before re-parsing.

**Note:** running `python` directly and printing to stdout raises
`UnicodeEncodeError` on characters like `▼` and `●`. Either write to a file with
an explicit `encoding='utf-8'`, or launch with `python -X utf8` and call
`sys.stdout.reconfigure(encoding='utf-8')`.


---

## RESOLVED — session 01

### B-005 — PostgreSQL and Docker are both absent
**Status:** worked around · see D-011

`psql`, `pg_isready` and `docker` are all missing, and there is no PostgreSQL
install directory. Rather than install anything, the project runs on SQLite with
`DATABASE_URL` available to switch engines.

Do not spend time installing PostgreSQL unless the user asks for it.

### B-006 — The cp1252 console kills any non-ASCII print
**Status:** recurring trap · hit twice in session 01

Windows console encoding is cp1252. Printing the rupee sign, an en dash or a
bullet from a Python script raises `UnicodeEncodeError` and aborts the command —
once mid-way through the seed, after the data had already been written.

**Rule: never print non-ASCII from a management command or script.** Write
`INR` rather than the rupee sign in console output. The symbol is fine in files,
API responses and PDFs — only the terminal breaks.

For scripts that must print Unicode: `python -X utf8` plus
`sys.stdout.reconfigure(encoding="utf-8")`, or write to a file opened with
`encoding="utf-8"`.

### B-007 — Chained heredocs in one Bash call fail to parse
**Status:** avoid · session 01

Writing several files in a single Bash command with chained `<<'EOF'` heredocs
failed with `unexpected EOF while looking for matching quote`. Backticks and
apostrophes inside the bodies interact badly with the shell.

Use the Write tool for file creation. For scripted edits, write a `.py` file and
run it rather than passing a long `python -c` string — inline quoting also ate a
set of backticks while reconciling the task board.

### B-008 — Django test client needs `testserver` in ALLOWED_HOSTS
**Status:** fixed · session 01

`smoke_api.py` drives the real HTTP stack, and Django's test client sends
`Host: testserver`. `settings.py` now appends it when `DEBUG` is on.

### B-009 — Subagent workflows are capped by the account session limit
**Status:** open · session 02

A multi-agent bug hunt (8 reviewers × 3 adversarial verifiers) was launched via
the Workflow tool. All eight finder agents died immediately with
`You've hit your session limit`, having consumed ~761k subagent tokens and
returned nothing. A re-run after the limit reset was making progress when the
user stopped it to prioritise packing.

**What this means:** large fan-out workflows are not free on this account, and a
failed fan-out still burns the budget. Before launching one, check remaining
capacity. The script survives at
`.claude/projects/.../workflows/scripts/peoplepay-bug-hunt-*.js` and can be
resumed with `resumeFromRunId` — completed agents replay from cache.

**Not a blocker for the product.** The manual review it was meant to replace
found the four real bugs listed below anyway.

### B-010 — `smoke_api.py` writes to the development database
**Status:** known, documented · session 02

It creates an `April 2026 (smoke)` payrun and 5 payslips in `db.sqlite3`, not in
a throwaway test database. The dashboard then defaults to that payrun, because it
is the most recent, and opens on junk instead of February.

**Always run `manage.py seed --flush` after `smoke_api.py`.** This is in the
README and in the runbook. Trevor's Django tests do not have this problem — they
use `TestCase`, so they run against a throwaway database and never touch
`db.sqlite3`.

### B-011 — The formula sandbox blocks tokens, not capabilities
**Status:** open, accepted · session 02

`payroll/engine.py` `safe_eval` rejects a denylist of substrings (`__`, `import`,
`getattr`, `open(`, …) before evaluating. It genuinely blocks the obvious
escapes, and there is a test for each.

But the evaluation context contains live Django model instances (`employee`,
`contract`, `payslip`), and attribute access is not restricted. A chain that
avoids every denied substring — reaching `_meta`, then the app registry — is not
prevented.

**Accepted, not fixed.** Writing formulas requires `can_configure_payroll`, i.e.
Payroll Manager or Admin, so this is a privileged configuration feature by
design rather than a user-input surface. Recording it so nobody claims the
sandbox is airtight, and so a future session that opens rule authoring to a
lower role knows to fix it first.

---

## RESOLVED / TRAPS — session 03

### B-012 — `probe_forms.py` needs a live server; the failure looks like a crash
**Status:** documented · session 03 (Trevor)

`smoke_api.py` uses Django's test client and needs no server. `probe_forms.py`
drives real HTTP with `urllib` against `http://127.0.0.1:8000` and **requires
`manage.py runserver` in another terminal**. Without one it does not print a
friendly message — it dies with a raw traceback ending in:

```
urllib.error.URLError: <urlopen error [WinError 10061] No connection could be
made because the target machine actively refused it>
```

That reads like a broken harness. It is a missing server. Start one and re-run.

### B-013 — The probe's `first()` silently swallows query strings
**Status:** fixed · session 03 (Trevor)

`first(path)` appends its own `?page_size=1`. Passing a path that already carries
a query — `first("/api/timeoff-types/?requires_allocation=false")` — produces
`...?requires_allocation=false?page_size=1`. The filter value becomes garbage,
django-filter drops it, and you get the *unfiltered* first row while believing
the filter applied. This cost a debugging cycle: the probe picked an
allocation-gated leave type and failed on the allocation gate rather than on the
payload shape it was meant to test.

**Fixed** by adding an `every()` helper that fetches `?page_size=200` and lets
the caller pick a row in Python. Filter in Python, not in a query string appended
to a helper that appends its own.

### B-015 — A form field whose type disagrees with the model field
**Status:** fixed, but the *class* of bug is worth remembering · session 03

`TimeOff.jsx` seeded `half_day: false` — a boolean — for
`half_day = models.CharField(choices=[FIRST, SECOND], blank=True)`. DRF's
`ChoiceField` reported `"False" is not a valid choice` and rejected **every**
submission with a 400, for every role, from the day the screen was written. No
control for the field was rendered at all, so there was no way to correct it from
the UI.

Two things let it survive to hour 3 of a 24-hour build:

1. **It was the one create form `probe_forms.py` did not cover** (now D-020).
2. It was never clicked. Every prior report describing this screen as working was
   written from source, not from a browser.

**The lesson, stated generally:** a field present in the payload but absent from
the rendered form can never be corrected by a human, so its default value is
load-bearing — and nothing type-checks it against the model. When adding a field
to a form's blank state, render a control for it or leave it out of the payload.

**The other lesson:** open the screen. Three sessions read this file; one clicked
it, and that is when it fell over.


---

## TRAPS — session 04

### B-016 — Never run `manage.py runserver --noreload`
**Status:** trap · session 04

Session 04 started the backend with `--noreload` to keep a background task
quiet. Python edits then had no effect on the running server, and a correct
employer-cost fix looked broken for several minutes: the UI showed employer
provident fund inside the employee's deductions because the *server* was still
executing pre-fix code, while a shell running the same code returned the right
answer.

Use plain `manage.py runserver`. If a served response disagrees with what the
same code produces in a shell, suspect a stale server before suspecting the code.

### B-017 — A PDF harness that only counts bytes proves nothing
**Status:** lesson · session 04

`smoke_api.py` asserted the payslip endpoint returns `application/pdf` and more
than 1,500 bytes. It stayed green for the entire build while every money figure
on the document rendered a substitute character, because ReportLab's Helvetica
has no rupee glyph. The user found it by downloading a payslip.

When a binary deliverable matters, read it:

```bash
pdftotext -layout -enc UTF-8 slip.pdf slip.txt
```

```python
import re
raw = open("slip.pdf", "rb").read()
print(sorted(set(re.findall(rb"/BaseFont\s*/([A-Za-z0-9+\-]+)", raw))))
```

If `Helvetica` still appears in a document meant to be fully embedded, some cell
is falling back to it — a `TableStyle` that sets `FONTNAME` only on its header
row leaves every body cell on the default face.

### B-018 — `pdftotext` misreads subset-embedded fonts
**Status:** know this · session 04

Even after the font fix, `pdftotext` rendered some rupee signs as `s`. That is an
extraction artifact of a subsetted TrueType face, not a rendering fault. The
decisive checks are the embedded ToUnicode CMap containing `<01> <20B9>`, and
counting how many money figures carry the glyph — 22 of 26 in the fixed file,
the remaining four being non-currency values (worked days, LOP days, OT hours).

### B-019 — The Browser pane will not display a PDF
**Status:** know this · session 04

Navigating the Browser pane to a `.pdf` URL triggers a download dialog instead of
rendering, so a payslip cannot be eyeballed that way. Inspect the file's
internals or extract its text instead.

### B-020 — Inline `python -c` and heredocs keep corrupting file content
**Status:** recurring · sessions 01 and 04

Extends B-007. In session 04 a heredoc turned `\Fonts\arial.ttf` into
`Fonts<BEL>rial.ttf` — a literal 0x07 byte, invisible in the file view, which the
Edit tool then could not match because the string on disk was not what it looked
like.

Write a `.py` file into the scratchpad and run it. Reserve inline `python -c` for
one-liners containing no backslashes, backticks or quotes.

---

## TRAPS — session 05 (Franklin)

### B-021 — Two `runserver` processes on port 8000, one serving stale code
**Severity:** high · wasted ~15 minutes

A `runserver` left over from an earlier session was still listening on 8000. A
second one started this session bound to the same port, and **the stale process
answered first**. `/api/auth/login/` returned the old payload with no
`capabilities` or `navigation` field, which looked exactly like the serializer
edit never having applied.

Same family as B-016 (`--noreload`), and the tell is identical: the code on disk
is right and the server disagrees.

```bash
netstat -ano | grep ":8000.*LISTENING"     # expect exactly ONE pid
taskkill //PID <stale> //F
```

Check this **before** debugging any "my change did not take effect" symptom.

### B-022 — Browser-pane element refs go stale after `resize_window`
**Severity:** medium · wasted ~10 minutes

After `resize_window`, `ref_N` handles captured from an earlier `read_page`
still resolve, but to the **wrong screen position** — clicks landed on the
neighbouring button. Symptom: clicking "HR Manager" filled in the Payroll User's
email, and clicking "Sign in" did nothing at all.

Two workarounds, both used successfully:

1. Re-run `read_page` *after* every resize and use only the new refs.
2. For a React form, skip the mouse entirely. `form_input` writes the DOM value
   but **React's controlled state does not see it**, so drive the app through
   `javascript_tool` instead:

```js
const r = await fetch('http://127.0.0.1:8000/api/auth/login/', {
  method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'sara@oxp.com', password: 'demo1234'})});
const d = await r.json();
localStorage.setItem('pp360_token', d.token);
localStorage.setItem('pp360_user', JSON.stringify(d.user));
location.hash = '#/dashboard'; setTimeout(() => location.reload(), 50);
```

That is how every role was verified this session.

### B-023 — Bash heredocs still corrupt multi-line appends — confirmed twice more
**Severity:** medium

B-020 warned about this and it bit twice in this session. A `cat >> file
<< 'EOF'` block containing triple-quoted Python, backticks or an apostrophe
failed with `unexpected EOF while looking for matching`, and **appended nothing
while reporting nothing useful**. The file was silently unchanged; only a
follow-up `grep` or `tail` caught it.

**Use the Write or Edit tool for any multi-line source or document change.**
Reserve Bash heredocs for short, quote-free text. Where a new block is large,
give it its own module — that is why `dashboard/role_views.py`,
`accounts/security.py`, `accounts/selfservice.py` and
`accounts/selfservice_api.py` exist as separate files rather than as appends.

For appending to an append-only document: write the new section to a file in the
scratchpad with the Write tool, then `cat scratchpad/thing.md >> target.md`.

### B-024 — `bulk_create` skips `save()`, so generated references come out blank
**Severity:** medium · anticipated, not hit

`Employee.save` and `Contract.save` mint `EMP/YYYY/NNNN` and `CON/YYYY/NNNN`
themselves. `bulk_create` does not call `save()`, so any row written that way
must carry its own reference. `seed.py`'s `_sequencer()` mints them, starting
**above** whatever is already in the table so the fixed demo roster's codes —
which the demo script quotes by name — are never reused or shifted.

`core/tests.py::test_generated_rows_carry_their_own_references` guards it.

### B-025 — The employee dashboard windowed on the current calendar month
**Severity:** medium · **fixed** this session

Seeded attendance ends March 2026; the machine clock reads September 2026. Every
employee therefore opened on a screen of zeroes, which reads as "the system is
broken" rather than "you have not clocked in yet". It now falls back to the
month of the employee's most recent record and labels which month is on screen.

**The same trap applies anywhere else a date window is anchored to `today`.**
`dashboard/api.py::_filters` already falls back to the newest payrun's period,
which is why the payroll and HR dashboards were unaffected — but any new panel
that windows on "this month" will be empty on the demo machine.

### B-026 — Vite served a transform from *between* two writes to one file
**Severity:** medium · **hit and diagnosed** this session (06)

A screen died with `canApprove is not defined` while the file on disk plainly
declared `canApprove` twenty lines above the use. It survived a hard browser
reload, which is what makes it worth writing down: **the stale copy was on the
server side of the module graph, not in the browser cache.**

The cause: two `write_text` calls to the same `.jsx` inside the same second.
Vite's transform cache keys on mtime, the second write did not advance it past
the first at the resolution being compared, and the module it kept was the
intermediate one — JSX already referencing the new binding, with the
declaration not yet added.

**Diagnosis in one command.** Ask the dev server what it is actually serving,
rather than reading the file yourself:

```bash
curl -s http://localhost:5173/src/screens/TimeOff.jsx | grep -n canApprove
```

If that disagrees with the file on disk, this is the bug. `touch <file>` fixes
it; there is no need to restart Vite.

**Avoid it** by making one write per file per edit — build the whole new
content, then write once. And note the family resemblance to B-021: in both
cases the thing answering you is not the thing you edited, and the symptom is
indistinguishable from "my change did not apply". The general move is to ask the
server what it is serving before doubting your own edit.

### B-027 — A stale dev server from *another worktree* held the frontend port
**Severity:** medium · hit at the start of session 06

B-021 says to check port 8000 before debugging a change that did not take
effect. Session 06 booted to a clean 8000 and a **busy 5173** — held by a Vite
belonging to `.claude/worktrees/frontend-routing-setup-e9a159`, a different
checkout of this repository. Had it gone unnoticed, `http://localhost:5173`
would have served an older frontend against the correct backend: the worst
possible version of this failure, because the app works, just not the way the
code says it should.

```bash
netstat -ano | grep -E ":(8000|5173).*LISTENING"
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<pid>' | Select CommandLine"
```

The second command is the one that matters — the pid alone does not tell you
*which checkout* it is serving, and on a machine with several worktrees that is
the only question worth asking.

### B-028 — One account cannot hold two live sessions, and the demo needs to know
**Severity:** medium · **not a bug — deliberate, and it bit twice anyway**

`accounts/api.py` deletes the account's existing token on **every** sign-in and
issues a fresh one, so `token.created` is the start of *this* session and the
expiry in `ExpiringTokenAuthentication` means what it says. That is correct and
worth keeping.

The consequence is not obvious: **signing in as an account that is already
signed in silently kills the first session.** The older tab 401s on its next
call and lands on the login screen. It happened twice this session while driving
the app, and both times looked like a product bug — the second time in the
middle of an approval flow.

**On stage this would be fatal.** If the presenter has the app open on a laptop
and someone opens the same account on the projector machine, the laptop drops
out mid-demo.

* Use **one tab per account**. Different accounts in different tabs is fine.
* When scripting the browser, sign in **once** per account and reuse the token,
  rather than re-issuing a login before each step.

### B-029 — `main` is held by an abandoned worktree, and its local ref is stale
**Severity:** high · hit during the session 06 handoff

`git checkout main` fails in this worktree:

```
fatal: 'main' is already used by worktree at
'.claude/worktrees/frontend-routing-setup-e9a159'
```

Worse, that worktree's `main` is at **`ba294be`**, far behind the real branch.
The local `main` ref is therefore **not** main, and anything reasoning from it
will merge into the wrong place.

**Work against `origin/main` and push to it explicitly:**

```bash
git fetch origin
git checkout -b integrate/<something> origin/main
git merge --no-ff <your-branch> -m "merge: ..."
git push origin HEAD:main
```

That is how session 06's work reached `main` at `1437c25`. Do not delete the
other worktree — it is not yours, and the stale ref is harmless as long as you
never read it.

### B-030 — Two sessions numbered 06 ran at the same time
**Severity:** high · **live at the moment this was written**

`origin/main` gained two commits mid-session from another session calling itself
**session 06, as Michael** (`a7c4d3d`, `a1ae6a7`). This session is also 06, as
Trevor. The relay's assumption — one session at a time, the repository as the
only channel — no longer holds.

They touched `claude/state/runbook.md` and `claude/workflow/session-log.md`;
this session touched neither, so the merge was clean. **That was luck.**

Before writing any `claude/` file:

```bash
git fetch origin && git log --oneline -5 origin/main
```

Expect `session-log.md`, `PROGRESS.md`, `current-state.md` and `task-board.md`
to have been edited by somebody who is not you. **Merge, never overwrite** — and
prefer appending a clearly-headed section over rewriting a shared one. Push small
and often; a large unpushed batch is what turns this into a real conflict.
