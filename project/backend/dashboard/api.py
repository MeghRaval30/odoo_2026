"""
Payroll dashboard aggregation (PRD-5.10).

Every figure is computed from live records — the problem statement warns
explicitly against hardcoded dashboards. Filters (period, department,
employee type, company) re-drive every card and panel.

Aggregates across six models: Employee, Contract, Payslip, PayslipWarning,
Attendance and TimeOff.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Avg, Count, DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view
from rest_framework.response import Response

from attendance.models import Attendance
from core.models import Department
from employees.models import Contract, Employee
from payroll.models import Payrun, Payslip, PayslipLine, PayslipWarning
from timeoff.models import Allocation, TimeOffRequest

ZERO = Decimal("0.00")


def _parse(value, fallback):
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def _filters(request):
    """Resolve the four dashboard filters into a reusable context."""
    today = date.today()
    default_end = today
    default_start = today.replace(day=1)

    period_start = _parse(request.query_params.get("period_start"), default_start)
    period_end = _parse(request.query_params.get("period_end"), default_end)

    # If nothing is passed, fall back to the most recent period that has data
    if not request.query_params.get("period_start"):
        latest = Payrun.objects.order_by("-period_start").first()
        if latest:
            period_start, period_end = latest.period_start, latest.period_end

    return {
        "period_start": period_start,
        "period_end": period_end,
        "department": request.query_params.get("department") or None,
        "employee_type": request.query_params.get("employee_type") or None,
        "company": request.query_params.get("company") or None,
    }


def _payslip_qs(f):
    qs = Payslip.objects.filter(period_start__gte=f["period_start"],
                                period_end__lte=f["period_end"])
    if f["department"]:
        qs = qs.filter(employee__department_id=f["department"])
    if f["employee_type"]:
        qs = qs.filter(employee__employee_type=f["employee_type"])
    if f["company"]:
        qs = qs.filter(employee__company_id=f["company"])
    return qs


def _employee_qs(f):
    qs = Employee.objects.filter(active=True)
    if f["department"]:
        qs = qs.filter(department_id=f["department"])
    if f["employee_type"]:
        qs = qs.filter(employee_type=f["employee_type"])
    if f["company"]:
        qs = qs.filter(company_id=f["company"])
    return qs


def _net_total(payslip_qs):
    """Net is stored on lines, so sum the NET category rather than a column."""
    return PayslipLine.objects.filter(
        payslip__in=payslip_qs, category="NET"
    ).aggregate(t=Coalesce(Sum("amount"), ZERO,
                           output_field=DecimalField()))["t"]


def _gross_total(payslip_qs):
    return PayslipLine.objects.filter(
        payslip__in=payslip_qs, category="GROSS"
    ).aggregate(t=Coalesce(Sum("amount"), ZERO,
                           output_field=DecimalField()))["t"]


@api_view(["GET"])
def dashboard_view(request):
    f = _filters(request)
    payslips = _payslip_qs(f)
    employees = _employee_qs(f)

    # ---------------------------------------------------------------- KPIs
    net_total = _net_total(payslips)
    gross_total = _gross_total(payslips)
    slip_count = payslips.count()
    paid_count = payslips.filter(state=Payrun.PAID).count()
    pending_count = slip_count - paid_count
    avg_salary = (net_total / slip_count) if slip_count else ZERO

    # Month-over-month delta on net pay.
    #
    # Anchored to the previous *payroll period* rather than a rolling N-day
    # window: a 28-day window walked back from 1 February starts on 4 January
    # and therefore excludes January's payslips entirely, which silently
    # produced a null delta.
    prev_slips = Payslip.objects.filter(period_end__lt=f["period_start"])
    if f["department"]:
        prev_slips = prev_slips.filter(employee__department_id=f["department"])
    if f["employee_type"]:
        prev_slips = prev_slips.filter(employee__employee_type=f["employee_type"])

    previous = prev_slips.order_by("-period_start").first()
    if previous is not None:
        prev_window = prev_slips.filter(period_start=previous.period_start,
                                        period_end=previous.period_end)
        prev_net = _net_total(prev_window)
        delta_pct = (float((net_total - prev_net) / prev_net * 100)
                     if prev_net else None)
    else:
        prev_net, delta_pct = ZERO, None

    approved_leave_days = TimeOffRequest.objects.filter(
        state=TimeOffRequest.APPROVED,
        date_from__lte=f["period_end"], date_to__gte=f["period_start"],
        employee__in=employees,
    ).aggregate(t=Coalesce(Sum("duration"), ZERO,
                           output_field=DecimalField()))["t"]

    attendance = Attendance.objects.filter(
        employee__in=employees,
        check_in__date__gte=f["period_start"],
        check_in__date__lte=f["period_end"])
    total_att = attendance.count()
    complete_att = attendance.filter(check_out__isnull=False).count()
    attendance_health = round(complete_att / total_att * 100, 1) if total_att else 0.0

    # ------------------------------------------------- salary by department
    by_dept = list(
        payslips.values(name=F("employee__department__name"))
        .annotate(total=Coalesce(Sum("lines__amount",
                                     filter=Q(lines__category="NET"), ),
                                 ZERO, output_field=DecimalField()),
                  headcount=Count("employee", distinct=True))
        .order_by("-total"))

    # -------------------------------------------------------- salary trend
    trend = []
    for run in Payrun.objects.order_by("period_start")[:12]:
        run_slips = Payslip.objects.filter(payrun=run)
        if f["department"]:
            run_slips = run_slips.filter(employee__department_id=f["department"])
        trend.append({
            "period": run.period_start.strftime("%b %Y"),
            "period_start": run.period_start,
            "net": _net_total(run_slips),
            "payslips": run_slips.count(),
        })

    # ----------------------------------------------- payslip status + alerts
    status_split = list(payslips.values("state").annotate(count=Count("id")))
    alerts = list(
        PayslipWarning.objects
        .filter(payrun__period_start__gte=f["period_start"],
                payrun__period_end__lte=f["period_end"])
        .values("code", "severity")
        .annotate(count=Count("id")).order_by("-count"))
    alert_messages = list(
        PayslipWarning.objects
        .filter(payrun__period_start__gte=f["period_start"],
                payrun__period_end__lte=f["period_end"])
        .values_list("message", flat=True)[:8])

    # -------------------------------------------------- attendance overview
    att_overview = {
        "present": attendance.filter(status=Attendance.PRESENT).count(),
        "overtime": attendance.filter(status=Attendance.OVERTIME).count(),
        "absent": attendance.filter(status=Attendance.ABSENT).count(),
        "half_day": attendance.filter(status=Attendance.HALF_DAY).count(),
        "missing_checkouts": attendance.filter(check_out__isnull=True).count(),
        "manual_edits": attendance.filter(is_manually_edited=True).count(),
        "coverage_pct": attendance_health,
        "total_overtime_hours": attendance.aggregate(
            t=Coalesce(Sum("overtime_hours"), ZERO,
                       output_field=DecimalField()))["t"],
    }

    # ----------------------------------------------------- time off overview
    timeoff_overview = []
    for row in (TimeOffRequest.objects
                .filter(employee__in=employees,
                        date_from__lte=f["period_end"],
                        date_to__gte=f["period_start"])
                .values(type_name=F("time_off_type__name"))
                .annotate(
                    approved_days=Coalesce(
                        Sum("duration", filter=Q(state=TimeOffRequest.APPROVED)),
                        ZERO, output_field=DecimalField()),
                    pending=Count("id", filter=Q(state=TimeOffRequest.TO_APPROVE)))
                .order_by("-approved_days")):
        allocs = Allocation.objects.filter(
            employee__in=employees,
            time_off_type__name=row["type_name"],
            state=Allocation.APPROVED)
        allocated = allocs.aggregate(
            t=Coalesce(Sum("allocated"), ZERO, output_field=DecimalField()))["t"]
        taken = sum((a.taken for a in allocs), ZERO)
        row["remaining_balance"] = allocated - taken if allocated else None
        timeoff_overview.append(row)

    # -------------------------------------------------- department overview
    dept_overview = list(
        Department.objects.annotate(
            headcount=Count("employees", filter=Q(employees__active=True),
                            distinct=True))
        .values("id", "name", "headcount").order_by("-headcount"))
    for row in dept_overview:
        row["monthly_salary"] = _net_total(
            payslips.filter(employee__department_id=row["id"]))

    return Response({
        "filters": {
            "period_start": f["period_start"],
            "period_end": f["period_end"],
            "department": f["department"],
            "employee_type": f["employee_type"],
            "company": f["company"],
        },
        "kpis": {
            "total_net_paid": net_total,
            "total_gross": gross_total,
            "net_delta_pct": delta_pct,
            "payslips_generated": slip_count,
            "payslips_paid": paid_count,
            "payslips_pending": pending_count,
            "avg_salary_per_employee": avg_salary.quantize(Decimal("0.01"))
            if slip_count else ZERO,
            "approved_timeoff_days": approved_leave_days,
            "attendance_health": attendance_health,
            "headcount": employees.count(),
        },
        "salary_by_department": by_dept,
        "salary_trend": trend,
        "payslip_status": status_split,
        "alerts": alerts,
        "alert_messages": alert_messages,
        "attendance_overview": att_overview,
        "timeoff_overview": timeoff_overview,
        "department_overview": dept_overview,
        "sources": [
            "Employee", "Contract", "Payslip", "PayslipWarning",
            "Attendance", "TimeOffRequest",
        ],
    })


@api_view(["GET"])
def filter_options_view(request):
    """Populate the dashboard filter dropdowns."""
    return Response({
        "departments": list(Department.objects.filter(active=True)
                            .values("id", "name").order_by("name")),
        "employee_types": [{"value": v, "label": l}
                           for v, l in Employee.EMPLOYEE_TYPES],
        # order_by() with no arguments clears Employee.Meta.ordering. Without
        # it Django adds first_name and last_name to the SELECT, distinct()
        # then sees one row per employee, and the filter returned the single
        # company 22 times.
        "companies": list(Employee.objects.order_by().values(
            "company__id", "company__name").distinct()),
        "periods": list(Payrun.objects.values(
            "id", "name", "period_start", "period_end").order_by("-period_start")),
    })
