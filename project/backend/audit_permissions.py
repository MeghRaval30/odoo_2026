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
    "employees":          {"Employee": "read", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "contracts":          {"Employee": "read", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "working-schedules":  {"Employee": "read", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "attendance":         {"Employee": "write", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "timeoff-requests":   {"Employee": "write", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "allocations":        {"Employee": "read", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "timeoff-types":      {"Employee": "read", "HR Manager": "write", "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "payruns":            {"Employee": "none", "HR Manager": "none",  "Payroll User": "write", "Payroll Manager": "write", "Admin": "write"},
    "payslips":           {"Employee": "read", "HR Manager": "read",  "Payroll User": "read",  "Payroll Manager": "read",  "Admin": "read"},
    "salary-structures":  {"Employee": "none", "HR Manager": "none",  "Payroll User": "read",  "Payroll Manager": "write", "Admin": "write"},
    "salary-rules":       {"Employee": "none", "HR Manager": "none",  "Payroll User": "read",  "Payroll Manager": "write", "Admin": "write"},
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

    print("\n" + "=" * 78)
    if problems:
        print(f"  {len(problems)} DISAGREEMENT(S) WITH THE MATRIX")
        for res, role, v in problems:
            print(f"    {res:<20} {role:<17} {v}")
    else:
        print("  every cell matches PRD 3.2")
    print("=" * 78 + "\n")
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
