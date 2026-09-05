# DEMO SCRIPT — 5 minutes, 2 end-to-end scenarios

A required hackathon deliverable, and our best scope-discipline tool: **anything
not in this script is optional.** Write it early, keep it honest, rehearse it in
the final two hours.

> **STATUS: OUTLINE ONLY.** Flesh out with exact click paths and seeded record
> names once the build is running (T-060).

---

## Scenario A — Employee to Payslip

The full spine of the product, in one unbroken path. Roughly 3 minutes.

1. Log in as **HR Payroll Manager**
2. Open an employee from the **Kanban** view → the unified Employee Form
3. Smart buttons → **Contracts**, showing contract history with exactly one
   `Running` contract, and say out loud that payroll will pick *this* one because
   it covers the payrun period
4. Show the **Working Schedule** and point out that weekly hours are **derived**
   from the day lines, not typed
5. Show the employee's **Attendance** for the period
6. Payroll → **Salary Structure** → the ordered rule list, and open one rule to
   show its computation method
7. Payroll → Payruns → **NEW** → step 1 defines scope → **Continue** → step 2
   select employees → **Create Payrun**.
   Emphasise: *no record existed until step 2* — this is a specific behaviour the
   problem statement calls out
8. **COMPUTE** → payslips generate
9. **Show the warnings** — missing bank account, duplicate payslip — *before*
   validating. This is graded rule #5
10. Open a payslip → the rule-by-rule **Salary Computation**, Basic → allowances
    → Gross → deductions → Net
11. **VALIDATE** → **MARK PAID**
12. **PRINT PAYSLIP** (PDF) → **SEND PAYSLIPS** (bulk email)

## Scenario B — Leave allocation to balance consumption

The rule the statement cares most about after payroll computation. Roughly
90 seconds.

1. Time Off ▼ → **Time Off Types** → open one marked **Requires Allocation**
2. Attempt a request against it with no allocation → **show it being blocked**
3. Time Off ▼ → **Allocations** → create one → **approve** it → balance appears
4. Submit the request again → now permitted
5. **Approve** it → show **Allocated / Taken / Remaining** update live
6. Open the request → show which allocation it consumed
7. Dashboard → **Time Off Overview** reflects it immediately

## Closing — 30 seconds

Open the **Payroll Dashboard**. Change the **Period** filter and show every KPI
card and chart re-driving from live data.

That single interaction is the strongest thing we can show: the problem statement
explicitly warns against hardcoded dashboards, and this proves ours aggregates
live across Employees, Contracts, Payslips, Attendance and Time Off.

---

## Rehearsal notes

- Run it end to end at least twice before submitting
- Have the seeded login credentials written down, not remembered
- Know exactly which seeded employee has the missing bank account, so the warning
  appears on cue
- If something breaks live, move on — never debug during the demo
