"""Attendance API, including the check-in / check-out widget endpoints."""

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import capabilities as caps
from accounts.models import AuditLog, SecuritySetting, client_ip
from accounts.permissions import CanManageHR
from core.formatting import hours_minutes, hours_minutes_compact

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
    # The same numbers as hours and minutes. Payroll multiplies the decimal;
    # people read the other one. "8.45" is eight hours twenty-seven, and a
    # timesheet that invites that misreading is a timesheet nobody trusts.
    worked_hm = serializers.SerializerMethodField()
    elapsed_hm = serializers.SerializerMethodField()
    overtime_hm = serializers.SerializerMethodField()
    is_open = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source="get_status_display",
                                           read_only=True)
    edited_by_email = serializers.CharField(source="edited_by.email",
                                            read_only=True, default=None)

    class Meta:
        model = Attendance
        fields = ["id", "employee", "employee_name", "department_name",
                  "manager_name", "check_in", "check_out", "worked_hours",
                  "worked_hm", "elapsed_hours", "elapsed_hm", "is_open",
                  "status", "status_display", "overtime_hours", "overtime_hm",
                  "is_manually_edited", "edited_by_email", "notes"]
        read_only_fields = ["is_manually_edited", "edited_by_email"]

    def get_worked_hm(self, obj):
        return hours_minutes(obj.worked_hours)

    def get_elapsed_hm(self, obj):
        return hours_minutes(obj.elapsed_hours)

    def get_overtime_hm(self, obj):
        return hours_minutes(obj.overtime_hours)


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
        """
        An employee may only create attendance for themselves, and only for
        today.

        Both halves matter. Without the first, anyone can punch a colleague in.
        Without the second, a missed week is a week you can quietly invent on
        the last day of the month — and worked days feed straight into pay, so
        a back-dated record is a self-service raise. HR keeps the ability to
        correct history; that is a different action, by a different person,
        and it is flagged and logged.
        """
        user = self.request.user
        payload = serializer.validated_data

        if user.can(caps.ATTENDANCE_CORRECT):
            record = serializer.save(is_manually_edited=True, edited_by=user)
            AuditLog.write(
                self.request, AuditLog.ATTENDANCE_CORRECTED,
                f"{user.email} created a manual attendance record for "
                f"{record.employee.full_name} on {record.check_in:%d-%b-%Y}",
                target=record)
            return

        if user.employee_id is None:
            raise PermissionDenied("No employee linked to this account.")

        requested = payload.get("employee")
        if requested is not None and requested.pk != user.employee_id:
            raise PermissionDenied(
                "You can only record your own attendance.")

        check_in = payload.get("check_in")
        if check_in is not None:
            today = timezone.localdate()
            when = timezone.localtime(check_in).date()
            if when != today:
                raise PermissionDenied(
                    f"You can only record attendance for today ({today:%d-%b-%Y}). "
                    f"Ask HR to correct an earlier day.")
            if check_in > timezone.now():
                raise PermissionDenied("Attendance cannot start in the future.")

        record = serializer.save(employee_id=user.employee_id)
        AuditLog.write(self.request, AuditLog.ATTENDANCE_PUNCH,
                       f"{record.employee.full_name} recorded attendance for "
                       f"{record.check_in:%d-%b-%Y}", target=record)

    def get_queryset(self):
        qs = Attendance.objects.select_related(
            "employee", "employee__department", "employee__manager")
        user = self.request.user
        if not user.can_manage_hr and user.employee_id:
            qs = qs.filter(employee_id=user.employee_id)
        return qs

    def perform_update(self, serializer):
        """
        Manual corrections are flagged and attributed (PRD-5.5.4), and now
        logged.

        Editing attendance edits pay. The record already carried
        `is_manually_edited` and `edited_by`, which answers "was this touched";
        the audit entry answers "by whom, from where, and what changed" — the
        questions actually asked when a figure is disputed.
        """
        instance = serializer.instance
        before = (instance.check_in, instance.check_out, instance.status,
                  instance.overtime_hours)
        record = serializer.save(is_manually_edited=True,
                                 edited_by=self.request.user)
        after = (record.check_in, record.check_out, record.status,
                 record.overtime_hours)
        if before != after:
            AuditLog.write(
                self.request, AuditLog.ATTENDANCE_CORRECTED,
                f"{self.request.user.email} corrected "
                f"{record.employee.full_name}'s {record.check_in:%d-%b-%Y} "
                f"attendance: in {before[0]:%H:%M} → {after[0]:%H:%M}, "
                f"worked {hours_minutes(record.worked_hours)}", target=record)

    def perform_destroy(self, instance):
        AuditLog.write(
            self.request, AuditLog.ATTENDANCE_CORRECTED,
            f"{self.request.user.email} deleted {instance.employee.full_name}'s "
            f"attendance for {instance.check_in:%d-%b-%Y}", target=instance)
        instance.delete()

    # -- widget endpoints (PRD-5.5.5) --------------------------------------

    @staticmethod
    def _punch_network_check(request):
        """
        A clock you can punch from your sofa is not attendance.

        This is the one place the network rule earns its keep even when general
        sign-in is unrestricted, so it has its own switch:
        `enforce_network_on_punch`.
        """
        settings_row = SecuritySetting.load()
        allowed, reason = settings_row.network_allows(
            client_ip(request), request.user.role_codes, for_punch=True)
        return allowed, reason

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
        can_punch, punch_reason = self._punch_network_check(request)
        return Response({
            "checked_in": session is not None,
            "session": AttendanceSerializer(session).data if session else None,
            "elapsed_hours": session.elapsed_hours if session else 0,
            "elapsed_hm": hours_minutes_compact(
                session.elapsed_hours if session else 0),
            "total_today": total_today,
            "total_today_hm": hours_minutes_compact(total_today),
            "can_punch": can_punch,
            "punch_blocked_reason": punch_reason,
        })

    @action(detail=False, methods=["post"])
    def check_in(self, request):
        employee = request.user.employee
        if employee is None:
            return Response({"detail": "No employee linked to this account."},
                            status=status.HTTP_400_BAD_REQUEST)

        allowed, reason = self._punch_network_check(request)
        if not allowed:
            AuditLog.write(request, AuditLog.ATTENDANCE_PUNCH,
                           f"{employee.full_name} was refused a check-in: {reason}")
            return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

        session, created = Attendance.check_in_employee(employee)
        if created:
            AuditLog.write(request, AuditLog.ATTENDANCE_PUNCH,
                           f"{employee.full_name} checked in at "
                           f"{timezone.localtime(session.check_in):%H:%M}",
                           target=session)
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
