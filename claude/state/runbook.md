# RUNBOOK

Get from a fresh clone to a running, seeded app. **Verify every command here at
each MEGATRON LAUNCH** — a stale runbook costs the next session its first hour.

Last verified: **session 09 (Trevor), 2026-09-06 06:00 IST.** Every command below
was re-run in that session, including the frontend build and all five harnesses,
plus the new local-model setup.

> **Do not add `--noreload` to `runserver`** (B-016). Session 04 did, then spent
> minutes chasing a phantom bug that was the server holding pre-fix code while a
> shell running the same code returned the right answer.

---

## ⚠️ Before your first command — check which branch you are on

> **The two paragraphs below are machine-specific** (B-035). They describe the
> checkout one teammate used. Session 08 ran on a different machine, where the
> repo is at `C:/Users/robo9/OneDrive/Desktop/odoo_2026` and `main` checked
> out, merged and pushed with no complaint. Read them as "this happened once,
> on one machine", not as instructions.

The main checkout on the build machine is parked on `test/backend-suite`, seven
commits behind `main` (B-014). Session 03 worked in a git worktree.

```bash
cd C:/Users/raval/Desktop/odoo_2026
git checkout main && git pull
git log --oneline -1
```

`.venv` and `db.sqlite3` live in the main checkout only and are gitignored, so a
fresh worktree or clone has neither. To run a worktree's code against the main
checkout's interpreter, use an absolute path — a venv's `site-packages` are
absolute, so this works:

```bash
PY="C:/Users/raval/Desktop/odoo_2026/project/backend/.venv/Scripts/python.exe"
```

A worktree also needs its own `npm install` — `node_modules` is gitignored too —
and it gets its own `db.sqlite3`, created from `BASE_DIR`, so `migrate` and
`seed` must be run there before anything works.

**`main` cannot be checked out in a second worktree** (B-029). It is held by
`.claude/worktrees/frontend-routing-setup-e9a159`, whose local `main` ref is
stale. Work against `origin/main` and push to it explicitly:

```bash
git fetch origin
git checkout -b integrate/<something> origin/main
git merge --no-ff <your-branch> -m "merge: ..."
git push origin HEAD:main
```

---

## Prerequisites

- Python 3.11+ (built and verified on 3.14.6)
- Node 18+ (**verified on v24.18.0, npm 11.16.0**)
- Git

**No database server needed.** The project runs on SQLite (D-011). PostgreSQL is
optional — set `DATABASE_URL` if you want it.

**Ollama is optional too.** It powers the Import Studio's column mapping and the
natural-language rule compilers, and everything works without it on a
deterministic path that says so. See *The local model* below.

---

## Backend

```bash
cd project/backend
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py seed --flush
./.venv/Scripts/python.exe manage.py runserver
```

`requirements.txt` gained **openpyxl** in session 09 (the import studio reads
.xlsx). A checkout whose venv predates that will fail on the first Excel upload
with `ModuleNotFoundError: openpyxl` -- re-run the pip install.

There are now **ten** Django apps: `core`, `accounts`, `employees`,
`attendance`, `timeoff`, `payroll`, `dashboard`, and the two added in session
09, `intelligence` (the import studio) and `workforce` (bulk operations, bonds,
playbooks). Both have migrations, so `migrate` is not optional on an existing
database.

Serves on `http://127.0.0.1:8000`.

> On macOS/Linux use `.venv/bin/python` instead of `./.venv/Scripts/python.exe`.

### Seeded logins — all password `demo1234`

| Email | Role | Use for |
|---|---|---|
| `admin@oxp.com` | Admin | everything, incl. user management |
| `aarav@oxp.com` | HR Payroll Manager | the main demo account |
| `sara@oxp.com` | HR Manager | HR without payroll access |
| `rahul@oxp.com` | HR Payroll User | proves read-only on salary rules |
| `john@oxp.com` | Employee | proves self-service scoping |

`manage.py seed --flush` is idempotent and reproducible (`random.seed(360)`).
It produces **22 employees · 24 contracts · 1731 attendance · 11 leave requests ·
4 payruns · 61 payslips · 976 lines · 6 warnings**, with December ₹14,73,360,
January ₹14,82,320 and February ₹15,58,320.41. `core/tests.py` pins all of it, so
a change that moves the demo's numbers fails there first.

