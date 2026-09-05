# DEMO SCRIPT — 5:00, two end-to-end scenarios + the closing move

Read this aloud while clicking. Every record name, button label and number below
was taken from the seeded database and the frontend source, not from memory.

**Notation:** `Menu ▾ → Item` is the top bar · `[Button]` is a button you click ·
`Field` = `value` is something you type or select · *Column* is a table heading.

---

## Time budget — it adds to 5:00

| Section | From | To | Length |
|---|---|---|---|
| Open | 0:00 | 0:15 | 0:15 |
| **Scenario A** — employee to payslip | 0:15 | 2:50 | 2:35 |
| **Scenario B** — allocation to balance | 2:50 | 3:55 | 1:05 |
| **Closing move** — the filter proof | 3:55 | 4:40 | 0:45 |
| Land it | 4:40 | 5:00 | 0:20 |

If you are running long, cut A2 (the contract-history beat) to a single sentence
and cut B3. Never cut the closing move.

---

## Pre-flight (do this 10 minutes before, not on stage)

- [ ] **Backend up.** `cd project/backend` then `./.venv/Scripts/python.exe manage.py runserver` → `http://127.0.0.1:8000`
- [ ] **Frontend up.** `cd project/frontend` then `npm run dev` → `http://localhost:5173`
- [ ] **Database freshly seeded.** If and only if the demo has already been run
      once on this database: `./.venv/Scripts/python.exe manage.py seed --flush`.
      It is idempotent (`random.seed(360)`), so the numbers in this script come
      back identical. Do **not** reseed if someone else is mid-demo.
- [ ] **Only three payruns exist** — December 2025, January 2026, February 2026,
      all `Paid`. If a fourth ("March 2026") is already there from a rehearsal,
      reseed, or rename your new one to "March 2026 — live".
- [ ] **Browser at 80% zoom** (Ctrl+Minus twice). The payslip computation table
      is 7 columns wide and the payrun wizard step 2 is 6 — at 100% they scroll.
- [ ] **Log in before you present** and land on `#/dashboard`, then go back to
      `#/employees`. A cold first render on stage costs three seconds.
- [ ] **Close the backend console** or move it off-screen — `Send Payslips` uses
      the console email backend and will dump 20 emails into it.
- [ ] Have a second tab open at `http://localhost:5173/#/dashboard` as insurance.

### Logins — password is `demo1234` for all five

| Email | Role | Notes |
|---|---|---|
| **`admin@oxp.com`** | Admin | **Use this one.** Pre-filled on the login card. Only role that sees `Time Off ▾ → Time Off Types` and `User Management`. |
| `aarav@oxp.com` | HR Payroll Manager | Full payroll + HR, no admin. Fine as a fallback. |
| `sara@oxp.com` | HR Manager | No payroll menu — useful if asked about permissions. |
| `rahul@oxp.com` | HR Payroll User | Read-only on Salary Rules. |
| `john@oxp.com` | Employee | Sees only his own records. |

The login card has a **Demo accounts** row of one-click chips: `Admin`,
`Payroll Manager`, `HR Manager`, `Payroll User`, `Employee`. Clicking a chip
fills both fields. Then `[Sign in]`.

### The seeded records this script depends on

| What | Value |
|---|---|
| Demo employee | **John Dsouza** · `EMP/2025/0003` · Engineering · Developer · Full Time |
| His two contracts | `CON/2025/0003` 01 Jul 2025 – 31 Dec 2025 · ₹1,03,000 · **Expired**<br>`CON/2026/0002` 01 Jan 2026 – open · ₹1,10,000 · **Running** |
| The other multi-contract employee | Aarav Mehta — ₹78,000 → ₹85,000 on the same dates |
| No bank account (the two warnings) | **Anita Oliver** (`EMP/2025/0005`, Sales) and **Meera Iyer** (`EMP/2025/0012`, Finance) |
| Allocation to move | **Priya Sharma** · Paid Time Off 2026 · Allocated 20 / Taken 0 / Remaining 20 · Approved |
| Allocation already consumed | **Audrey Peterson** · 20 / 3 / **17** |
| Type that requires allocation | **Paid Time Off** and **Comp Off**. Sick Leave and Unpaid Leave do not. |
| Existing payruns | December 2025 ₹14,73,360 net · January 2026 ₹14,82,320 · February 2026 ₹15,63,027.86 — all `Paid`, 20 payslips each |
| Payrun you create live | **March 2026**, 01–31 Mar 2026, Regular Salary, 20 employees |

