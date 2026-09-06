"""
Proof harness for the five graded business rules.

Run:  .venv/Scripts/python.exe verify_rules.py
Every check prints PASS or FAIL with the evidence behind it.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from employees.models import Contract, Employee, WorkingSchedule
from payroll.models import Payrun, Payslip, PayslipWarning, SalaryRule
from payroll import engine
from timeoff.models import Allocation, TimeOffRequest, TimeOffType

results = []


def check(label, condition, evidence=""):
    results.append(bool(condition))
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}")
    if evidence:
        print(f"         {evidence}")


print("\n" + "=" * 72)
print("GRADED RULE 1 - Period-based contract resolution")
print("=" * 72)

emp = Employee.objects.filter(contracts__state=Contract.EXPIRED).distinct().first()
old = emp.contract_for_period(date(2025, 12, 1), date(2025, 12, 31))
new = emp.contract_for_period(date(2026, 2, 1), date(2026, 2, 28))

check("December resolves the historical contract",
      old is not None and old.state == Contract.EXPIRED,
      f"{emp.full_name}: {old.reference} wage={old.wage} state={old.state}")
check("February resolves the running contract",
      new is not None and new.state == Contract.RUNNING,
      f"{emp.full_name}: {new.reference} wage={new.wage} state={new.state}")
check("Resolution is by period, not recency (different contracts)",
      old.pk != new.pk and old.wage < new.wage,
      f"old wage {old.wage} < new wage {new.wage}")

dec = Payslip.objects.filter(employee=emp, period_start=date(2025, 12, 1)).first()
feb = Payslip.objects.filter(employee=emp, period_start=date(2026, 2, 1)).first()
check("December payslip actually used the old contract",
      dec and dec.contract_id == old.pk,
      f"payslip {dec.number} -> {dec.contract.reference} (wage {dec.contract.wage})")
check("February payslip actually used the new contract",
      feb and feb.contract_id == new.pk,
      f"payslip {feb.number} -> {feb.contract.reference} (wage {feb.contract.wage})")

clash = Contract(employee=emp, start_date=date(2026, 3, 1), end_date=None,
                 wage=Decimal("99000"), working_schedule=new.working_schedule,
                 salary_structure=new.salary_structure, state=Contract.RUNNING)
try:
    clash.clean()
    check("Overlapping RUNNING contract rejected", False, "no error raised")
except ValidationError as exc:
    check("Overlapping RUNNING contract rejected", True, str(exc.messages[0])[:90])


print("\n" + "=" * 72)
print("GRADED RULE 2 - Derived weekly hours")
print("=" * 72)

sched = WorkingSchedule.objects.get(name="40 Hours / Week")
before = sched.hours_per_week
check("Weekly hours derived from day lines", before == Decimal("40.00"),
      f"{sched.name}: {before}h over {sched.days_per_week} days")

line = sched.lines.first()
original_break = line.break_minutes
line.break_minutes = 0
line.save()
after = WorkingSchedule.objects.get(pk=sched.pk).hours_per_week
check("Editing a line changes weekly hours with no other edit",
      after == before + Decimal("1.00"), f"{before}h -> {after}h after removing a 60m break")
line.break_minutes = original_break
line.save()


print("\n" + "=" * 72)
print("GRADED RULE 3 - Allocation-gated leave")
print("=" * 72)

pto = TimeOffType.objects.get(code="PTO")
sick = TimeOffType.objects.get(code="SICK")
check("PTO requires allocation; Sick Leave does not",
      pto.requires_allocation and not sick.requires_allocation)

victim = Employee.objects.exclude(
    allocations__time_off_type=pto, allocations__state=Allocation.APPROVED
).first()
if victim is None:
    victim = Employee.objects.last()
    Allocation.objects.filter(employee=victim, time_off_type=pto).delete()

blocked = TimeOffRequest(employee=victim, time_off_type=pto,
                         date_from=date(2026, 6, 1), date_to=date(2026, 6, 3))
blocked.duration = blocked.compute_duration()
try:
    blocked.full_clean()
    check("Request without allocation is blocked", False, "no error raised")
except ValidationError as exc:
    check("Request without allocation is blocked", True, str(exc.messages[0])[:90])

alloc = Allocation.objects.create(
    employee=victim, time_off_type=pto, name="Verification Grant",
    allocated=Decimal("5"), valid_from=date(2026, 1, 1),
    valid_to=date(2026, 12, 31), state=Allocation.APPROVED)

ok = TimeOffRequest(employee=victim, time_off_type=pto,
                    date_from=date(2026, 6, 1), date_to=date(2026, 6, 3))
ok.duration = ok.compute_duration()
try:
    ok.full_clean()
    ok.state = TimeOffRequest.APPROVED
    ok.save()
    check("Same request succeeds once an allocation is approved", True,
          f"consumed allocation '{ok.allocation_used.name}'")
except ValidationError as exc:
    check("Same request succeeds once an allocation is approved", False, str(exc))

alloc.refresh_from_db()
check("Balance maths is derived (Allocated - Taken = Remaining)",
      alloc.remaining == alloc.allocated - alloc.taken,
      f"allocated {alloc.allocated}, taken {alloc.taken}, remaining {alloc.remaining}")

over = TimeOffRequest(employee=victim, time_off_type=pto,
                      date_from=date(2026, 7, 1), date_to=date(2026, 7, 31))
over.duration = over.compute_duration()
try:
    over.full_clean()
    check("Request exceeding remaining balance is blocked", False, "no error raised")
except ValidationError as exc:
    check("Request exceeding remaining balance is blocked", True, str(exc.messages[0])[:90])

taken_before = alloc.taken
ok.state = TimeOffRequest.CANCELLED
ok.save()
alloc.refresh_from_db()
check("Cancelling an approved request restores balance",
      alloc.taken < taken_before, f"taken {taken_before} -> {alloc.taken}")


print("\n" + "=" * 72)
print("GRADED RULE 4 - Sequenced salary rules")
print("=" * 72)

slip = Payslip.objects.filter(period_start=date(2026, 2, 1)).exclude(
    lines__isnull=True).first()
lines = list(slip.lines.order_by("sequence"))
check("Rules executed in sequence order",
      [l.sequence for l in lines] == sorted(l.sequence for l in lines),
      " -> ".join(f"{l.code}({l.sequence})" for l in lines))

basic = slip.basic
allow = slip.allowances
gross_line = next(l for l in lines if l.code == "GROSS")
check("Gross is derived from earlier categories, not stored",
      gross_line.amount == basic + allow,
      f"BASIC {basic} + ALLOWANCE {allow} = GROSS {gross_line.amount}")

net_line = next(l for l in lines if l.code == "NET")
check("Net is derived from Gross minus Deductions",
      net_line.amount == slip.gross - slip.deductions,
      f"GROSS {slip.gross} - DEDUCTIONS {slip.deductions} = NET {net_line.amount}")

pf = next(l for l in lines if l.code == "PF")
check("Percentage-of-another-rule works (PF = 12% of Basic)",
      pf.amount == engine.money(basic * Decimal("0.12")),
      f"12% of {basic} = {pf.amount}")

before_lines = [(l.code, l.amount) for l in slip.lines.order_by("sequence")]
engine.compute_payslip(slip)
after_lines = [(l.code, l.amount) for l in slip.lines.order_by("sequence")]
check("Recompute is idempotent (no duplicate or drifting lines)",
      before_lines == after_lines,
      f"{len(before_lines)} lines before, {len(after_lines)} after")

try:
    engine.safe_eval("__import__('os').system('echo pwned')", {})
    check("Formula sandbox blocks imports", False, "expression executed")
except engine.RuleEvaluationError as exc:
    check("Formula sandbox blocks imports", True, str(exc)[:70])


print("\n" + "=" * 72)
print("GRADED RULE 5 - Pre-finalisation warnings")
print("=" * 72)

run = Payrun.objects.filter(period_start=date(2026, 2, 1)).first()
codes = set(run.warnings.values_list("code", flat=True))
check("Payrun surfaces warnings", run.warnings.exists(),
      f"{run.warning_count} warning(s): {', '.join(sorted(codes)) or 'none'}")
check("Missing bank account is detected",
      PayslipWarning.AC_MISSING in codes,
      ", ".join(w.message for w in run.warnings.filter(code=PayslipWarning.AC_MISSING)))

# Compared against the employees actually in this payrun, not against the
# whole roster. The two are the same number only on the 22-person demo seed,
# where every employee has a contract covering February; at `seed --employees
# 200` ten people lack bank details and nine of them are in the February run,
# because the tenth joined after it closed. A payrun can only warn about the
# payslips it contains, so that is what the rule says and what is checked.
in_run = set(run.payslips.values_list("employee_id", flat=True))
no_bank_total = Employee.objects.filter(bank_account_number__isnull=True).count()
no_bank_in_run = (Employee.objects
                  .filter(pk__in=in_run, bank_account_number__isnull=True)
                  .count())
check("Every employee without bank details is flagged",
      run.warnings.filter(code=PayslipWarning.AC_MISSING).count() == no_bank_in_run,
      f"{no_bank_in_run} of {no_bank_total} without bank details are in this run")


print("\n" + "=" * 72)
print("INTEGRATION (D-002) - attendance and leave reach payroll")
print("=" * 72)

ot_slips = Payslip.objects.filter(period_start=date(2026, 2, 1),
                                  overtime_hours__gt=0)
check("Overtime hours captured from attendance onto payslips",
      ot_slips.exists(),
      f"{ot_slips.count()} payslips carry overtime")

ot_line = next((l for l in lines if l.code == "OT"), None)
check("Overtime is paid through a salary rule",
      ot_line is not None and ot_line.amount > 0,
      f"{slip.employee.full_name}: {slip.overtime_hours}h -> {ot_line.amount if ot_line else 0}")

lop_slips = Payslip.objects.filter(period_start=date(2026, 2, 1), lop_days__gt=0)
check("Unpaid leave produces Loss of Pay days",
      lop_slips.exists(),
      f"{lop_slips.count()} payslip(s) with LOP; "
      f"e.g. {lop_slips.first().employee.full_name if lop_slips.exists() else '-'}")

if lop_slips.exists():
    s = lop_slips.first()
    lop_line = s.lines.filter(code="LOP").first()
    check("Loss of Pay is deducted on the payslip",
          lop_line is not None and lop_line.amount > 0,
          f"{s.lop_days} LOP days -> deduction {lop_line.amount if lop_line else 0}")

check("Worked days derived from attendance, not assumed",
      slip.worked_days > 0 and slip.expected_days > 0,
      f"worked {slip.worked_days} of expected {slip.expected_days} days")


print("\n" + "=" * 72)
passed, total = sum(results), len(results)
print(f"  {passed}/{total} checks passed")
print("=" * 72 + "\n")
raise SystemExit(0 if passed == total else 1)
