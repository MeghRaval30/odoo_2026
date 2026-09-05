# RUNBOOK

Get from a fresh clone to a running, seeded app. **Verify every command here at
each MEGATRON LAUNCH** — a stale runbook costs the next session its first hour.

Last verified: session 01 (Michael), 2026-09-05. All commands below were run.

---

## Prerequisites

- Python 3.11+ (built and verified on 3.14.6)
- Node 18+ (verified on 24.19.0)
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
npm install
npm run dev
```

Serves on `http://localhost:5173`. CORS for that origin is already configured.

> **As of the session-01 handoff the frontend renders nothing** — only
> `src/api.js` and `src/index.css` exist. `src/App.jsx` is still the Vite demo.

---

## Verification harnesses — run these before trusting anything

```bash
cd project/backend
./.venv/Scripts/python.exe verify_rules.py    # 28/28 — the five graded rules
./.venv/Scripts/python.exe smoke_api.py       # 51/51 — the HTTP layer
```

Both exit non-zero on failure, so they work in a pipeline. `smoke_api.py` cleans
up its own previous run, so it is safe to run repeatedly.

**If either goes red, fix that before writing new code.** They are the only
proof the graded rules still hold.

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
