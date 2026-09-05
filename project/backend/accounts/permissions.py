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
    """Payrun and payslip access — Payroll User and above."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return user.can_run_payroll or user.is_admin
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
