"""Post the payload each frontend create form actually sends, and report failures.

Mirrors the shape the UI builds, not an idealised one - the point is to catch
required fields the forms forget, the way the missing company FK was caught.
Anything created is deleted again at the end.
"""

import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000"


def call(method, path, token=None, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Token " + token)
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw[:200]


status, login = call("POST", "/api/auth/login/",
                     body={"email": "admin@oxp.com", "password": "demo1234"})
token = login["token"]


def first(path, key="results"):
    _, payload = call("GET", path + "?page_size=1", token)
    rowset = payload[key] if isinstance(payload, dict) else payload
    return rowset[0] if rowset else None


company = first("/api/companies/")["id"]
employee = first("/api/employees/")["id"]
department = first("/api/departments/")["id"]
structure = first("/api/salary-structures/")["id"]
schedule = first("/api/working-schedules/")["id"]
timeoff_type = first("/api/timeoff-types/")["id"]

CASES = [
    ("employee", "/api/employees/", {
        "first_name": "Probe", "last_name": "Person",
        "work_email": "probe.person@oxp.com", "work_phone": "",
        "employee_type": "FULL_TIME", "date_of_joining": "2026-01-01",
        "department": department, "job_position": None, "manager": None,
        "work_location": None, "working_schedule": schedule,
        "bank_account_number": "", "bank_ifsc": "", "pan_number": "",
        "active": True, "company": company,
    }),
    ("contract", "/api/contracts/", {
        "employee": employee, "start_date": "2030-01-01", "end_date": None,
        "wage": "50000", "salary_structure": structure,
        "working_schedule": schedule, "department": department,
        "job_position": None, "structure_type": "Employee Salary", "state": "DRAFT",
        "notes": "",
    }),
    ("working-schedule", "/api/working-schedules/", {
        "name": "Probe Schedule", "calendar_type": "FIXED",
        "timezone": "Asia/Kolkata", "active": True, "company": company,
        "lines": [{"day_of_week": 0, "start_time": "09:00",
                   "end_time": "18:00", "break_minutes": 60}],
    }),
    ("attendance", "/api/attendance/", {
        "employee": employee, "check_in": "2030-01-01T09:00",
        "check_out": "2030-01-01T18:00", "status": "PRESENT", "notes": "",
    }),
    ("timeoff-type", "/api/timeoff-types/", {
        "name": "Probe Leave", "code": "PROBE", "unit": "DAYS",
        "requires_allocation": False, "approval": "MANAGER",
        "is_paid": True, "active": True, "description": "",
    }),
    ("allocation", "/api/allocations/", {
        "employee": employee, "time_off_type": timeoff_type,
        "name": "Probe Allocation", "allocated": "5",
        "valid_from": "2030-01-01", "valid_to": "2030-12-31",
        "state": "TO_APPROVE", "description": "",
    }),
    ("salary-rule", "/api/salary-rules/", {
        "structure": structure, "name": "Probe Rule", "code": "PROBE",
        "category": "ALLOWANCE", "sequence": 999, "computation": "FIXED",
        "amount": "100", "percentage": "0", "percentage_base": "",
        "formula": "", "condition": "", "quantity": "1",
        "appears_on_payslip": True, "is_employer_cost": False, "active": True,
    }),
    ("holiday", "/api/holidays/", {
        "name": "Probe Holiday", "date": "2030-08-15", "company": company,
    }),
    ("department", "/api/departments/", {
        "name": "Probe Dept", "active": True, "company": company,
        "manager": None,
    }),
    ("job-position", "/api/job-positions/", {
        "name": "Probe Position", "active": True, "company": company,
        "department": department,
    }),
    ("work-location", "/api/work-locations/", {
        "name": "Probe Location", "active": True, "company": company,
    }),
    ("user", "/api/users/", {
        "email": "probe.user@oxp.com", "employee": None, "role_ids": [],
        "is_active": True, "password": "demo1234",
    }),
]

created, failures = [], []

for name, path, body in CASES:
    status, payload = call("POST", path, token, body)
    if status in (200, 201):
        print("  PASS  %-18s %s" % (name, status))
        if isinstance(payload, dict) and "id" in payload:
            created.append((path, payload["id"]))
    else:
        print("  FAIL  %-18s %s  %s" % (name, status, payload))
        failures.append((name, status, payload))

print()
for path, pk in reversed(created):
    call("DELETE", "%s%s/" % (path, pk), token)
print("cleaned up %d record(s)" % len(created))

print()
print("=" * 60)
print("  %d/%d create endpoints accept the UI payload" %
      (len(CASES) - len(failures), len(CASES)))
print("=" * 60)