The fourth payrun is `March 2026 (off-cycle correction)` — one payslip, left at
**Computed** on purpose, so the March payrun the demo creates finds a `DUPLICATE`
alongside the two `AC_MISSING` warnings and PRD criterion 4 is met on stage
(D-033). Do not mark it paid: the dashboard opens on the newest *paid* period
(D-034), and paying it would make a one-payslip run the default view.

---

## Frontend

```bash
cd project/frontend
npm ci            # or npm install
npm run dev
```

Serves on `http://localhost:5173`. CORS for that origin is already configured in
`config/settings.py`. `npm run build` is also clean (~835 kB JS, 35 kB CSS) and is
worth running before a handoff.

> **The frontend is complete** — 28 screens, and the top bar is built by the
> server from the signed-in account's capabilities, so it differs per role
> (D-028). Sign in with any account below; the login card's one-click role chips
> appear in `npm run dev` only and are compiled out of `npm run build` (D-038).

> **Do not pipe `npm run dev` into `tail`.** The pipe buffers Vite's output, so
> the server looks like it failed to start when it is actually running. Session
> 03 lost a few minutes to this.

---

## The local model — optional, and the product works without it

Added session 09. Powers the Import Studio's column mapping and the
natural-language rule compilers on Segments and Playbooks.

**You do not need it to run or demo the product.** With it off, column matching
falls back to a synonym dictionary and value profiling — 10 of 13 columns on the
bundled rosters — and every screen states which path produced its answer. What
you lose is accuracy on header names nobody put in the dictionary.

### Setting it up

```bash
# Windows, from the repository root
powershell -ExecutionPolicy Bypass -File scripts\setup-ai.ps1

# macOS or Linux
bash scripts/setup-ai.sh
```

Both are idempotent, safe to re-run, and **verify rather than assume**: after
pulling they fire one real mapping prompt at the model and report PASS or FAIL
with the latency, because "the pull succeeded" and "the model can do the job"
are different claims. If Ollama is not installed they print the download URL
and exit 0 rather than failing obscurely.

### Checking it later

```bash
cd project/backend
./.venv/Scripts/python.exe manage.py ai_doctor
```

A healthy machine prints, and **always exits 0** — it is a diagnostic, not a
gate:

```
  PASS  GPU                        8151 MB of video memory
  PASS  Ollama reachable           5 model(s) installed
  PASS  Model present              qwen2.5:7b
  PASS  Round trip                 1157 ms (0 ms of that the first load)
  PASS  Answer quality             mapped 'Sal (pm)' to wage
  PASS  Warm latency               711 ms
```

### Measured on the build machine (RTX 5060 Laptop, 8151 MiB)

* **Cold load ~11 s**, warm generation **~4.4 s** for a whole spreadsheet.
* Every request sends `keep_alive: 30m`, and the import screen warms the model
  when it opens — so the cold load is paid while somebody is choosing a file,
  not while they watch a progress bar.
* **One call per file, never one per column.** A forty-column sheet is a single
  generation.

If the *first* analysis of a session feels slow, that is the load and the second
will not be. If *every* analysis is slow, something else is resident — check
with `ollama ps`; two 7B models will not fit in 8 GB and Ollama will swap on
every call.

### Environment variables

| Variable | Default | Effect |
|---|---|---|
| `PP360_LLM_ENABLED` | `1` | `0` forces the deterministic path |
| `PP360_LLM_BASE` | `http://127.0.0.1:11434` | Ollama endpoint |
| `PP360_LLM_MODEL` | `qwen2.5:7b` | `qwen2.5:3b` under 8 GB VRAM |
| `PP360_LLM_KEEP_ALIVE` | `30m` | how long weights stay resident |
| `PP360_LLM_TIMEOUT` | `120` | seconds before a generation is abandoned |

Full detail, including the four failure modes that actually happen:
`docs/AI-SETUP.md`.

---

## Demo data for the import studio

`test-data/import/` holds seven rosters, each broken a different way, plus a
README narrating what each one proves. **Open them in Excel before importing
one** — that is the point of them being files rather than buttons (D-064).

