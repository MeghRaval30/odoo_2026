"""Employees, contracts and working schedules API."""

from django.db.models import Count
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CanManageHR
from core.models import Company, Department, JobPosition, WorkLocation

from .models import Contract, Employee, ScheduleLine, WorkingSchedule


# ==========================================================================
# Core reference data
# ==========================================================================

class DepartmentSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(source="manager.full_name",
                                         read_only=True, default=None)
    employee_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Department
        fields = ["id", "name", "company", "manager", "manager_name",
                  "employee_count", "active"]


class JobPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobPosition
        fields = ["id", "name", "department", "company", "active"]


class WorkLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkLocation
        fields = ["id", "name", "company", "active"]


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "currency", "timezone", "active"]


# ==========================================================================
# Working schedules — graded rule #2
# ==========================================================================

class ScheduleLineSerializer(serializers.ModelSerializer):
    day_name = serializers.CharField(source="get_day_of_week_display",
                                     read_only=True)
    hours = serializers.DecimalField(max_digits=6, decimal_places=2,
                                     read_only=True)

    class Meta:
        model = ScheduleLine
        fields = ["id", "day_of_week", "day_name", "start_time", "end_time",
                  "break_minutes", "hours"]


class WorkingScheduleSerializer(serializers.ModelSerializer):
    lines = ScheduleLineSerializer(many=True, required=False)
    # Derived, never accepted as input (PRD-4.2.2)
    hours_per_week = serializers.DecimalField(max_digits=6, decimal_places=2,
                                              read_only=True)
    days_per_week = serializers.IntegerField(read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = WorkingSchedule
        fields = ["id", "name", "company", "company_name", "calendar_type",
                  "timezone", "active", "lines", "hours_per_week",
                  "days_per_week"]

    def create(self, validated):
        lines = validated.pop("lines", [])
        schedule = WorkingSchedule.objects.create(**validated)
        for line in lines:
            ScheduleLine.objects.create(schedule=schedule, **line)
        return schedule

    def update(self, instance, validated):
        lines = validated.pop("lines", None)
        for key, value in validated.items():
            setattr(instance, key, value)
        instance.save()
        if lines is not None:
            instance.lines.all().delete()
            for line in lines:
                ScheduleLine.objects.create(schedule=instance, **line)
        return instance


# ==========================================================================
# Contracts — graded rule #1
# ==========================================================================

class ContractSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True)
    department_name = serializers.CharField(source="department.name",
                                            read_only=True, default=None)
    job_position_name = serializers.CharField(source="job_position.name",
                                              read_only=True, default=None)
    working_schedule_name = serializers.CharField(
        source="working_schedule.name", read_only=True, default=None)
    salary_structure_name = serializers.CharField(
        source="salary_structure.name", read_only=True, default=None)
    state_display = serializers.CharField(source="get_state_display",
                                          read_only=True)

    class Meta:
        model = Contract
        fields = ["id", "reference", "employee", "employee_name", "department",
                  "department_name", "job_position", "job_position_name",
                  "start_date", "end_date", "wage", "working_schedule",
                  "working_schedule_name", "salary_structure",
                  "salary_structure_name", "structure_type", "state",
                  "state_display", "notes"]
        read_only_fields = ["reference"]

    def validate(self, attrs):
        """Surface the overlap guard as a clean API error (PRD-4.1.1)."""
        instance = Contract(**{**{f: getattr(self.instance, f, None)
                                  for f in ("employee", "start_date", "end_date",
                                            "state")},
                               **attrs})
        instance.pk = self.instance.pk if self.instance else None
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"state": exc.messages})
        return attrs


# ==========================================================================
# Employees
# ==========================================================================

class EmployeeListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name",
                                            read_only=True, default=None)
    job_position_name = serializers.CharField(source="job_position.name",
                                              read_only=True, default=None)

    class Meta:
        model = Employee
        fields = ["id", "employee_code", "full_name", "initials", "work_email",
                  "work_phone", "department", "department_name",
                  "job_position", "job_position_name", "employee_type",
                  "active"]


class EmployeeDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    initials = serializers.CharField(read_only=True)
    has_bank_details = serializers.BooleanField(read_only=True)
    department_name = serializers.CharField(source="department.name",
                                            read_only=True, default=None)
    job_position_name = serializers.CharField(source="job_position.name",
                                              read_only=True, default=None)
    manager_name = serializers.CharField(source="manager.full_name",
                                         read_only=True, default=None)
    work_location_name = serializers.CharField(source="work_location.name",
                                               read_only=True, default=None)
    working_schedule_name = serializers.CharField(
        source="working_schedule.name", read_only=True, default=None)
    company_name = serializers.CharField(source="company.name", read_only=True)

    # Smart-button counts — annotated, never stored (PRD-5.2.4)
    contract_count = serializers.IntegerField(read_only=True, default=0)
    attendance_count = serializers.IntegerField(read_only=True, default=0)
    timeoff_count = serializers.IntegerField(read_only=True, default=0)
    allocation_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Employee
        fields = "__all__"


class EmployeeViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageHR]
    filterset_fields = ["department", "employee_type", "active", "company",
                        "job_position"]
    search_fields = ["first_name", "last_name", "work_email", "employee_code"]
    ordering_fields = ["first_name", "last_name", "date_of_joining",
                       "employee_code"]

    def get_queryset(self):
        qs = (Employee.objects
              .select_related("department", "job_position", "manager",
                              "work_location", "working_schedule", "company")
              .annotate(
                  contract_count=Count("contracts", distinct=True),
                  attendance_count=Count("attendances", distinct=True),
                  timeoff_count=Count("timeoff_requests", distinct=True),
                  allocation_count=Count("allocations", distinct=True),
              ).order_by("first_name", "last_name"))
        user = self.request.user
        # An employee sees only themselves (PRD §3.2)
        if not user.can_manage_hr and user.employee_id:
            qs = qs.filter(pk=user.employee_id)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeListSerializer
        return EmployeeDetailSerializer

    @action(detail=True, methods=["get"])
    def contracts(self, request, pk=None):
        """Smart button — related contracts, filtered to this employee."""
        qs = self.get_object().contracts.select_related(
            "department", "job_position", "working_schedule", "salary_structure")
        return Response(ContractSerializer(qs, many=True).data)


class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.select_related(
        "employee", "department", "job_position", "working_schedule",
        "salary_structure")
    serializer_class = ContractSerializer
    permission_classes = [CanManageHR]
    filterset_fields = ["employee", "state", "salary_structure"]
    search_fields = ["reference", "employee__first_name", "employee__last_name"]
    ordering_fields = ["start_date", "wage", "reference"]


class WorkingScheduleViewSet(viewsets.ModelViewSet):
    queryset = WorkingSchedule.objects.prefetch_related("lines").select_related("company")
    serializer_class = WorkingScheduleSerializer
    permission_classes = [CanManageHR]
    filterset_fields = ["company", "calendar_type", "active"]
    search_fields = ["name"]


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = [CanManageHR]
    filterset_fields = ["company", "active"]
    search_fields = ["name"]

    def get_queryset(self):
        return (Department.objects.select_related("manager", "company")
                .annotate(employee_count=Count("employees", distinct=True)))


class JobPositionViewSet(viewsets.ModelViewSet):
    queryset = JobPosition.objects.select_related("department", "company")
    serializer_class = JobPositionSerializer
    permission_classes = [CanManageHR]
    filterset_fields = ["department", "company", "active"]


class WorkLocationViewSet(viewsets.ModelViewSet):
    queryset = WorkLocation.objects.select_related("company")
    serializer_class = WorkLocationSerializer
    permission_classes = [CanManageHR]


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [CanManageHR]
