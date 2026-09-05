# BLOCKERS & DEAD ENDS

**Read this before debugging anything.** A previous session may have already
burned an hour on exactly what you are about to try.

Record not just what is broken, but **what was tried and why it failed**. That
negative information is the most valuable thing in this file.

---

## OPEN BLOCKERS

### B-001 — Hackathon start time is assumed, not confirmed
**Severity:** medium · **Opened:** session 01 (Michael)

The clock in `current-state.md` assumes a 2026-09-05 09:00 IST start. It was
inferred from file modification timestamps, not told to us. Every scope gate
depends on it. Ask the user to confirm the real start and end times, then correct
`current-state.md`.

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
