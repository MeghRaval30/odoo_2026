"""
The capability matrix — one declarative home for "who may do what".

Roles are the five the problem statement names in §3, and a user may hold
**more than one**; the mockup's login note is explicit about assigning "one or
more roles". Effective permission is therefore the *union* of the capabilities
of every role held, never the highest single role — that distinction matters,
because "HR Manager + Payroll User" is a real combination a company would grant
and it has to behave as the sum of both.

Capabilities are named `resource.action[.scope]` and are the only vocabulary the
rest of the codebase should reason in. Permission classes, the navigation
manifest and the frontend all read this table, so a role change is one edit
here rather than a hunt through viewsets.

**Own-scope access is not a capability.** Every authenticated user may read
their own employee record, attendance, leave balance and payslips, and may
punch their own clock. That baseline is unconditional (the PDF grants it to the
Employee role, which every account effectively has), so it lives in `BASELINE`
and is never gated. What the matrix controls is access to *other people's*
records and to configuration.
"""

from .models import Role

# ==========================================================================
# Vocabulary
# ==========================================================================

# -- self service, granted to everyone ------------------------------------
PROFILE_READ = "profile.read"            # own employee record
PROFILE_EDIT = "profile.edit"            # own low-risk fields, directly
PROFILE_REQUEST = "profile.request"      # own sensitive fields, via approval
PASSWORD_CHANGE = "password.change"
ATTENDANCE_PUNCH = "attendance.punch"    # own check in / check out
ATTENDANCE_READ_OWN = "attendance.read.own"
TIMEOFF_REQUEST = "timeoff.request"      # raise own request
TIMEOFF_READ_OWN = "timeoff.read.own"
PAYSLIP_READ_OWN = "payslip.read.own"

# -- HR ---------------------------------------------------------------------
EMPLOYEE_READ_ALL = "employee.read.all"
EMPLOYEE_WRITE = "employee.write"
EMPLOYEE_DELETE = "employee.delete"
CONTRACT_READ_ALL = "contract.read.all"
CONTRACT_WRITE = "contract.write"
SCHEDULE_READ = "schedule.read"
SCHEDULE_WRITE = "schedule.write"
REFERENCE_WRITE = "reference.write"      # departments, positions, locations, holidays
ATTENDANCE_READ_ALL = "attendance.read.all"
ATTENDANCE_CORRECT = "attendance.correct"    # manual entry or edit for anyone
TIMEOFF_READ_ALL = "timeoff.read.all"
TIMEOFF_APPROVE = "timeoff.approve"
TIMEOFF_TYPE_WRITE = "timeoff.type.write"
ALLOCATION_READ_ALL = "allocation.read.all"
ALLOCATION_WRITE = "allocation.write"
PROFILE_APPROVE = "profile.approve"      # decide other people's change requests
DASHBOARD_HR = "dashboard.hr"

# -- payroll ----------------------------------------------------------------
PAYRUN_READ = "payrun.read"
PAYRUN_WRITE = "payrun.write"            # create / update / process
PAYRUN_DELETE = "payrun.delete"
PAYSLIP_READ_ALL = "payslip.read.all"
PAYSLIP_WRITE = "payslip.write"
PAYSLIP_DELETE = "payslip.delete"
SALARY_CONFIG_READ = "salaryconfig.read"     # structures and rules
SALARY_CONFIG_WRITE = "salaryconfig.write"
DASHBOARD_PAYROLL = "dashboard.payroll"

# -- administration ---------------------------------------------------------
USER_MANAGE = "user.manage"
SECURITY_MANAGE = "security.manage"
AUDIT_READ = "audit.read"


#: Unconditional. Not part of any role — every signed-in account has it.
BASELINE = frozenset({
    PROFILE_READ, PROFILE_EDIT, PROFILE_REQUEST, PASSWORD_CHANGE,
    ATTENDANCE_PUNCH, ATTENDANCE_READ_OWN,
    TIMEOFF_REQUEST, TIMEOFF_READ_OWN,
    PAYSLIP_READ_OWN,
})


