"""PeoplePay360 API routing."""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.api import RoleViewSet, UserViewSet, login_view, logout_view, me_view
from attendance.api import AttendanceViewSet
from dashboard.api import dashboard_view, filter_options_view
from employees.api import (CompanyViewSet, ContractViewSet, DepartmentViewSet,
                           EmployeeViewSet, JobPositionViewSet,
                           WorkLocationViewSet, WorkingScheduleViewSet)
from payroll.api import (PayrunViewSet, PayslipViewSet, SalaryRuleViewSet,
                         SalaryStructureViewSet)
from timeoff.api import (AllocationViewSet, TimeOffRequestViewSet,
                         TimeOffTypeViewSet)

router = DefaultRouter()

# HR master data
router.register("employees", EmployeeViewSet, basename="employee")
router.register("contracts", ContractViewSet)
router.register("working-schedules", WorkingScheduleViewSet)
router.register("departments", DepartmentViewSet, basename="department")
router.register("job-positions", JobPositionViewSet)
router.register("work-locations", WorkLocationViewSet)
router.register("companies", CompanyViewSet)

# Attendance
router.register("attendance", AttendanceViewSet, basename="attendance")

# Time off
router.register("timeoff-types", TimeOffTypeViewSet)
router.register("allocations", AllocationViewSet, basename="allocation")
router.register("timeoff-requests", TimeOffRequestViewSet,
                basename="timeoffrequest")

# Payroll
router.register("salary-structures", SalaryStructureViewSet)
router.register("salary-rules", SalaryRuleViewSet)
router.register("payruns", PayrunViewSet)
router.register("payslips", PayslipViewSet, basename="payslip")

# Administration
router.register("users", UserViewSet)
router.register("roles", RoleViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/login/", login_view, name="login"),
    path("api/auth/logout/", logout_view, name="logout"),
    path("api/auth/me/", me_view, name="me"),

    path("api/dashboard/", dashboard_view, name="dashboard"),
    path("api/dashboard/filters/", filter_options_view, name="dashboard-filters"),

    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
