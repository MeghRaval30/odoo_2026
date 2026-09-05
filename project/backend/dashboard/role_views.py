"""
The other two dashboards.

Five roles do not want the same home screen. A payroll operator opens on money.
An HR manager opens on people, and on what is sitting in their queue this
morning. An employee opens on themselves.

These are separate **endpoints**, not one endpoint with cards hidden in the
browser. Hiding a card client-side leaks its numbers to anybody who opens the
network tab, and the HR Manager role is defined as having no access to payroll
features — so the payroll figures never leave the server for a role that may
not see them.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts import capabilities as caps
from attendance.models import Attendance
from core.formatting import days_display, hours_minutes
from employees.models import Contract
from payroll.models import Payslip
from timeoff.models import Allocation, TimeOffRequest

from .api import _employee_qs, _filters

ZERO = Decimal("0.00")


def _attendance_facts(attendance):
    """
    Shared attendance arithmetic.

    Worked hours are derived from check in/out and are deliberately not stored,
    so the average cannot be done in SQL. At a few thousand rows per period
    that is cheap; the alternative is a stored derived column, which the data
    model refuses on purpose.
    """
    total = attendance.count()
    complete = attendance.filter(check_out__isnull=False).count()
    overtime = attendance.aggregate(
        t=Coalesce(Sum("overtime_hours"), ZERO,
                   output_field=DecimalField()))["t"]
    worked_rows = [a.worked_hours for a in attendance if a.check_out]
    average = sum(worked_rows, ZERO) / len(worked_rows) if worked_rows else ZERO
    return {
        "present": attendance.filter(status=Attendance.PRESENT).count(),
        "overtime_sessions": attendance.filter(status=Attendance.OVERTIME).count(),
        "absent": attendance.filter(status=Attendance.ABSENT).count(),
        "half_day": attendance.filter(status=Attendance.HALF_DAY).count(),
        "missing_checkouts": attendance.filter(check_out__isnull=True).count(),
        "manual_edits": attendance.filter(is_manually_edited=True).count(),
        "coverage_pct": round(complete / total * 100, 1) if total else 0.0,
        # How much overtime there was, and how many people carried it. The count
        # of overtime *events* on its own answers no question anybody has.
        "total_overtime_hm": hours_minutes(overtime, blank="none"),
        "total_overtime_hours": overtime,
        "overtime_employees": attendance.filter(overtime_hours__gt=0)
        .values("employee").distinct().count(),
        "average_worked_hm": hours_minutes(average, blank="—"),
    }


@api_view(["GET"])
def hr_dashboard_view(request):
    """
    The workforce dashboard — people, attendance quality, leave, approvals.

    Contains no salary figure of any kind. What it does contain is the thing an
    HR manager actually opens the product for: what is waiting on their
    decision, and what will break if nobody acts.
    """
    if not request.user.can(caps.DASHBOARD_HR):
        return Response({"detail": "Not available for your role."}, status=403)

    from accounts.models import ProfileChangeRequest

    f = _filters(request)
    employees = _employee_qs(f)
    today = date.today()

    attendance = Attendance.objects.filter(
        employee__in=employees,
        check_in__date__gte=f["period_start"],
        check_in__date__lte=f["period_end"])
    facts = _attendance_facts(attendance)

    pending_leave = TimeOffRequest.objects.filter(
        employee__in=employees, state=TimeOffRequest.TO_APPROVE)
    pending_allocations = Allocation.objects.filter(
        employee__in=employees, state=Allocation.TO_APPROVE)
    # "Awaiting you" must mean awaiting *you*. A reviewer may never decide a
    # change to their own record -- ProfileChangeRequest.approve() refuses it
    # outright -- so an HR Manager's own pending request is awaiting somebody
    # else, and listing it here put a row in their queue whose Approve button
    # could only ever return 400.
    pending_profile = ProfileChangeRequest.objects.filter(
        state=ProfileChangeRequest.PENDING)
    viewer_employee_id = getattr(request.user, "employee_id", None)
    if viewer_employee_id is not None:
        pending_profile = pending_profile.exclude(employee_id=viewer_employee_id)

    # The HR equivalent of a payroll warning: nothing is broken yet, but it
    # will be. A contract that lapses mid-period means somebody is not paid.
    expiring = (Contract.objects
                .filter(state=Contract.RUNNING, end_date__isnull=False,
                        end_date__gte=today,
                        end_date__lte=today + timedelta(days=45))
                .select_related("employee")
                .order_by("end_date")[:10])

    without_contract = [
        e for e in employees.select_related("department")[:400]
        if e.contract_for_period(f["period_start"], f["period_end"]) is None]

    return Response({
        "filters": {
            "period_start": f["period_start"], "period_end": f["period_end"],
            "department": f["department"], "employee_type": f["employee_type"],
        },
        "kpis": {
            "headcount": employees.count(),
            "joined_this_period": employees.filter(
                date_of_joining__gte=f["period_start"],
                date_of_joining__lte=f["period_end"]).count(),
            "attendance_coverage": facts["coverage_pct"],
            "average_worked_hm": facts["average_worked_hm"],
            "total_overtime_hm": facts["total_overtime_hm"],
            "overtime_employees": facts["overtime_employees"],
            "pending_leave": pending_leave.count(),
            "pending_allocations": pending_allocations.count(),
            "pending_profile_changes": pending_profile.count(),
        },
        "awaiting_you": {
            "leave": [{
                "id": r.pk, "employee": r.employee.full_name,
                "type": r.time_off_type.name,
                "date_from": r.date_from, "date_to": r.date_to,
                "duration": days_display(
                    r.duration,
                    unit="hour" if r.time_off_type.unit == "HOURS" else "day"),
            } for r in pending_leave.select_related(
                "employee", "time_off_type")[:8]],
            "allocations": [{
                "id": a.pk, "employee": a.employee.full_name,
                "type": a.time_off_type.name, "allocated": a.allocated,
            } for a in pending_allocations.select_related(
                "employee", "time_off_type")[:8]],
            "profile_changes": [{
                "id": c.pk, "employee": c.employee.full_name,
                "field": c.field_label, "new_value": c.new_value,
                "sensitive": c.is_sensitive,
            } for c in pending_profile.select_related("employee")[:8]],
        },
        "attendance_overview": facts,
        "headcount_by_department": list(
            employees.values(name=F("department__name"))
            .annotate(headcount=Count("id")).order_by("-headcount")),
        "headcount_by_type": list(
            employees.values(name=F("employee_type"))
            .annotate(headcount=Count("id")).order_by("-headcount")),
        "contracts_expiring": [{
            "id": c.pk, "employee": c.employee.full_name,
            "reference": c.reference, "end_date": c.end_date,
            "days_left": (c.end_date - today).days,
        } for c in expiring],
        "employees_without_contract": [{
            "id": e.pk, "name": e.full_name,
            "department": e.department.name if e.department else None,
        } for e in without_contract[:10]],
        "sources": ["Employee", "Contract", "Attendance", "TimeOffRequest",
                    "Allocation", "ProfileChangeRequest"],
    })


@api_view(["GET"])
def admin_dashboard_view(request):
    """
    The administrator's home screen: accounts, access, and what the system has
    been doing.

    An Admin also holds every payroll capability, so they can reach the payroll
    dashboard from Reports. What they cannot get anywhere else is this: who has
    which role, who is signed in, whether the security posture is what they
    think it is, and what happened recently that a person would be asked about.
    """
    if not request.user.can(caps.USER_MANAGE):
        return Response({"detail": "Not available for your role."}, status=403)

    from accounts.models import (AuditLog, LoginAttempt, NetworkPolicy, Role,
                                 SecuritySetting, User)
    from accounts.security_session import SessionActivity
    from django.utils import timezone

    settings_row = SecuritySetting.load()
    day_ago = timezone.now() - timedelta(days=1)
    recent_failures = LoginAttempt.objects.filter(
        succeeded=False, created_at__gte=day_ago)

    by_role = []
    for code, name in Role.CHOICES:
        by_role.append({
            "code": code, "name": name,
            "count": User.objects.filter(roles__code=code, is_active=True).count(),
        })

    return Response({
        "accounts": {
            "total": User.objects.count(),
            "active": User.objects.filter(is_active=True).count(),
            "disabled": User.objects.filter(is_active=False).count(),
            "unlinked": User.objects.filter(employee__isnull=True).count(),
            "multi_role": sum(
                1 for u in User.objects.prefetch_related("roles")
                if u.roles.count() > 1),
            "by_role": by_role,
        },
        "sessions": {
            "live": SessionActivity.objects.count(),
            "rows": [{
                "email": s.user.email, "ip_address": s.ip_address,
                "started_at": s.started_at, "last_used": s.last_used,
            } for s in SessionActivity.objects.select_related("user")[:8]],
        },
        "posture": {
            "network_enforced": settings_row.enforce_network_policy,
            "punch_network_enforced": settings_row.enforce_network_on_punch,
            "session_bound_to_ip": settings_row.bind_session_to_ip,
            "active_policies": NetworkPolicy.objects.filter(is_active=True).count(),
            "max_failed_logins": settings_row.max_failed_logins,
            "session_idle_minutes": settings_row.session_idle_minutes,
            "session_max_hours": settings_row.session_max_hours,
            "password_min_length": settings_row.password_min_length,
            "your_ip_address": request.META.get("REMOTE_ADDR", ""),
        },
        "sign_ins": {
            "succeeded_24h": LoginAttempt.objects.filter(
                succeeded=True, created_at__gte=day_ago).count(),
            "failed_24h": recent_failures.count(),
            "failed_addresses": list(
                recent_failures.values("ip_address")
                .annotate(count=Count("id")).order_by("-count")[:5]),
        },
        "audit_tail": [{
            "id": a.pk, "action": a.action, "action_display": a.get_action_display(),
            "actor_email": a.actor_email, "summary": a.summary,
            "ip_address": a.ip_address, "created_at": a.created_at,
        } for a in AuditLog.objects.all()[:12]],
    })


@api_view(["GET"])
def my_dashboard_view(request):
    """
    An employee's own screen: am I clocked in, what is my balance, what was I
    paid, and what is waiting on somebody else.

    Every query here is scoped to `request.user.employee` in the query itself
    rather than filtered afterwards, so there is no shape of request that
    returns somebody else's row.
    """
    from accounts.models import ProfileChangeRequest

    employee = getattr(request.user, "employee", None)
    if employee is None:
        return Response(
            {"detail": "This account is not linked to an employee record, so "
                       "there is nothing personal to show. An administrator "
                       "can link it from Users & Roles."},
            status=400)

    today = date.today()
    month_start = today.replace(day=1)
    month_end = today

    # If nothing has been recorded this month, show the most recent month that
    # has something rather than a screen of zeroes. An empty dashboard reads as
    # "the system is broken" far more often than it reads as "you have not
    # clocked in yet", and the label below says which month is on screen.
    if not Attendance.objects.filter(employee=employee,
                                     check_in__date__gte=month_start).exists():
        newest = (Attendance.objects.filter(employee=employee)
                  .order_by("-check_in").first())
        if newest is not None:
            anchor = newest.date
            month_start = anchor.replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    attendance = Attendance.objects.filter(
        employee=employee, check_in__date__gte=month_start,
        check_in__date__lte=month_end)
    worked_rows = [a.worked_hours for a in attendance if a.check_out]
    worked_total = sum(worked_rows, ZERO)
    overtime_total = attendance.aggregate(
        t=Coalesce(Sum("overtime_hours"), ZERO,
                   output_field=DecimalField()))["t"]
    open_session = Attendance.open_session_for(employee)

    allocations = (Allocation.objects
                   .filter(employee=employee, state=Allocation.APPROVED)
                   .select_related("time_off_type"))
    requests_qs = (TimeOffRequest.objects.filter(employee=employee)
                   .select_related("time_off_type").order_by("-date_from"))

    contract = employee.contract_for_period(today, today)
    payslips = (Payslip.objects.filter(employee=employee)
                .select_related("payrun").order_by("-period_start")[:6])

    return Response({
        "employee": {
            "name": employee.full_name,
            "code": employee.employee_code,
            "department": employee.department.name if employee.department else None,
            "job_title": employee.job_position.name if employee.job_position else None,
            "manager": employee.manager.full_name if employee.manager else None,
            "schedule": (employee.working_schedule.name
                         if employee.working_schedule else None),
            "expected_weekly_hm": hours_minutes(
                employee.working_schedule.hours_per_week
                if employee.working_schedule else None),
            "has_bank_details": employee.has_bank_details,
        },
        "attendance": {
            "period_start": month_start,
            "period_end": month_end,
            "period_label": month_start.strftime("%B %Y"),
            "is_current_month": month_start == today.replace(day=1),
            "checked_in": open_session is not None,
            "open_since": open_session.check_in if open_session else None,
            "days_recorded": attendance.count(),
            "worked_this_month_hm": hours_minutes(worked_total, blank="none yet"),
            "overtime_this_month_hm": hours_minutes(overtime_total, blank="none"),
            "missing_checkouts": attendance.filter(check_out__isnull=True).count(),
            "recent": [{
                "id": a.pk, "date": a.date,
                "check_in": a.check_in, "check_out": a.check_out,
                "worked_hm": hours_minutes(a.worked_hours),
                "overtime_hm": hours_minutes(a.overtime_hours),
                "status": a.get_status_display(),
            } for a in attendance.order_by("-check_in")[:7]],
        },
        "leave": {
            "balances": [{
                "type": a.time_off_type.name,
                "unit": a.time_off_type.get_unit_display(),
                "allocated": a.allocated, "taken": a.taken,
                "remaining": a.remaining, "valid_to": a.valid_to,
            } for a in allocations],
            "pending": requests_qs.filter(state=TimeOffRequest.TO_APPROVE).count(),
            "recent": [{
                "id": r.pk, "type": r.time_off_type.name,
                "date_from": r.date_from, "date_to": r.date_to,
                "duration": days_display(
                    r.duration,
                    unit="hour" if r.time_off_type.unit == "HOURS" else "day"),
                "state": r.state,
            } for r in requests_qs[:6]],
        },
        "contract": {
            "reference": contract.reference if contract else None,
            "start_date": contract.start_date if contract else None,
            "end_date": contract.end_date if contract else None,
            "job_position": (contract.job_position.name
                             if contract and contract.job_position else None),
            # Their own wage. The PDF grants the Employee role "view own
            # employee details", and their pay is the most own of those.
            "wage": contract.wage if contract else None,
        },
        "payslips": [{
            "id": p.pk, "number": p.number,
            "period_start": p.period_start, "period_end": p.period_end,
            "net": p.net, "gross": p.gross, "state": p.state,
            "payrun": p.payrun.name if p.payrun else None,
        } for p in payslips],
        "pending_profile_changes": ProfileChangeRequest.objects.filter(
            employee=employee, state=ProfileChangeRequest.PENDING).count(),
    })
