"""
Audit every role against the PRD 3.2 permission matrix.

Drives the real HTTP stack with Django's test client and reports each cell as
OK or as a LEAK (allowed when it should not be) / BLOCK (denied when it should
be allowed). Exit code is non-zero if any cell disagrees with the matrix.

Run:  .venv/Scripts/python.exe audit_permissions.py
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client  # noqa: E402

ACCOUNTS = {
    "Employee": "john@oxp.com",
    "HR Manager": "sara@oxp.com",
    "Payroll User": "rahul@oxp.com",
    "Payroll Manager": "aarav@oxp.com",
    "Admin": "admin@oxp.com",
}

# PRD 3.2. Values: "none" | "read" | "write"  (write implies read).
#
# BOTH PAYROLL COLUMNS ARE DELIBERATELY NARROWER THAN THE PRD.
#
# The PRD stacks the roles into a ladder, each a superset of the last, which
# ends with the person who signs the payrun also owning every input to it.
# Here the HR Manager and the Payroll Manager are siblings: HR owns people
# (hiring, leave decisions, attendance corrections, HR configuration),
# payroll owns payroll (contracts and wages, salary rules, payruns). Only
# the Admin holds both sides.
# The matrix grants that role "all HR Manager permissions plus CRU on
# Payruns and Payslips", which puts every input to a payslip and the
# payslip itself under one login: raise the wage, approve the leave,
# correct the attendance, compute the run, mark it paid. This build
# separates deciding pay from processing pay, so the role reads all of
# it and writes almost none of it. SEPARATION OF DUTIES below pins the
# specific refusals; accounts/capabilities.py carries the reasoning.
#
# Two rows deliberately read wider than a literal reading of the matrix, and
# both are recorded as decisions:
#
#   attendance / timeoff-requests for Employee are "CR (own)" in the PRD, not
#   plain R — an employee creates their own attendance and their own leave
#   requests. Row scoping is enforced in the viewsets.
#
#   timeoff-types is "-" for Employee in the matrix, but the self-service leave
#   form has to render a type dropdown, so the catalogue is readable. The row
#   means no management rights, not that the list is invisible.
#
#   payslips is "-" for HR Manager in the matrix; in practice an HR Manager is
#   also an employee and may read their own. The row means no access to other
#   people's payslips.
MATRIX = {
    "employees":          {"Employee": "read", "HR Manager": "write", "Payroll User": "read",  "Payroll Manager": "read",  "Admin": "write"},
    "contracts":          {"Employee": "read", "HR Manager": "write", "Payroll User": "read",  "Payroll Manager": "read",  "Admin": "write"},
    "working-schedules":  {"Employee": "read", "HR Manager": "write", "Payroll User": "read",  "Payroll Manager": "read",  "Admin": "write"},
    "attendance":         {"Employee": "write", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "timeoff-requests":   {"Employee": "write", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "allocations":        {"Employee": "read", "HR Manager": "write", "Payroll User": "read",  "Payroll Manager": "read",  "Admin": "write"},
    "timeoff-types":      {"Employee": "read", "HR Manager": "write", "Payroll User": "read",  "Payroll Manager": "read",  "Admin": "write"},
    "payruns":            {"Employee": "none", "HR Manager": "none",  "Payroll User": "read",  "Payroll Manager": "write", "Admin": "write"},
    "payslips":           {"Employee": "read", "HR Manager": "read",  "Payroll User": "read",  "Payroll Manager": "read",  "Admin": "read"},
    "salary-structures":  {"Employee": "none", "HR Manager": "none",  "Payroll User": "none",  "Payroll Manager": "read",  "Admin": "write"},
    "salary-rules":       {"Employee": "none", "HR Manager": "none",  "Payroll User": "none",  "Payroll Manager": "read",  "Admin": "write"},
    "users":              {"Employee": "none", "HR Manager": "none",  "Payroll User": "none",  "Payroll Manager": "none",  "Admin": "write"},
}

#: Rows a role may only ever see for itself. Checked separately from the
#: allow/deny matrix, because a 200 that returns everyone else's records is a
#: worse leak than a missing 403.
OWN_ROWS_ONLY = {
    "Employee": ["employees", "contracts", "attendance", "timeoff-requests",
                 "allocations", "payslips"],
}

#: A minimal creatable body per resource, used only to probe write access.
#: The body may be invalid — a 400 still proves the request got past permissions.
WRITE_PROBE = {
    "employees": {"first_name": "Perm", "last_name": "Probe"},
    "contracts": {"wage": "1.00"},
    "working-schedules": {"name": "Perm Probe"},
    "attendance": {"check_in": "2026-05-01T09:00:00Z"},
    "timeoff-requests": {"date_from": "2026-05-01", "date_to": "2026-05-01"},
    "allocations": {"name": "Perm Probe", "allocated": "1"},
    "timeoff-types": {"name": "Perm Probe", "code": "PERMPROBE"},
    "payruns": {"name": "Perm Probe"},
    "payslips": {},
    "salary-structures": {"name": "Perm Probe", "code": "PERMPROBE"},
    "salary-rules": {"name": "Perm Probe", "code": "PERMPROBE"},
    "users": {"email": "perm.probe@oxp.com"},
}

DENIED = (401, 403, 404, 405)


def cleanup():
    """
    Remove whatever the write probes actually managed to create.

    Most of the payloads above are deliberately incomplete and are rejected at
    validation, which is all the audit needs -- a 400 proves permission passed.
    A few are complete enough to succeed, and the users one always does, so a
    run left a `perm.probe@oxp.com` account sitting in User Management. Every
    probe carries the same marker so the sweep can be exact.

    probe_forms.py already tidies up after itself; this brings the permission
    audit in line, so running the harnesses before a demo cannot dirty it.
    """
    from accounts.models import User
    from employees.models import Employee, WorkingSchedule
    from payroll.models import Payrun, SalaryRule, SalaryStructure
    from timeoff.models import Allocation, TimeOffType

    removed = 0
    for queryset in (
        User.objects.filter(email__startswith="perm.probe"),
        Employee.objects.filter(first_name="Perm", last_name="Probe"),
        Allocation.objects.filter(name="Perm Probe"),
        Payrun.objects.filter(name="Perm Probe"),
        WorkingSchedule.objects.filter(name="Perm Probe"),
        TimeOffType.objects.filter(code="PERMPROBE"),
        SalaryRule.objects.filter(code="PERMPROBE"),
        SalaryStructure.objects.filter(code="PERMPROBE"),
    ):
        count = queryset.count()
        if count:
            queryset.delete()
            removed += count
    return removed


def token_for(email):
    c = Client()
    r = c.post("/api/auth/login/", {"email": email, "password": "demo1234"},
               content_type="application/json")
    assert r.status_code == 200, f"login failed for {email}: {r.status_code}"
    return c, {"HTTP_AUTHORIZATION": f"Token {r.json()['token']}"}


def probe(client, headers, resource):
    """Return (can_read, can_write) as the server actually behaves."""
    r = client.get(f"/api/{resource}/", **headers)
    can_read = r.status_code == 200

    body = WRITE_PROBE.get(resource, {})
    w = client.post(f"/api/{resource}/", body,
                    content_type="application/json", **headers)
    # 400 means the payload was rejected *after* permission passed — still write access.
    can_write = w.status_code not in DENIED
    return can_read, can_write, r.status_code, w.status_code


def main():
    problems = []
    print("\n" + "=" * 78)
    print("PERMISSION AUDIT — PRD 3.2")
    print("=" * 78)

    sessions = {role: token_for(email) for role, email in ACCOUNTS.items()}

    for resource, expected_by_role in MATRIX.items():
        print(f"\n{resource}")
        for role, expected in expected_by_role.items():
            client, headers = sessions[role]
            can_read, can_write, rc, wc = probe(client, headers, resource)

            want_read = expected in ("read", "write")
            want_write = expected == "write"

            issues = []
            if can_read and not want_read:
                issues.append(f"LEAK read (GET {rc})")
            if not can_read and want_read:
                issues.append(f"BLOCKED read (GET {rc})")
            if can_write and not want_write:
                issues.append(f"LEAK write (POST {wc})")
            if not can_write and want_write:
                issues.append(f"BLOCKED write (POST {wc})")

            verdict = "OK" if not issues else " | ".join(issues)
            flag = " " if not issues else "!"
            print(f"  {flag} {role:<17} want={expected:<5} "
                  f"got read={'Y' if can_read else 'n'} write={'Y' if can_write else 'n'}"
                  f"   {verdict}")
            if issues:
                problems.append((resource, role, verdict))

    # ---- separation of duties -------------------------------------------
    #
    # The matrix above is coarse: one POST per resource. These are the exact
    # refusals the Payroll User restriction exists for, plus the reads that
    # must survive it -- a role that cannot also read the run it is checking
    # would be useless, and quietly over-tightening is its own kind of bug.
    #
    # Detail routes use an id that does not exist on purpose. DRF checks
    # has_permission before it looks the object up, so a denied call answers
    # 403 and an allowed one answers 404 -- the distinction is visible without
    # mutating a single row.
    # On a detail route with a deliberately missing id, only 401/403 is a
    # refusal -- 404 means the permission check passed and the object was
    # simply not there, which is the whole point of using that id.
    REFUSED = (401, 403)

    print("")
    print("SEPARATION OF DUTIES  (HR Payroll User)")
    client, headers = sessions["Payroll User"]
    GONE = 999999

    must_refuse = [
        ("set a wage",           "PATCH",  f"/api/contracts/{GONE}/"),
        ("correct attendance",   "PATCH",  f"/api/attendance/{GONE}/"),
        ("approve leave",        "POST",   f"/api/timeoff-requests/{GONE}/approve/"),
        ("delete an employee",   "DELETE", f"/api/employees/{GONE}/"),
        ("create a payrun",      "POST",   "/api/payruns/create-with-employees/"),
        ("compute a payrun",     "POST",   f"/api/payruns/{GONE}/compute/"),
        ("validate a payrun",    "POST",   f"/api/payruns/{GONE}/validate/"),
        ("mark a payrun paid",   "POST",   f"/api/payruns/{GONE}/mark-paid/"),
        ("send payslips",        "POST",   f"/api/payruns/{GONE}/send-payslips/"),
        ("edit a salary rule",   "POST",   "/api/salary-rules/"),
        ("edit a leave type",    "POST",   "/api/timeoff-types/"),
        ("edit a schedule",      "POST",   "/api/working-schedules/"),
        ("add an employee",      "POST",   "/api/employees/"),
        ("edit an employee",     "PATCH",  f"/api/employees/{GONE}/"),
        ("grant leave balance",  "POST",   "/api/allocations/"),
        ("edit a department",    "POST",   "/api/departments/"),
    ]
    for label, method, path in must_refuse:
        r = client.generic(method, path, "{}",
                           content_type="application/json", **headers)
        ok = r.status_code in REFUSED
        print(f"  {' ' if ok else '!'} refuses to {label:<20} "
              f"{method:<6} {r.status_code}   {'OK' if ok else 'LEAK'}")
        if not ok:
            problems.append(("separation of duties", label,
                             f"ALLOWED ({method} {r.status_code})"))

    must_allow = [
        ("read payruns",         "/api/payruns/"),
        ("read every payslip",   "/api/payslips/"),
        ("read contracts",       "/api/contracts/"),
        ("read attendance",      "/api/attendance/"),
        ("read leave requests",  "/api/timeoff-requests/"),
        ("read the dashboard",   "/api/dashboard/"),
    ]
    for label, path in must_allow:
        r = client.get(path, **headers)
        ok = r.status_code == 200
        print(f"  {' ' if ok else '!'} can still {label:<23} "
              f"GET    {r.status_code}   {'OK' if ok else 'OVER-TIGHTENED'}")
        if not ok:
            problems.append(("separation of duties", label,
                             f"BLOCKED (GET {r.status_code})"))

    # ---- separation of duties, the manager rank ---------------------------
    #
    # The Payroll Manager runs payroll and must not own its inputs. Both lists
    # matter equally: the refusals prove the separation, the allowances prove
    # we separated the role rather than crippling it.
    print("")
    print("SEPARATION OF DUTIES  (HR Payroll Manager)")
    client, headers = sessions["Payroll Manager"]

    manager_must_refuse = [
        ("set a wage",           "PATCH",  f"/api/contracts/{GONE}/"),
        ("add an employee",      "POST",   "/api/employees/"),
        ("edit an employee",     "PATCH",  f"/api/employees/{GONE}/"),
        ("approve leave",        "POST",   f"/api/timeoff-requests/{GONE}/approve/"),
        ("correct attendance",   "PATCH",  f"/api/attendance/{GONE}/"),
        ("delete an employee",   "DELETE", f"/api/employees/{GONE}/"),
        ("edit a leave type",    "POST",   "/api/timeoff-types/"),
        ("edit a schedule",      "POST",   "/api/working-schedules/"),
        ("edit a department",    "POST",   "/api/departments/"),
        ("edit a holiday",       "POST",   "/api/holidays/"),
        ("write a salary rule",  "POST",   "/api/salary-rules/"),
        ("grant leave balance",  "POST",   "/api/allocations/"),
    ]
    for label, method, path in manager_must_refuse:
        r = client.generic(method, path, "{}",
                           content_type="application/json", **headers)
        ok = r.status_code in REFUSED
        print(f"  {' ' if ok else '!'} refuses to {label:<20} "
              f"{method:<6} {r.status_code}   {'OK' if ok else 'LEAK'}")
        if not ok:
            problems.append(("separation of duties (mgr)", label,
                             f"ALLOWED ({method} {r.status_code})"))

    # Payroll itself must be entirely intact. Detail routes use the missing id
    # again, so an allowed call answers 404 and nothing is actually run.
    manager_must_allow = [
        ("create a payrun",      "POST",   "/api/payruns/create-with-employees/"),
        ("compute a payrun",     "POST",   f"/api/payruns/{GONE}/compute/"),
        ("validate a payrun",    "POST",   f"/api/payruns/{GONE}/validate/"),
        ("mark a payrun paid",   "POST",   f"/api/payruns/{GONE}/mark-paid/"),
        ("delete a payrun",      "DELETE", f"/api/payruns/{GONE}/"),
        ("read the salary rules","GET",    "/api/salary-rules/"),
        ("read every contract",  "GET",    "/api/contracts/"),
        ("read every employee",  "GET",    "/api/employees/"),
        ("read all attendance",  "GET",    "/api/attendance/"),
    ]
    for label, method, path in manager_must_allow:
        r = client.generic(method, path, "{}",
                           content_type="application/json", **headers)
        ok = r.status_code not in REFUSED
        print(f"  {' ' if ok else '!'} may still {label:<21} "
              f"{method:<6} {r.status_code}   {'OK' if ok else 'OVER-TIGHTENED'}")
        if not ok:
            problems.append(("separation of duties (mgr)", label,
                             f"BLOCKED ({method} {r.status_code})"))

    # ---- the two payroll ranks agree about people -------------------------
    #
    # Employees, contracts and attendance are HR's to change. Both payroll
    # ranks read them and neither writes them, so on these three resources the
    # Manager must be indistinguishable from the User. Asserted as an identity
    # rather than cell by cell, because the point is the sameness.
    print("")
    print("PAYROLL RANKS AGREE ON PEOPLE DATA  (employees, contracts, attendance)")
    user_client, user_headers = sessions["Payroll User"]
    mgr_client, mgr_headers = sessions["Payroll Manager"]
    for resource in ("employees", "contracts", "attendance"):
        for method, body in (("GET", None), ("POST", "{}"),
                             ("PATCH", "{}"), ("DELETE", None)):
            path = f"/api/{resource}/"
            if method in ("PATCH", "DELETE"):
                path = f"/api/{resource}/{GONE}/"
            a = user_client.generic(method, path, body or "",
                                    content_type="application/json",
                                    **user_headers)
            b = mgr_client.generic(method, path, body or "",
                                   content_type="application/json",
                                   **mgr_headers)
            same = (a.status_code in REFUSED) == (b.status_code in REFUSED)
            print(f"  {' ' if same else '!'} {resource:<12} {method:<6} "
                  f"user={a.status_code} manager={b.status_code}   "
                  f"{'SAME' if same else 'DIVERGED'}")
            if not same:
                problems.append((resource, "payroll ranks",
                                 f"{method} user={a.status_code} "
                                 f"manager={b.status_code}"))

    # ---- read breadth: read-only must not mean blind ----------------------
    #
    # The queryset scoping used to ask "can this account manage HR?", which is
    # a write question. Making the Payroll User read-only would then have
    # narrowed it to its own rows and left it unable to check anything. The
    # scoping now asks a read question, and this is what pins that: the role
    # writes nothing and still sees the whole organisation.
    print("")
    print("READ BREADTH  (HR Payroll User sees everyone, not just itself)")
    admin_client, admin_headers = sessions["Admin"]
    client, headers = sessions["Payroll User"]
    for resource in ("employees", "contracts", "attendance",
                     "timeoff-requests", "allocations", "payslips"):
        everyone = admin_client.get(f"/api/{resource}/?page_size=500",
                                    **admin_headers)
        theirs = client.get(f"/api/{resource}/?page_size=500", **headers)
        if everyone.status_code != 200 or theirs.status_code != 200:
            print(f"  ! {resource:<18} GET {theirs.status_code} (cannot check)")
            continue
        total = everyone.json().get("count")
        seen = theirs.json().get("count")
        ok = total is not None and seen == total
        print(f"  {' ' if ok else '!'} {resource:<18} sees {seen} of {total}"
              f"   {'OK' if ok else 'NARROWED'}")
        if not ok:
            problems.append((resource, "Payroll User",
                             f"NARROWED to {seen} of {total}"))

    # ---- row scoping: a 200 must not hand back other people's records ----
    print("\nROW SCOPING")
    for role, resources in OWN_ROWS_ONLY.items():
        client, headers = sessions[role]
        me = client.get("/api/auth/me/", **headers).json()
        emp_id = me.get("employee_id")
        for resource in resources:
            r = client.get(f"/api/{resource}/?page_size=200", **headers)
            if r.status_code != 200:
                print(f"  ! {role:<12} {resource:<18} GET {r.status_code} (cannot check)")
                continue
            rows = r.json().get("results", r.json())
            foreign = [x for x in rows
                       if isinstance(x, dict)
                       and x.get("employee") not in (None, emp_id)]
            if resource == "employees":
                foreign = [x for x in rows if x.get("id") != emp_id]
            if foreign:
                msg = f"LEAK {len(foreign)} row(s) belonging to others"
                print(f"  ! {role:<12} {resource:<18} {msg}")
                problems.append((resource, role, msg))
            else:
                print(f"    {role:<12} {resource:<18} {len(rows)} row(s), all own  OK")

    removed = cleanup()
    print("")
    print(f"cleaned up {removed} probe record(s)")

    print("\n" + "=" * 78)
    if problems:
        print(f"  {len(problems)} DISAGREEMENT(S) WITH THE MATRIX")
        for res, role, v in problems:
            print(f"    {res:<20} {role:<17} {v}")
    else:
        print("  every cell matches the intended matrix")
    print("=" * 78 + "\n")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