---

## SCENARIO A — employee to payslip (0:15 → 2:50)

The whole spine of the product in one unbroken path. Do not stop to explain
anything that is not on screen.

| # | At | Click | Say |
|---|---|---|---|
| **A1** | 0:15 | `Employees ▾ → Employees`. Kanban is the default view. Click the **John Dsouza** card. | "One employee record. Work Information, Private Information, HR Settings — and four smart buttons across the top, counted server-side." |
| | | Point at the smart buttons: **2 Contracts** · **35 Attendance** · **1 Time Off** · **1 Allocations**. | "Two contracts. That number is the whole point of the next thirty seconds." |
| **A2** | 0:27 | Click the **Contracts** smart button. It navigates to `#/contracts?employee=25` — the Contracts list filtered to John. | "He has held two contracts. The July 2025 one at ₹1,03,000 is **Expired**. The January 2026 one at ₹1,10,000 is **Running** — green left edge." |
| | | Point at the *Period* and *Wage* columns on both rows. | "So there is no such thing as 'his salary'. There is only his salary **for a period**. Payroll has to resolve that, and it does." |
| **A3** | 0:45 | `Payroll ▾ → Payruns`. Then **[New Payrun]**. | "Three payruns, all paid. New one." |
| | | Step **1 · Scope**: `Payrun name` = `March 2026` · `Period start` = `01/03/2026` · `Period end` = `31/03/2026` · `Salary structure` = `Regular Salary` · leave `Employee type` = `All employee types`. | "Step one collects scope only. Name, period, structure. **Nothing has been created.** There is no payrun record behind this modal." |
| **A4** | 1:00 | **[Next]**. | "Step two is a pure query. It asks the server: for this period, who is eligible, and *which contract governs them*." |
| | | Step **2 · Employees** — 20 rows, `1–20 / 20`, badge `20 selected`. Find the **John Dsouza** row. | "Twenty employees. The two interns are gone — their contracts run on the Intern Salary structure, so choosing Regular Salary scoped them out." |
| | | Point at John's *Contract from* = **01 Jan 2026** and *Wage* = **₹1,10,000.00**. | "**Contract from: January 2026. Wage: one lakh ten.** If I had set this period to December, this same row would read July 2025 and ₹1,03,000. That is graded rule one, resolved before a single record exists." |
| **A5** | 1:20 | **[Create payrun (20)]**. It lands on the payrun detail page. | "*Now* it exists. Twenty payslip shells, all zeros, state **Draft**." |
| **A6** | 1:30 | **[Compute]**. Green banner: `Compute complete.` | "Compute. Every payslip runs the fourteen rules of the Regular Salary structure against that employee's resolved contract, their March attendance and their approved leave." |
| | | Point at the stat tiles — *Payslips* 20, *Gross*, *Net*. | "Gross and net are sums of the payslip lines, not stored columns." |
| **A7** | 1:45 | Scroll to the card titled **Pre-validation checks — 0 error(s), 2 warning(s)**. It sits *above* the payslip table. | "Before I validate anything, the system tells me what is wrong with this run." |
| | | Read the two amber rows. | "**Bank account missing · Anita Oliver.** **Bank account missing · Meera Iyer.** Two of twenty have no account on file. I would have paid them into nothing." |
| | | Point at the *Flags* column on those two rows in the payslips table — amber `AC_MISSING` badges. | "The same flag is on their payslip rows. Zero errors here, so **[Validate]** is available. If either had been an *error* — a negative net — Validate would still be greyed out. The state machine will not let me finalise a broken run." |
| **A8** | 2:05 | **[Validate]**. Banner: `Validate complete.` Stepper moves to **Validated**. | "Validate." |
| **A9** | 2:15 | **[Mark Paid]**. Banner: `Mark paid complete.` | "Mark paid. That locks the run — a paid payrun cannot be recomputed." |
| **A10** | 2:25 | In the *Payslips* table click **John Dsouza**'s row (`PAY/2026/03/…`). | "One payslip." |
| | | Point at the **Contract resolved for this period** card: *Reference* `CON/2026/0002`, *Contract wage* ₹1,10,000. | "It names the contract it used. Not his newest — the one that covers March." |
| | | Scroll to **Salary computation — evaluated in sequence order**. | "Fourteen lines, in the order the engine ran them. Seq 1 Basic. Ten through fifty-five, the allowances — HRA, Standard, Bonus, LTA, Fixed, Overtime. **Seq 60 Gross** — the sum of everything above it. Then the deductions: LOP, Labour Welfare, Provident Fund, ESIC, Professional Tax. **Seq 110 Net** — Gross minus everything below sixty." |
| | | | "Nothing here is hardcoded. Change rule 60's expression and every payslip changes. That is graded rule four." |
| | 2:42 | **[Print Payslip]** — opens the PDF in a new tab. Glance at it, close the tab. | "And it prints." |

