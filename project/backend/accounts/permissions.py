"""
Role-based permission classes.

Enforced server-side — hiding a button is not enforcement (PRD-3.1).
The matrix these implement is in claude/context/prd.md §3.2.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.is_admin)


class CanManageHR(BasePermission):
    """HR Manager and above may write; everyone authenticated may read."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return user.can_manage_hr


class CanRunPayroll(BasePermission):
    """
    Payrun and payslip access — Payroll User and above.

    Delete is what separates the two payroll rows of the matrix: an HR Payroll
    User has "Create / Read / Update", an HR Payroll Manager has "Full CRUD"
    (PRD §3.2). Collapsing every unsafe method into a single can_run_payroll
    check erased that distinction, so DELETE is tested on its own.

    `can_configure_payroll` is named for structures and rules, but it resolves
    to exactly the set this needs — Payroll Manager or Admin.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return user.can_run_payroll or user.is_admin
        if request.method == "DELETE":
            return user.can_configure_payroll
        return user.can_run_payroll


class CanConfigurePayroll(BasePermission):
    """
    Salary structures and rules.

    Payroll User gets read-only here; only Payroll Manager and Admin may
    write. This distinction is explicit in the problem statement.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return user.can_run_payroll or user.is_admin
        return user.can_configure_payroll


class CanReadOwnPayslips(BasePermission):
    """
    Payslips: payroll staff read everyone's, everyone else reads only their own.

    The viewset's queryset already narrows non-payroll users to their own
    records, so this only has to let the request through — the row filtering,
    including the PDF action which resolves through the same queryset, happens
    there. Writes are impossible regardless: the viewset is read-only.

    PRD 3.2 grants the Employee role "R (own)" on payslips, and gating the
    endpoint behind CanRunPayroll made that unreachable — an employee could
    never see their own payslip. The same reading applies to an HR Manager:
    the matrix row means no access to *other people's* payslips, not that a
    person is denied their own.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.method in SAFE_METHODS)


class IsOwnerOrHR(BasePermission):
    """An employee sees only their own records; HR sees everything."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.can_manage_hr:
            return True
        employee = getattr(user, "employee", None)
        if employee is None:
            return False
        owner = getattr(obj, "employee", obj)
        return owner == employee