# ==========================================================================
# The matrix
# ==========================================================================

#: "Full CRUD access to Employees, Attendance, Contracts, Working Schedules,
#: and Time Off modules. Approve or refuse Time Off Requests, with no access to
#: payroll features." — PDF §3, HR Manager. The last clause is why nothing
#: payroll-shaped appears here, dashboard included.
_HR_MANAGER = frozenset({
    EMPLOYEE_READ_ALL, EMPLOYEE_WRITE, EMPLOYEE_DELETE,
    CONTRACT_READ_ALL, CONTRACT_WRITE,
    SCHEDULE_READ, SCHEDULE_WRITE, REFERENCE_WRITE,
    ATTENDANCE_READ_ALL, ATTENDANCE_CORRECT,
    TIMEOFF_READ_ALL, TIMEOFF_APPROVE, TIMEOFF_TYPE_WRITE,
    ALLOCATION_READ_ALL, ALLOCATION_WRITE,
    PROFILE_APPROVE, DASHBOARD_HR,
})

#: "All HR Manager permissions plus Create, Read, and Update access to Payruns
#: and Payslips. Read-only access to Salary Structures and Salary Rules."
#: Note what is absent: delete. That is the whole difference from the Manager
#: row below, and it is deliberate.
_PAYROLL_USER = _HR_MANAGER | {
    PAYRUN_READ, PAYRUN_WRITE,
    PAYSLIP_READ_ALL, PAYSLIP_WRITE,
    SALARY_CONFIG_READ,
    DASHBOARD_PAYROLL,
}

#: "All HR Payroll User permissions with full CRUD access to Payruns, Payslips,
#: Salary Structures, and Salary Rules."
_PAYROLL_MANAGER = _PAYROLL_USER | {
    PAYRUN_DELETE, PAYSLIP_DELETE, SALARY_CONFIG_WRITE,
}

#: "Full access to all modules and models across the platform. User management,
#: role assignment, permission updates, and complete system administration."
_ADMIN = _PAYROLL_MANAGER | {
    USER_MANAGE, SECURITY_MANAGE, AUDIT_READ,
}

ROLE_CAPABILITIES = {
    Role.EMPLOYEE: frozenset(),          # baseline only, by design
    Role.HR_MANAGER: _HR_MANAGER,
    Role.PAYROLL_USER: frozenset(_PAYROLL_USER),
    Role.PAYROLL_MANAGER: frozenset(_PAYROLL_MANAGER),
    Role.ADMIN: frozenset(_ADMIN),
}

#: Every capability that exists. Used to validate the matrix and to render the
#: permission grid on the role screen.
ALL_CAPABILITIES = frozenset(BASELINE | _ADMIN)


def capabilities_for(role_codes) -> frozenset:
    """The union of every capability granted by the roles held, plus baseline."""
    granted = set(BASELINE)
    for code in role_codes:
        granted |= ROLE_CAPABILITIES.get(code, frozenset())
    return frozenset(granted)


# ==========================================================================
# Navigation
# ==========================================================================
#
# The top bar is built server-side, from the same table the API enforces. A menu
# the user cannot use is not rendered disabled — it is absent, which is what the
# mockup's access note asks for ("show only the modules and actions allowed by
# the user's assigned role"). Hiding a control is presentation, never
# enforcement; the permission classes do the enforcing.
#
# `cap: None` means baseline — always shown. A group with no visible children
# collapses and disappears.