| File | Use it to show |
|---|---|
| `01-meridian-complete.xlsx` | the control case: 22/22, no issues |
| `02-brightloom-handmade.xlsx` | junk rows above the header, Hinglish names, three date formats, rupees three ways, a TOTAL row |
| `03-northgate-legacy-export.xlsx` | annual salary where we store monthly — only the *distribution* reveals it |
| **`04-fieldforce-incomplete.xlsx`** | **the demo file**: no email, no bank details, no codes, five rows genuinely unimportable |
| `04b-fieldforce-bank-details.xlsx` | the second file 04 fetches bank details from; matches 14 of 16 on `Staff ID` |
| `05-northwind-acquisition.csv` | another company's vocabulary plus four people already on the roster |
| `06-vantage-240-headcount.xlsx` | 240 employees onboarded live |

Regenerate any of them (deterministic, so the figures stay true):

```bash
python test-data/generate.py
```

### A larger seeded roster

```bash
./.venv/Scripts/python.exe manage.py seed --flush --employees 200
```

Verified working: 200 employees, 223 contracts, 15,077 attendance rows, 545
payslips; employee list 158 ms, dashboard 644 ms; `verify_rules.py` still 28/28.

**It is not the default, deliberately** (D-066). The demo script's three-month
narrative quotes figures that are a function of the 22-person roster, and at 200
every one of them changes. Tell the scale story with `06-vantage-240-headcount.xlsx`
instead, where the audience watches it happen.
---

## Verification harnesses — run these before trusting anything

Three of the four need nothing but the venv:

```bash
cd project/backend
./.venv/Scripts/python.exe verify_rules.py    # 28/28 — the five graded rules
./.venv/Scripts/python.exe audit_permissions.py    # role matrix + row scoping
./.venv/Scripts/python.exe smoke_api.py       # 53/53 — the HTTP layer
./.venv/Scripts/python.exe manage.py seed --flush   # smoke_api dirties the DB
./.venv/Scripts/python.exe manage.py test     # 314/314 — Django suite, 10 apps
```

The fourth drives real HTTP and **needs a live server in another terminal**:

```bash
./.venv/Scripts/python.exe manage.py runserver    # terminal 1
./.venv/Scripts/python.exe probe_forms.py         # terminal 2 — 26/26
```

Without a server, `probe_forms.py` dies with a raw
`urllib.error.URLError: <urlopen error [WinError 10061] …>` traceback. That is a
missing server, not a broken harness (B-012).

**`smoke_api.py` writes to the development database** (B-010) — it leaves an
`April 2026 (smoke)` payrun that the dashboard then opens on, because it is the
most recent. Always `manage.py seed --flush` after running it, and before any
demo. `manage.py test` does **not** have this problem: it uses `TestCase`, so it
runs against a throwaway database.

All harnesses exit non-zero on failure, so they work in a pipeline.

**If any goes red, fix that before writing new code.** They are the only proof the
graded rules still hold.

### What each one is actually for

| Harness | Covers | Blind to |
|---|---|---|
| `verify_rules.py` | the five graded rules, at model level | anything HTTP |
| `smoke_api.py` | the HTTP layer, with payloads it builds itself | a form sending the wrong shape |
| `probe_forms.py` | the payload each **UI form** actually sends | anything with no probe case (D-020) |
| `manage.py test` | roles, derivations, gating, idempotence | the browser |

None of them clicks a button. Session 03 found a completely broken screen that
all four were green over — so **open the app too**.

---

## Useful endpoints

| | |
|---|---|
| API root | `http://127.0.0.1:8000/api/` (browsable) |
| Django admin | `http://127.0.0.1:8000/admin/` |
| Dashboard | `GET /api/dashboard/?period_start=2026-02-01&period_end=2026-02-28` |
| Payslip PDF | `GET /api/payslips/<id>/pdf/` |

```bash
# Log in and keep the token
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@oxp.com","password":"demo1234"}'
```

---

## Environment quirks on the build machine

- `gh` CLI is **not** installed. Plain `git` over HTTPS; credentials are cached.
- PostgreSQL and Docker are **not** installed (B-005).
- The console is **cp1252** — never print non-ASCII from a script (B-006). This
  aborted the seed once, after data had already been written.
