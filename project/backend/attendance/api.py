"""Attendance API, including the check-in / check-out widget endpoints."""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CanManageHR

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True)
    department_name = serializers.CharField(source="employee.department.name",
                                            read_only=True, default=None)
    manager_name = serializers.CharField(source="employee.manager.full_name",
                                         read_only=True, default=None)
    # Derived from check in/out, never accepted as input
    worked_hours = serializers.DecimalField(max_digits=6, decimal_places=2,
                                            read_only=True)
    elapsed_hours = serializers.DecimalField(max_digits=6, decimal_places=2,
                                             read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source="get_status_display",
                                           read_only=True)

    class Meta:
        model = Attendance
        fields = ["id", "employee", "employee_name", "department_name",
                  "manager_name", "check_in", "check_out", "worked_hours",
                  "elapsed_hours", "is_open", "status", "status_display",
                  "overtime_hours", "is_manually_edited", "notes"]
        read_only_fields = ["is_manually_edited"]


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [CanManageHR]
    filterset_fields = ["employee", "status", "employee__department"]
    search_fields = ["employee__first_name", "employee__last_name"]
    ordering_fields = ["check_in", "check_out"]

    #: Actions any authenticated employee may perform on their own attendance.
    #: PRD §3.2 grants Employee create-and-read on their own records, and the
    #: check-in widget is explicitly employee-facing — gating these behind
    #: CanManageHR would make the widget unusable for the people who need it.
    SELF_SERVICE_ACTIONS = {"status", "check_in", "check_out", "create"}

    def get_permissions(self):
        if self.action in self.SELF_SERVICE_ACTIONS:
            return [IsAuthenticated()]
        return super().get_permissions()

    def perform_create(self, serializer):
        """An employee may only create attendance for themselves."""
        user = self.request.user
        if not user.can_manage_hr:
            if user.employee_id is None:
                raise PermissionDenied("No employee linked to this account.")
            serializer.save(employee_id=user.employee_id)
        else:
            serializer.save()

    def get_queryset(self):
        qs = Attendance.objects.select_related(
            "employee", "employee__department", "employee__manager")
        user = self.request.user
        if not user.can_manage_hr and user.employee_id:
            qs = qs.filter(employee_id=user.employee_id)
        return qs

    def perform_update(self, serializer):
        """Manual corrections are flagged and attributed (PRD-5.5.4)."""
        serializer.save(is_manually_edited=True, edited_by=self.request.user)

    # -- widget endpoints (PRD-5.5.5) --------------------------------------

    @action(detail=False, methods=["get"])
    def status(self, request):
        """Drives the red/green top-bar indicator."""
        employee = request.user.employee
        if employee is None:
            return Response({"detail": "No employee linked to this account."},
                            status=status.HTTP_400_BAD_REQUEST)
        session = Attendance.open_session_for(employee)
        today = Attendance.objects.filter(
            employee=employee, check_in__date=timezone.localdate())
        total_today = sum((a.worked_hours for a in today), Decimal("0.00"))
        return Response({
            "checked_in": session is not None,
            "session": AttendanceSerializer(session).data if session else None,
            "elapsed_hours": session.elapsed_hours if session else 0,
            "total_today": total_today,
        })

    @action(detail=False, methods=["post"])
    def check_in(self, request):
        employee = request.user.employee
        if employee is None:
            return Response({"detail": "No employee linked to this account."},
                            status=status.HTTP_400_BAD_REQUEST)
        session, created = Attendance.check_in_employee(employee)
        return Response(
            {"created": created, "session": AttendanceSerializer(session).data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def check_out(self, request):
        employee = request.user.employee
        if employee is None:
            return Response({"detail": "No employee linked to this account."},
                            status=status.HTTP_400_BAD_REQUEST)
        session = Attendance.check_out_employee(employee)
        if session is None:
            return Response({"detail": "No open session to check out of."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(AttendanceSerializer(session).data)