**Optional 10-second flourish if you are ahead of schedule (insert after A2):**
on the Contracts page click **[Resolve by period]**. The probe is already
defaulted to `01/12/2025` – `31/12/2025`. Click **[Resolve]** and John Dsouza's
*Wage for this period* reads **₹1,03,000** — the historical contract. That is
the same resolver the payrun wizard uses, run against a different window.

---

## SCENARIO B — allocation to balance (2:50 → 3:55)

| # | At | Click | Say |
|---|---|---|---|
| **B1** | 2:50 | `Time Off ▾ → Allocations`. | "Twenty-two allocations. *Allocated*, *Taken*, *Remaining*." |
| | | Point at **Audrey Peterson** — 20 / 3 / **17**. | "Audrey has taken three of twenty. *Taken* is not a stored counter — it is summed from her approved requests every time you look. Refuse one and this number goes back up on its own." |
| | | Point at **Priya Sharma** — 20 / 0 / **20**. | "Priya has taken none. Watch this row." |
| **B2** | 3:04 | `Time Off ▾ → Time Off Requests`, then **[New Request]**. | |
| | | `Employee` = `Priya Sharma` · `From` = `06/04/2026` · `To` = `08/04/2026` · `Time off type` = **`Comp Off (allocation required)`**. Then **[Submit]**. | "Three working days in April. Against Comp Off — which is marked *requires allocation*, and Priya has no Comp Off allocation." |
| | | Red banner appears: *No approved Comp Off allocation covering 2026-04-06 – 2026-04-08. An allocation must be created and approved before this request can be submitted.* | "**Refused.** And that message is the server's, not the browser's — the rule lives in the model, the API surfaces it verbatim. That is graded rule three." |
| **B3** | 3:26 | Change `Time off type` to **`Paid Time Off (allocation required)`**. A balance table appears on the form: *Allocated* 20.00 · *Taken* 0 · *Remaining* 20.00. Then **[Submit]**. | "Switch to Paid Time Off, where she *does* have a balance — and the form reads it live. Twenty available. Submit, and it saves." |
| **B4** | 3:38 | The list is sorted newest-first, so the row you just filed is on top and Priya's **08 Mar 2026 → 10 Mar 2026** row is directly below it — status **To Approve**, *Duration* **2.00**. Click its **[Approve]**. | "Here is one of hers already submitted for approval. Two days. Approve." |
| **B5** | 3:47 | `Time Off ▾ → Allocations`. Point at the **Priya Sharma** row. | "Allocated twenty. **Taken two. Remaining eighteen.** Nobody wrote eighteen anywhere. Remaining equals Allocated minus Taken, computed on read." |

