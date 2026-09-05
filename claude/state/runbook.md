# RUNBOOK

How to get this project running from a fresh clone. **Verify these commands still
work at every MEGATRON LAUNCH** — a stale runbook costs the next session its
first hour.

> **STATUS: NOT YET APPLICABLE.** No application code exists. Session 01 got as
> far as the context system and planning. This file becomes real the moment
> T-010 (Django scaffold) lands.

---

## Prerequisites

- Python 3.11+
- Node 18+
- PostgreSQL 14+
- Git

## First-time setup

```bash
git clone https://github.com/MeghRaval30/odoo_2026.git
cd odoo_2026
```

*(Backend and frontend setup steps go here once T-010 and T-030 are done.)*

## Run

*(TBD)*

## Seed data

*(TBD — see T-028)*

## Test

*(TBD)*

---

## Known environment quirks on the original machine

- `gh` CLI is **not** installed. Use plain `git`; Git Credential Manager handles
  browser authentication on the first push.
- `pdftoppm` is unavailable, so PDF page rendering fails. `pdftotext` does work,
  at `/mingw64/bin/pdftotext`.
- The Windows console is cp1252. Python scripts that print non-ASCII need
  `python -X utf8` plus `sys.stdout.reconfigure(encoding='utf-8')`, or should
  write to a file opened with `encoding='utf-8'`.
- Shell is Git Bash. Chained heredocs in a single command have proven fragile —
  write files one at a time if a heredoc fails to parse.
