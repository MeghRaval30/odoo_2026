# Test data

Six rosters for demonstrating **Workforce → Data Import**. Open them in Excel
first — the point is that they look exactly like what a real company hands you,
and none of them is in our format.

Regenerate any time (deterministic, so the figures in the demo script stay true):

```bash
python test-data/generate.py
```

---

## The files

| File | Rows | What it is | What it exercises |
|---|---|---|---|
| `01-meridian-complete.xlsx` | 22 | Tidy, complete, every field present | The control case. Imports clean, no issues. |
| `02-brightloom-handmade.xlsx` | 22 | A spreadsheet somebody kept by hand since 2019 | Header detection, transforms, duplicate and missing email |
| `03-northgate-legacy-export.xlsx` | 18 | A clean export from another HR system | Value profiling — it is structurally perfect and semantically wrong |
| `04-fieldforce-incomplete.xlsx` | 16 | **The demo file.** People and pay, nothing else | Missing required fields, the second-file join, code generation |
| `04b-fieldforce-bank-details.xlsx` | 15 | What finance keeps separately | Joining a supplementary file onto the first |
| `05-northwind-acquisition.csv` | 12 | Another company's roster after an acquisition | Value mapping across vocabularies, duplicate detection |

---

## 01 — Meridian Systems, complete

Nothing wrong with it. Employee code, both name halves, work email,
department, position, ISO dates, monthly salary, bank account, IFSC, PAN.

Worth showing first so the harder files are read against a baseline: every
column maps, no issues, straight to import.

---

## 02 — Brightloom Textiles, hand-kept

The one everybody recognises.

- **Row 1** is the company name, **row 2** a note, **row 3** blank. The header
  is on **row 4**. An importer that assumes row 1 destroys this file silently.
- **Hinglish and abbreviated headers**: `Emp Naam`, `Dept.`, `DOJ`, `Sal (pm)`,
  `Mob No`, `A/C No`.
- **Three date formats in one column**: `15-03-2021`, `02/07/2019`, `2020-11-30`.
- **Rupees three ways**: `Rs 45,000`, `72,000`, `38500/-`.
- **Departments abbreviated**: `Engg`, `Sls`, `Mktg`, `Ops`.
- **Names cased inconsistently**, some with leading spaces: `rajesh kumar`,
  `PRIYA NAIR`, `  ROHIT Verma`.
- **Two people have no email**, and **one email is a duplicate** of another row.
- **Two have no bank details.**
- **A `TOTAL` row at the bottom** which is not a person.

Expect: header found on line 4, three rows ignored, the total row dropped, one
row blocked as a duplicate, two offered a derived email.

---

## 03 — Northgate Systems, legacy export

A machine wrote this, and it is worse for it. Structurally immaculate, so
nothing looks wrong, and two things are.

- **`ANNUAL_CTC`** — the salary is annual where we store monthly. Only the
  *distribution* reveals it: a median of ₹9,00,000 is not a monthly wage. The
  studio proposes dividing by twelve, as a step you can see and remove.
- **`NULL` as a literal string** in blank bank cells.
- `ALL_CAPS_UNDERSCORE` headers, names already split, trailing whitespace,
  `Y`/`N` status.
- Its departments are `Technology`, `Revenue`, `People`, `Operations` —
  another vocabulary for the same units.

---

## 04 — Fieldforce Logistics, incomplete → **use this one for the demo**

Sixteen people. It has names, sections, roles, joining dates, pay and phone
numbers, and it is missing three things the software needs:

- **no email column at all**
- **no bank details at all**
- **no employee codes** in our format — it has `FF-101` style staff ids

On top of that, **two people have no joining date** and **three have no
salary**, so those rows genuinely cannot be imported and have to be reported
rather than guessed at.

This is the file that shows the whole flow:

1. Import it. The studio maps what is there and says plainly what is missing.
2. It offers to **fetch the missing bank details from a second file** — give it
   `04b`. It works out the join key itself and reports what matched.
3. It offers to **generate employee codes** in a pattern you choose, with a
   live preview.
4. The rows that are genuinely short of data stay blocked, listed by name.

## 04b — the bank details supplement

What finance keeps in its own spreadsheet: staff id, name, account number,
IFSC, PAN, account type.

Deliberately not a perfect mirror of `04`:

- **Two of the sixteen are missing** (`FF-107`, `FF-113`) — finance never got them.
- **One person is on this list and not on HR's** (`FF-098`, Bhaskar Rao).

So the join has something real to report: matched, not found, and unused.

---

## 05 — Northwind, acquisition

Twelve people from a company that was just bought.

- **`Business Unit`** instead of Department, holding `Technology`, `Revenue`
  and `People Ops` — which are our Engineering, Sales and HR under other names.
- **Four of the twelve already work here** (`john@oxp.com`, `priya@oxp.com`,
  `meera@oxp.com`, `billy@oxp.com`) and must be caught rather than duplicated.
- CSV rather than xlsx, because a due-diligence export usually is.

---

## A note on what these prove

Each file fails in a way a *different* part of the pipeline catches, and only
one of those parts is the language model:

| File | Caught by |
|---|---|
| 02 | Header row scoring, then the transform chain — no model involved |
| 03 | Value profiling, arithmetic over the actual cells — no model involved |
| 04 | Required-field checking and the join — no model involved |
| 05 | Value mapping, where the model does help, over a dictionary that handles most of it |

The model reads *meaning*: that `Emp Naam` is a name and `Sal (pm)` is a
monthly wage. Everything structural is deterministic, which is why the import
still works with the model switched off.