> **Say this in B3/B4 so the two rows do not confuse anyone:** a new request is
> filed as a **Draft** — the approve/refuse buttons only appear once it is
> **To Approve**. So the April row you just created sits in Draft above Priya's
> March row, which is already submitted. Approve the March one. If you would
> rather avoid the two-row moment entirely, skip B3 (cancel the modal after the
> refusal) and go straight to approving the March row.

---

## CLOSING MOVE — the filter proof (3:55 → 4:40)

This is the strongest twenty seconds in the demo. The problem statement warns
explicitly against hardcoded dashboards. Slow down. Let the screen do the work.

| # | At | Click | What appears |
|---|---|---|---|
| **C1** | 3:55 | `Reports` (top bar, far right) → **`Payroll Dashboard`**. | `Reports` is a **dropdown with two items** — `Payroll Dashboard` and `Payroll Register`. You want the first. It opens on **March 2026** — the payrun you created ninety seconds ago is already the default period. Say that out loud. |
| | | `Period` → **`February 2026`**. | *Total Net Paid* → **₹ 15.63L**. Exact: **₹15,63,027.86** across 20 payslips. |
| **C2** | 4:05 | `Period` → **`December 2025`**. Then stop talking for two seconds. | *Total Net Paid* → **₹ 14.73L** (**₹14,73,360**). *Payslips*, *Avg Net / Employee*, *Approved Time Off Days*, *Attendance Health*, the Net Payroll Trend line, the Net Pay by Department bars, the Payslip Status donut, the Pre-Validation Alerts and the Time Off Overview **all re-drive together**. |
| | | | "**Fifteen lakh sixty-three thousand, to fourteen lakh seventy-three thousand.** One dropdown. Every card on this page just re-queried six models — Employee, Contract, Payslip, PayslipWarning, Attendance, TimeOffRequest. They are listed at the bottom of the page." |
| **C3** | 4:20 | `Department` → **`Engineering`**. | *Total Net Paid* → **₹ 4.69L** (**₹4,68,760**) — six payslips of twenty. |
| | | `Period` → **`February 2026`**, Engineering still selected. | *Total Net Paid* → **₹ 5.04L** (**₹5,03,997.74**). The *Department Overview* card shows Engineering ₹5,03,997.74 and every other department at zero, because the slice is real. |

**Land it (4:40 → 5:00):**

> "Two independent filters, four different totals, nothing cached and nothing
> stored. The dashboard is a query, not a screenshot. Everything you have seen
> in the last five minutes — the contract that changes with the period, the
> warnings that arrive before validation, the leave balance that is subtraction
> rather than a counter — is the same idea: derive it, don't store it. Thank
> you."

> **Number check before you present.** The KPI cards use compact notation —
> the *Total Net Paid* tile literally reads `₹ 15.63L`, not `₹15,63,027.86`. The
> exact rupee figures are on the **Payruns** list (*Net* column) and in the
> **Department Overview** rows. Say the lakh figure, point at the exact one if
> challenged.

---

## The five graded business rules, and where each one is visibly proven

Point at the screen when you say these. One line each is enough.

