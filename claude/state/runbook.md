# RUNBOOK

Get from a fresh clone to a running, seeded app. **Verify every command here at
each MEGATRON LAUNCH** — a stale runbook costs the next session its first hour.

Last verified: **session 04 (Michael), 2026-09-05 15:10 IST.** Every command below
was run in that session, including the frontend build and all four harnesses.

> **Do not add `--noreload` to `runserver`** (B-016). Session 04 did, then spent
> minutes chasing a phantom bug that was the server holding pre-fix code while a
> shell running the same code returned the right answer.

---

## ⚠️ Before your first command — check which branch you are on

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

---

## Prerequisites

- Python 3.11+ (built and verified on 3.14.6)
- Node 18+ (**verified on v24.18.0, npm 11.16.0**)
- Git

**No database server needed.** The project runs on SQLite (D-011). PostgreSQL is
optional — set `DATABASE_URL` if you want it.

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

---

## Frontend

```bash
cd project/frontend
npm ci            # or npm install
npm run dev
```

Serves on `http://localhost:5173`. CORS for that origin is already configured in
`config/settings.py`. `npm run build` is also clean (613 modules, ~6s) and is
worth running before a handoff.

> **The frontend is complete** — 18 screens, all reachable from the six-menu top
> bar. Sign in with any account below; the login card has one-click role chips.

> **Do not pipe `npm run dev` into `tail`.** The pipe buffers Vite's output, so
> the server looks like it failed to start when it is actually running. Session
> 03 lost a few minutes to this.

---

## Verification harnesses — run these before trusting anything

Three of the four need nothing but the venv:

```bash
cd project/backend
./.venv/Scripts/python.exe verify_rules.py    # 28/28 — the five graded rules
./.venv/Scripts/python.exe smoke_api.py       # 51/51 — the HTTP layer
./.venv/Scripts/python.exe manage.py seed --flush   # smoke_api dirties the DB
./.venv/Scripts/python.exe manage.py test     # 171/171 — Django suite, 7 apps
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
