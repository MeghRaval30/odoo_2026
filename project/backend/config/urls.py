"""PeoplePay360 API routing."""

from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.api import RoleViewSet, UserViewSet, login_view, logout_view, me_view
from accounts.selfservice_api import (AuditLogViewSet, NetworkPolicyViewSet,
                                      ProfileChangeRequestViewSet,
                                      change_password_view, my_profile_request_view,
                                      my_profile_update_view, my_profile_view,
                                      my_sessions_view, security_settings_view)
from attendance.api import AttendanceViewSet
from core.api import HolidayViewSet
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
router.register("holidays", HolidayViewSet)

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
router.register("profile-change-requests", ProfileChangeRequestViewSet,
                basename="profilechangerequest")
router.register("security/networks", NetworkPolicyViewSet,
                basename="networkpolicy")
router.register("audit", AuditLogViewSet, basename="auditlog")

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/login/", login_view, name="login"),
    path("api/auth/logout/", logout_view, name="logout"),
    path("api/auth/me/", me_view, name="me"),

    # Self service — what a person may do to their own account
    path("api/me/profile/", my_profile_view, name="my-profile"),
    path("api/me/profile/update/", my_profile_update_view, name="my-profile-update"),
    path("api/me/profile/request/", my_profile_request_view, name="my-profile-request"),
    path("api/me/password/", change_password_view, name="my-password"),
    path("api/me/sessions/", my_sessions_view, name="my-sessions"),

    # Security administration
    path("api/security/settings/", security_settings_view, name="security-settings"),

    path("api/dashboard/", dashboard_view, name="dashboard"),
    path("api/dashboard/filters/", filter_options_view, name="dashboard-filters"),

    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls")),
]
