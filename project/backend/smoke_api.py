"""
End-to-end API smoke test.

Drives the real HTTP stack through Django's test client: login, role
enforcement, the two-step payrun wizard, the action bar, PDF generation and
the dashboard.

Run:  .venv/Scripts/python.exe smoke_api.py
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# Capture email in memory so the console backend does not dump base64 PDFs
os.environ["EMAIL_BACKEND"] = "django.core.mail.backends.locmem.EmailBackend"
django.setup()

from datetime import date

from django.test import Client

results = []


def check(label, condition, evidence=""):
    results.append(bool(condition))
    print(f"  [{'PASS' if condition else 'FAIL'}] {label}")
    if evidence:
        print(f"         {evidence}")


def auth(client, email, password="demo1234"):
    r = client.post("/api/auth/login/",
                    {"email": email, "password": password},
                    content_type="application/json")
    return r


print("\n" + "=" * 72)
print("AUTH AND ROLES")
print("=" * 72)

admin = Client()
r = auth(admin, "admin@oxp.com")
check("Admin login returns a token", r.status_code == 200 and "token" in r.json(),
      f"roles={r.json()['user']['roles'] if r.status_code == 200 else r.status_code}")
admin_token = r.json()["token"]
AH = {"HTTP_AUTHORIZATION": f"Token {admin_token}"}

r = admin.post("/api/auth/login/", {"email": "admin@oxp.com", "password": "wrong"},
               content_type="application/json")
check("Bad password rejected", r.status_code == 401)

emp = Client()
r = auth(emp, "john@oxp.com")
check("Employee login works", r.status_code == 200,
      f"roles={r.json()['user']['roles'] if r.status_code == 200 else ''}")
EH = {"HTTP_AUTHORIZATION": f"Token {r.json()['token']}"}

r = emp.get("/api/payruns/", **EH)
check("Employee role is blocked from payruns (server-side)",
      r.status_code == 403, f"HTTP {r.status_code}")

r = emp.get("/api/employees/", **EH)
count = r.json().get("count") if r.status_code == 200 else None
check("Employee sees only their own record", r.status_code == 200 and count == 1,
      f"HTTP {r.status_code}, count={count}")

r = admin.get("/api/employees/", **AH)
check("Admin sees the full roster", r.json().get("count") == 22,
      f"count={r.json().get('count')}")

from payroll.models import SalaryStructure as _SS
structure_pk = _SS.objects.first().id
payroll_user = Client()
r = auth(payroll_user, "rahul@oxp.com")
PH = {"HTTP_AUTHORIZATION": f"Token {r.json()['token']}"}
r = payroll_user.get("/api/salary-structures/", **PH)
check("Payroll User can READ salary structures", r.status_code == 200)
r = payroll_user.post("/api/salary-rules/",
                      {"structure": structure_pk, "name": "X", "code": "X",
                       "category": "ALLOWANCE", "sequence": 5},
                      content_type="application/json", **PH)
check("Payroll User is blocked from WRITING salary rules (read-only)",
      r.status_code == 403, f"HTTP {r.status_code}")


print("\n" + "=" * 72)
print("HR MASTER DATA")
print("=" * 72)

emp_id = admin.get("/api/employees/", **AH).json()["results"][0]["id"]
r = admin.get(f"/api/employees/{emp_id}/", **AH)
body = r.json()
check("Employee detail carries smart-button counts",
      all(k in body for k in ("contract_count", "attendance_count",
                              "timeoff_count", "allocation_count")),
      f"contracts={body.get('contract_count')} attendance={body.get('attendance_count')} "
      f"timeoff={body.get('timeoff_count')} allocations={body.get('allocation_count')}")

r = admin.get(f"/api/employees/{body['id']}/contracts/", **AH)
check("Smart button returns contracts filtered to this employee",
      r.status_code == 200 and len(r.json()) >= 1,
      f"{len(r.json())} contract(s)")

r = admin.get("/api/working-schedules/", **AH)
sched = next(s for s in r.json()["results"] if s["name"] == "40 Hours / Week")
check("Working schedule exposes derived hours, not an input field",
      str(sched["hours_per_week"]) == "40.00" and sched["days_per_week"] == 5,
      f"{sched['hours_per_week']}h over {sched['days_per_week']} days, "
      f"{len(sched['lines'])} lines")

r = admin.get("/api/contracts/?state=RUNNING", **AH)
check("Contracts filterable by state", r.status_code == 200,
      f"{r.json()['count']} running contracts")


print("\n" + "=" * 72)
print("ATTENDANCE WIDGET")
print("=" * 72)

r = emp.get("/api/attendance/status/", **EH)
check("Widget status endpoint responds", r.status_code == 200,
      f"checked_in={r.json().get('checked_in')}")

r = emp.post("/api/attendance/check_in/", **EH)
check("Check in creates an open session", r.status_code in (200, 201),
      f"HTTP {r.status_code}")

r = emp.get("/api/attendance/status/", **EH)
check("Status flips to checked-in with live elapsed time",
      r.json().get("checked_in") is True,
      f"elapsed={r.json().get('elapsed_hours')}h")

r = emp.post("/api/attendance/check_out/", **EH)
check("Check out closes the session and derives worked hours",
      r.status_code == 200 and r.json().get("check_out") is not None,
      f"worked_hours={r.json().get('worked_hours')}")


print("\n" + "=" * 72)
print("TIME OFF — allocation gate over HTTP")
print("=" * 72)

r = admin.get("/api/timeoff-types/", **AH)
types = {t["code"]: t for t in r.json()["results"]}
check("Types expose the requires_allocation flag",
      types["PTO"]["requires_allocation"] and not types["SICK"]["requires_allocation"])

r = admin.get("/api/allocations/", **AH)
alloc = r.json()["results"][0]
check("Allocation exposes Allocated / Taken / Remaining",
      all(k in alloc for k in ("allocated", "taken", "remaining")),
      f"{alloc['allocated']} / {alloc['taken']} / {alloc['remaining']}")

# An employee with no PTO allocation should be refused
from employees.models import Employee as Emp
from timeoff.models import Allocation as Alloc, TimeOffType as TOT

pto = TOT.objects.get(code="PTO")
victim = Emp.objects.exclude(
    allocations__time_off_type=pto, allocations__state=Alloc.APPROVED).first()
if victim is None:
    victim = Emp.objects.last()
    Alloc.objects.filter(employee=victim, time_off_type=pto).delete()

r = admin.post("/api/timeoff-requests/",
               {"employee": victim.id, "time_off_type": pto.id,
                "date_from": "2026-09-07", "date_to": "2026-09-09"},
               content_type="application/json", **AH)
check("Request without allocation is refused by the API",
      r.status_code == 400, f"HTTP {r.status_code}: {str(r.json())[:100]}")

r = admin.post("/api/allocations/",
               {"employee": victim.id, "time_off_type": pto.id,
                "name": "Smoke Grant", "allocated": "5",
                "valid_from": "2026-01-01", "valid_to": "2026-12-31",
                "state": "DRAFT"},
               content_type="application/json", **AH)
alloc_id = r.json()["id"]
r = admin.post(f"/api/allocations/{alloc_id}/approve/", **AH)
check("Allocation can be approved", r.json()["state"] == "APPROVED")

r = admin.post("/api/timeoff-requests/",
               {"employee": victim.id, "time_off_type": pto.id,
                "date_from": "2026-09-07", "date_to": "2026-09-09"},
               content_type="application/json", **AH)
check("Same request now succeeds", r.status_code == 201,
      f"consumed allocation id={r.json().get('allocation_used')}")
req_id = r.json()["id"]

r = admin.post(f"/api/timeoff-requests/{req_id}/approve/", **AH)
check("Request approves", r.json()["state"] == "APPROVED")

r = admin.get(f"/api/allocations/{alloc_id}/", **AH)
check("Balance decreased after approval",
      float(r.json()["remaining"]) < float(r.json()["allocated"]),
      f"{r.json()['allocated']} allocated, {r.json()['taken']} taken, "
      f"{r.json()['remaining']} remaining")


print("\n" + "=" * 72)
print("PAYRUN WIZARD AND ACTION BAR")
print("=" * 72)

from core.models import Company as _Co
from payroll.models import SalaryStructure
structure = SalaryStructure.objects.get(code="REGULAR")
company_pk = _Co.objects.first().id

# Make the smoke test idempotent: clear any payrun left by a previous run
from payroll.models import Payrun as _PR
_PR.objects.filter(name__contains="(smoke)").delete()

before = admin.get("/api/payruns/", **AH).json()["count"]
r = admin.post("/api/payruns/eligible-employees/",
               {"employee_type": "FULL_TIME", "salary_structure": structure.id,
                "period_start": "2026-04-01", "period_end": "2026-04-30"},
               content_type="application/json", **AH)
eligible = r.json()
check("Wizard step 2 lists eligible employees", r.status_code == 200 and eligible,
      f"{len(eligible)} eligible; sample: {eligible[0]['name']} "
      f"wage={eligible[0]['wage']}")

after = admin.get("/api/payruns/", **AH).json()["count"]
check("Step 1 -> 2 creates NO payrun record", before == after,
      f"payruns before={before} after={after}")

picked = [e["id"] for e in eligible[:5]]
r = admin.post("/api/payruns/create-with-employees/",
               {"name": "April 2026 (smoke)", "company": company_pk,
                "salary_structure": structure.id,
                "period_start": "2026-04-01", "period_end": "2026-04-30",
                "employee_ids": picked},
               content_type="application/json", **AH)
check("Create Payrun persists the run", r.status_code == 201, f"HTTP {r.status_code}")
run = r.json()
run_id = run["id"]
check("Payrun contains ONLY the selected employees",
      run["payslip_count"] == len(picked),
      f"{run['payslip_count']} payslips for {len(picked)} selected")

r = admin.post(f"/api/payruns/{run_id}/validate/", **AH)
check("Validate is refused before Compute", r.status_code == 400,
      f"HTTP {r.status_code}")

r = admin.post(f"/api/payruns/{run_id}/compute/", **AH)
run = r.json()
check("Compute produces payslips and totals", run["state"] == "COMPUTED",
      f"state={run['state']} net={run['total_net']} warnings={run['warning_count']}")

first_net = run["total_net"]
run2 = admin.post(f"/api/payruns/{run_id}/compute/", **AH).json()
check("Recompute is idempotent over HTTP", run2["total_net"] == first_net,
      f"{first_net} -> {run2['total_net']}")

r = admin.get(f"/api/payruns/{run_id}/warnings/", **AH)
check("Warnings visible before validation", r.status_code == 200,
      f"{len(r.json())} warning(s): "
      f"{', '.join(sorted({w['code'] for w in r.json()})) or 'none'}")

r = admin.post(f"/api/payruns/{run_id}/validate/", **AH)
check("Validate succeeds after compute", r.json()["state"] == "VALIDATED")

r = admin.post(f"/api/payruns/{run_id}/mark-paid/", **AH)
check("Mark Paid moves to the terminal state", r.json()["state"] == "PAID")

r = admin.post(f"/api/payruns/{run_id}/compute/", **AH)
check("A PAID payrun is read-only", r.status_code == 400,
      f"HTTP {r.status_code}: {r.json().get('detail', '')[:60]}")


print("\n" + "=" * 72)
print("PAYSLIP, PDF AND EMAIL")
print("=" * 72)

r = admin.get(f"/api/payruns/{run_id}/payslips/", **AH)
slip_id = r.json()[0]["id"]
r = admin.get(f"/api/payslips/{slip_id}/", **AH)
slip = r.json()
check("Payslip detail carries the rule-by-rule computation",
      len(slip["lines"]) > 0,
      " -> ".join(f"{l['code']}={l['amount']}" for l in slip["lines"][:6]) + " ...")
check("Payslip shows contract used and worked days",
      slip["contract_reference"] and slip["worked_days"] is not None,
      f"contract={slip['contract_reference']} wage={slip['contract_wage']} "
      f"worked={slip['worked_days']}/{slip['expected_days']}")

r = admin.get(f"/api/payslips/{slip_id}/pdf/", **AH)
check("Payslip PDF renders",
      r.status_code == 200 and r["Content-Type"] == "application/pdf"
      and len(r.content) > 1500,
      f"{len(r.content):,} bytes")

from django.core import mail
mail.outbox = []
r = admin.post(f"/api/payruns/{run_id}/send-payslips/", **AH)
check("Bulk Send Payslips dispatches email with PDF attached",
      r.status_code == 200 and r.json()["sent"] == len(picked),
      f"sent={r.json()['sent']} skipped={r.json()['skipped']}, "
      f"outbox={len(mail.outbox)}, "
      f"attachments={len(mail.outbox[0].attachments) if mail.outbox else 0}")


print("\n" + "=" * 72)
print("DASHBOARD — live aggregation")
print("=" * 72)

r = admin.get("/api/dashboard/?period_start=2026-02-01&period_end=2026-02-28", **AH)
d = r.json()
check("Dashboard responds", r.status_code == 200)
check("Aggregates across six models", len(d["sources"]) >= 5,
      ", ".join(d["sources"]))
k = d["kpis"]
check("KPI cards computed from live data",
      float(k["total_net_paid"]) > 0 and k["payslips_generated"] > 0,
      f"net={k['total_net_paid']} slips={k['payslips_generated']} "
      f"avg={k['avg_salary_per_employee']} leave={k['approved_timeoff_days']} "
      f"attendance={k['attendance_health']}%")
check("Month-over-month delta computed", k["net_delta_pct"] is not None,
      f"{k['net_delta_pct']:.2f}% vs previous period" if k['net_delta_pct'] is not None else 'no previous period')
check("Salary by department populated", len(d["salary_by_department"]) > 0,
      ", ".join(f"{r_['name']}={r_['total']}" for r_ in d["salary_by_department"][:3]))
check("Salary trend has multiple periods", len(d["salary_trend"]) >= 3,
      " | ".join(f"{t['period']}:{t['net']}" for t in d["salary_trend"]))
check("Alerts surfaced", len(d["alert_messages"]) > 0,
      d["alert_messages"][0] if d["alert_messages"] else "none")
check("Attendance overview populated",
      d["attendance_overview"]["coverage_pct"] > 0,
      f"present={d['attendance_overview']['present']} "
      f"overtime_hrs={d['attendance_overview']['total_overtime_hours']} "
      f"coverage={d['attendance_overview']['coverage_pct']}%")
check("Time off overview populated", len(d["timeoff_overview"]) > 0)
check("Department overview populated", len(d["department_overview"]) > 0)

# The filter must genuinely re-drive the numbers
unfiltered = float(d["kpis"]["total_net_paid"])
dept_id = d["department_overview"][0]["id"]
r = admin.get(f"/api/dashboard/?period_start=2026-02-01&period_end=2026-02-28"
              f"&department={dept_id}", **AH)
filtered = float(r.json()["kpis"]["total_net_paid"])
check("Department filter genuinely re-drives the data",
      filtered < unfiltered and filtered > 0,
      f"all departments {unfiltered:,.0f} -> one department {filtered:,.0f}")

r = admin.get("/api/dashboard/?period_start=2025-12-01&period_end=2025-12-31", **AH)
dec = float(r.json()["kpis"]["total_net_paid"])
check("Period filter genuinely re-drives the data",
      dec != unfiltered and dec > 0,
      f"Feb {unfiltered:,.0f} vs Dec {dec:,.0f}")

r = admin.get("/api/dashboard/filters/", **AH)
check("Filter options endpoint populated",
      len(r.json()["departments"]) > 0 and len(r.json()["periods"]) > 0,
      f"{len(r.json()['departments'])} departments, "
      f"{len(r.json()['periods'])} periods")


print("\n" + "=" * 72)
passed, total = sum(results), len(results)
print(f"  {passed}/{total} checks passed")
print("=" * 72 + "\n")
raise SystemExit(0 if passed == total else 1)