| # | Rule | Proven at | What the presenter points at |
|---|---|---|---|
| **1** | **Period-based contract selection.** Payroll picks the contract valid for the payrun's period, not the most recent. No two `Running` contracts may overlap. | **A2 + A4 + A10** | John Dsouza's two contracts (₹1,03,000 Expired / ₹1,10,000 Running); the wizard's *Contract from* column reading **01 Jan 2026** for a March period; the payslip's **Contract resolved for this period** card naming `CON/2026/0002`. |
| **2** | **Derived weekly hours.** Weekly hours come from the schedule's day lines, never typed. | **A4** (in path) and `Employees ▾ → Working Schedules` (if asked) | The wizard's *Working hours* column reads **40.00 hours/week** for John — computed from five day lines. On the Working Schedules screen the *Hours / week* and *Days / week* columns are read-only tiles above an editable day-line table: add a line and the tile moves. |
| **3** | **Allocation-gated leave.** A type marked *Requires Allocation* cannot be requested without an approved allocation. `Remaining = Allocated − Taken`. | **B2 + B5** | The server's own refusal on Comp Off; then Priya Sharma's row moving 20 / 0 / 20 → **20 / 2 / 18** after one approval. |
| **4** | **Sequenced salary rules.** Rules run in `sequence` order so later rules read earlier results. Gross = Basic + Allowances, Net = Gross − Deductions. | **A10** | The **Salary computation — evaluated in sequence order** table: Seq 1 Basic → Seq 55 Overtime → **Seq 60 Gross** → Seq 65–100 deductions → **Seq 110 Net**. |
| **5** | **Pre-finalization warnings.** Problems surface *before* validation — missing bank account, duplicate payslip. | **A7** | The **Pre-validation checks** card sitting *above* the payslip table and *before* `[Validate]`: two `AC_MISSING` warnings for Anita Oliver and Meera Iyer, plus the `AC_MISSING` badges in the *Flags* column. |

---

## If it breaks

**The one most likely failure: the payrun wizard's `[Next]` returns an empty
step 2, or step 2 shows red `No contract for period` badges.** You typed the
period wrong. It must be `01/03/2026` – `31/03/2026`. Fix the two date fields
and press `[Next]` again — step 1 has created nothing, so there is no mess to
clean up. If it still comes back empty, `Salary structure` is set to
`Intern Salary`; switch it to `Regular Salary`.

**Second most likely: a stale token.** Any screen showing
`Session expired. Please sign in again.` means the backend restarted. Sign in
again with `admin@oxp.com` / `demo1234` and resume from the top of the current
scenario — nothing you have already done is lost.

**Rules for going wrong on stage:** never open devtools, never open a terminal,
never say "that's strange". If a beat fails twice, say *"I'll come back to
that"* and move to the next section. **The closing move needs no setup from
Scenarios A or B** — you can jump straight to `Reports` → `Payroll Dashboard`
from anywhere and still finish strong.

**Do not click `Reports` → `Payroll Register` by mistake.** It is the second item
in the same dropdown and it is a different screen: one row per payslip, one
column per rule code, with a `Payrun` selector instead of the `Period` and
`Department` filters. It is a genuinely good screen, but it is **not** the
closing move and it will not re-drive on a period change. If you land there,
reopen `Reports` and pick `Payroll Dashboard`.

---

## Things on screen that are not bugs, so do not react to them

- After **[Compute]** the four-step progress strip (Draft · Computed · Validated
  · Paid) may not highlight the current step, and the state chip may render grey
  instead of amber. **The chip text is correct** — it reads `Computed`,
  `Validated`, `Paid` in turn, and the action buttons enable and disable
  correctly. Ignore the highlight; narrate the chip.
- Choosing `Comp Off` on the New Time Off Request form shows a balance table
  with headings and **no rows**. That is the point — she has no Comp Off
  balance. Say so.
- `[Send Payslips]` works and returns *"20 payslip(s) sent, 0 skipped"*, but the
  mail backend is the console, so the mail lands in the backend terminal. It is
  in the action bar if you want to mention it; it is not in the timed script.
- `[Export Register]` downloads a CSV. Also not in the timed script.

---

## Rehearsal notes

- Run it end to end **twice** before submitting, with a stopwatch.
- Reseed between rehearsals (`manage.py seed --flush`) so March 2026 does not
  accumulate and so Priya's balance is back at 20 / 0 / 20.
- Have this file open on a second screen or printed. Do not present from memory.
- The three numbers you must not fumble: **15,63,028 → 14,73,360 → 5,03,998**.