NAVIGATION = [
    {
        "key": "dashboard", "label": "Dashboard", "to": "/dashboard",
        "cap": None,
    },
    {
        "key": "employees", "label": "Employees", "cap": EMPLOYEE_READ_ALL,
        "items": [
            {"to": "/employees", "label": "Employees", "cap": EMPLOYEE_READ_ALL},
            {"to": "/schedules", "label": "Working Schedules", "cap": SCHEDULE_READ},
            {"to": "/departments", "label": "Departments", "cap": EMPLOYEE_READ_ALL},
            {"to": "/job-positions", "label": "Job Positions", "cap": EMPLOYEE_READ_ALL},
            {"to": "/work-locations", "label": "Work Locations", "cap": EMPLOYEE_READ_ALL},
            {"to": "/holidays", "label": "Holidays", "cap": EMPLOYEE_READ_ALL},
        ],
    },
    {
        "key": "contracts", "label": "Contracts", "cap": CONTRACT_READ_ALL,
        "items": [
            {"to": "/contracts", "label": "Contracts", "cap": CONTRACT_READ_ALL},
            {"to": "/salary-structures", "label": "Salary Structures",
             "cap": SALARY_CONFIG_READ},
            {"to": "/salary-rules", "label": "Salary Rules",
             "cap": SALARY_CONFIG_READ},
        ],
    },
    {
        "key": "attendance", "label": "Attendance", "to": "/attendance",
        "cap": None,
    },
    {
        "key": "timeoff", "label": "Time Off", "cap": None,
        "items": [
            {"to": "/timeoff", "label": "Time Off Requests", "cap": None},
            {"to": "/allocations", "label": "Allocations", "cap": None},
            {"to": "/timeoff-types", "label": "Time Off Types",
             "cap": TIMEOFF_TYPE_WRITE},
        ],
    },
    {
        "key": "payroll", "label": "Payroll", "cap": PAYRUN_READ,
        "items": [
            {"to": "/payroll", "label": "Payruns", "cap": PAYRUN_READ},
            {"to": "/payslips", "label": "Payslips", "cap": PAYSLIP_READ_ALL},
        ],
    },
    {
        "key": "myslips", "label": "My Payslips", "to": "/my-payslips",
        "cap": None, "hide_if": PAYSLIP_READ_ALL,
    },
    {
        "key": "reports", "label": "Reports", "cap": DASHBOARD_PAYROLL,
        "items": [
            {"to": "/reports", "label": "Payroll Register", "cap": PAYRUN_READ},
        ],
    },
    {
        "key": "admin", "label": "Administration", "cap": USER_MANAGE,
        "items": [
            {"to": "/users", "label": "Users & Roles", "cap": USER_MANAGE},
            {"to": "/security", "label": "Security", "cap": SECURITY_MANAGE},
            {"to": "/audit", "label": "Audit Log", "cap": AUDIT_READ},
        ],
    },
]


def navigation_for(caps) -> list:
    """
    Prune NAVIGATION down to what `caps` can actually reach.

    `hide_if` is the inverse gate — "My Payslips" is the employee's private
    route to their own slips, and it would be noise next to the full Payslips
    list, so it disappears for anyone who has that.
    """
    def allowed(node):
        if node.get("hide_if") and node["hide_if"] in caps:
            return False
        cap = node.get("cap")
        return cap is None or cap in caps

    out = []
    for group in NAVIGATION:
        if not allowed(group):
            continue
        if "items" not in group:
            out.append({k: v for k, v in group.items() if k != "cap"})
            continue
        items = [{"to": i["to"], "label": i["label"]}
                 for i in group["items"] if allowed(i)]
        if not items:
            continue
        out.append({"key": group["key"], "label": group["label"], "items": items})
    return out


# ==========================================================================
# Which dashboard a person lands on
# ==========================================================================
#
# Five roles do not mean five equally-weighted home screens: they mean each
# person opens on the view that answers *their* first question of the day.
# Richest wins, because a user holding several roles wants the fullest picture.

DASHBOARD_ADMIN = "admin"
DASHBOARD_PAYROLL_VIEW = "payroll"
DASHBOARD_HR_VIEW = "hr"
DASHBOARD_EMPLOYEE = "employee"


def dashboard_for(caps) -> str:
    if USER_MANAGE in caps:
        return DASHBOARD_ADMIN
    if DASHBOARD_PAYROLL in caps:
        return DASHBOARD_PAYROLL_VIEW
    if DASHBOARD_HR in caps:
        return DASHBOARD_HR_VIEW
    return DASHBOARD_EMPLOYEE