- Chained heredocs in one Bash call fail to parse (B-007). Use the Write tool,
  or a `.py` file for scripted edits.
- `pdftotext` exists at `/mingw64/bin/pdftotext`; `pdftoppm` does not (B-003).


---

## Seed figures, as of session 07

`manage.py seed --flush` is idempotent and reproducible (`random.seed(360)`).
The figures below moved in session 07 when attendance began following each
contract's working schedule (D-047). **December and January did not move**, so
the demo's Dec < Jan < Feb evidence is unchanged.

| | Value |
|---|---|
| Employees / contracts | 22 / 24 |
| Attendance rows | **1731** (was 1746) |
| Leave requests | 11 |
| Payruns / payslips / lines / warnings | 4 / 61 / 976 / 6 |
| December 2025 net | ₹14,73,360.00 |
| January 2026 net | ₹14,82,320.00 |
| **February 2026 net** | **₹15,58,320.41** (was ₹15,58,667.87) |
| March 2026 (off-cycle) | ₹84,684.37, left `Computed` on purpose (D-033) |

**The harnesses no longer dirty the demo** (D-046). `seed --flush` resets the
security settings and network policies, and `audit_permissions.py` sweeps the
probe records it creates. Running the full verification pass immediately before
presenting is safe. After it, the state is 5 accounts, network enforcement off,
sessions not IP-bound.

### One trap worth knowing

**Any login rotates that account's token.** `accounts/api.py:186` deletes every
existing token for a user before issuing a new one, so an account holds exactly
one live session. Running any harness signs out a browser logged in as one of
the five demo accounts — which looks exactly like a session timeout and is not
one. Two people cannot demo from the same account at the same time.

---

## What changed in session 08

`seed --flush` now also clears **`AuditLog` and `LoginAttempt`** (D-050). Two
consequences worth knowing before a demo:

* The Administration dashboard opens on **"Nothing recorded yet"** and fills as
  people sign in. That is intended — every row a judge reads is then something
  that just happened in front of them, rather than harness residue naming
  accounts that no longer exist.
* **A lockout can now be cleared.** `LoginAttempt` is what `_recent_failures`
  counts, so before this a run of failed sign-ins could leave a demo account
  locked with no supported way out. If an account ever refuses a known-good
  password, `seed --flush` is the fix.

The register export now downloads with the server's own per-run filename —
`register-February-2026.csv` rather than `register.csv` for every month (D-052).

The payroll register opens on **February 2026 (20 payslips)**, not the March
off-cycle correction (D-051).

A leave request raised through the UI is created as **To Approve** and appears
immediately in HR's queue (D-053). If you are demonstrating the approval flow,
you no longer need to plant a row by hand.

---

## What changed in session 09

Two new Django apps and six new screens, all gated on the Admin (D-060).

| Area | What it is |
|---|---|
| `intelligence/` | The Import Studio. Reads a messy spreadsheet, maps its columns with three voters, joins a second file for what is missing, generates employee codes, previews everything, then writes |
| `workforce/` | Segments, bulk increment/exit/transfer/bond-issue, bonds with pro-rata recovery, and playbooks that raise reminders |
| `test-data/import/` | Seven demo rosters plus a README |
| `scripts/setup-ai.*` | Install, pull, warm and verify the local model |
| `docs/AI-SETUP.md` | The full setup and troubleshooting guide |

Things that will trip you up if nobody says so:

* **`requirements.txt` gained openpyxl.** An old venv fails on the first .xlsx
  upload.
* **Two new migrations.** `migrate` is not optional on an existing database.
* **`seed --flush` now also clears the workforce tables** and seeds two bond
  templates, five bonds, three segments and two playbooks, so those screens
  open on something real.
* **`AuditLog` gained two actions**, `DATA_IMPORTED` and `WORKFORCE_BULK`.
* **The Workforce menu group is invisible to four of the five roles**, which is
  correct and not a bug. Sign in as `admin@oxp.com` to see any of it.
* **Long commit messages and file edits must go through a file**, never a shell
  heredoc (B-040). It bit twice this session, once silently.
