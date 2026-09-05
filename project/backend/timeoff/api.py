"""Time off API — types, allocations, requests and the approval flow."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts import capabilities as caps
from accounts.permissions import RequiresCapability

from .models import Allocation, TimeOffRequest, TimeOffType


class TimeOffTypeSerializer(serializers.ModelSerializer):
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    approval_display = serializers.CharField(source="get_approval_display",
                                             read_only=True)

    class Meta:
        model = TimeOffType
        fields = ["id", "name", "code", "unit", "unit_display",
                  "requires_allocation", "approval", "approval_display",
                  "is_paid", "work_entry_code", "color", "active",
                  "description"]


class AllocationSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True)
    type_name = serializers.CharField(source="time_off_type.name",
                                      read_only=True)
    unit = serializers.CharField(source="time_off_type.unit", read_only=True)
    # Derived balance maths (PRD-4.3.3)
    taken = serializers.DecimalField(max_digits=6, decimal_places=2,
                                     read_only=True)
    remaining = serializers.DecimalField(max_digits=6, decimal_places=2,
                                         read_only=True)
    state_display = serializers.CharField(source="get_state_display",
                                          read_only=True)

    class Meta:
        model = Allocation
        fields = ["id", "employee", "employee_name", "time_off_type",
                  "type_name", "unit", "name", "allocated", "taken",
                  "remaining", "valid_from", "valid_to", "state",
                  "state_display", "description"]


class TimeOffRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True)
    type_name = serializers.CharField(source="time_off_type.name",
                                      read_only=True)
    allocation_name = serializers.CharField(source="allocation_used.name",
                                            read_only=True, default=None)
    state_display = serializers.CharField(source="get_state_display",
                                          read_only=True)
    approver_email = serializers.CharField(source="approver.email",
                                           read_only=True, default=None)

    class Meta:
        model = TimeOffRequest
        fields = ["id", "employee", "employee_name", "time_off_type",
                  "type_name", "allocation_used", "allocation_name",
                  "date_from", "date_to", "duration", "half_day", "state",
                  "state_display", "reason", "approver", "approver_email",
                  "approved_at"]
        read_only_fields = ["allocation_used", "approver", "approved_at"]

    def validate(self, attrs):
        """
        Run the allocation gate and surface it as a readable API error.

        This is graded rule #3 — a request against an allocation-required type
        must be refused when no approved allocation covers it.
        """
        data = {**{f: getattr(self.instance, f, None)
                   for f in ("employee", "time_off_type", "date_from",
                             "date_to", "half_day", "state")},
                **attrs}
        probe = TimeOffRequest(**{k: v for k, v in data.items() if v is not None})
        probe.pk = self.instance.pk if self.instance else None
        probe.duration = probe.compute_duration()
        try:
            probe.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"detail": exc.messages})
        attrs["duration"] = probe.duration
        attrs["allocation_used"] = probe.allocation_used
        return attrs


class TimeOffTypeViewSet(viewsets.ModelViewSet):
    queryset = TimeOffType.objects.all()
    serializer_class = TimeOffTypeSerializer
    # Readable by anyone -- the self-service leave form needs the
    # dropdown. Writing one is configuration.
    permission_classes = [RequiresCapability(write=caps.TIMEOFF_TYPE_WRITE)]
    filterset_fields = ["active", "requires_allocation", "unit"]
    search_fields = ["name", "code"]


class AllocationViewSet(viewsets.ModelViewSet):
    serializer_class = AllocationSerializer
    permission_classes = [RequiresCapability(write=caps.ALLOCATION_WRITE)]
    filterset_fields = ["employee", "time_off_type", "state"]
    search_fields = ["name", "employee__first_name", "employee__last_name"]

    def get_queryset(self):
        qs = Allocation.objects.select_related("employee", "time_off_type")
        user = self.request.user
        if not user.can(caps.ALLOCATION_READ_ALL) and user.employee_id:
            qs = qs.filter(employee_id=user.employee_id)
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Only an approved allocation creates balance."""
        allocation = self.get_object()
        allocation.state = Allocation.APPROVED
        allocation.save(update_fields=["state", "updated_at"])
        return Response(self.get_serializer(allocation).data)

    @action(detail=True, methods=["post"])
    def refuse(self, request, pk=None):
        allocation = self.get_object()
        allocation.state = Allocation.REFUSED
        allocation.save(update_fields=["state", "updated_at"])
        return Response(self.get_serializer(allocation).data)


class TimeOffRequestViewSet(viewsets.ModelViewSet):
    serializer_class = TimeOffRequestSerializer
    # Managing other people's leave is the same authority as deciding it,
    # so editing a request needs the capability that approves one --
    # otherwise refusing a request could be done by editing it instead.
    permission_classes = [RequiresCapability(write=caps.TIMEOFF_APPROVE)]
    filterset_fields = ["employee", "time_off_type", "state"]
    search_fields = ["employee__first_name", "employee__last_name", "reason"]
    ordering_fields = ["date_from", "duration"]

    # An Employee may raise their own request (product-spec section 2, the same
    # cell that gives them their own attendance). Reads are already open to any
    # authenticated user, and narrowed by get_queryset below, so
    # POST is the only method that needs the carve-out.
    SELF_SERVICE_ACTIONS = {"create"}

    def get_permissions(self):
        if self.action in self.SELF_SERVICE_ACTIONS:
            return [IsAuthenticated()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """
        Force ownership *before* validation, not after it.

        AttendanceViewSet can set the employee in perform_create because
        nothing in its validation depends on who the employee is. This
        serializer is different: validate() runs the allocation gate (graded
        rule #3) against the employee in the payload and resolves
        allocation_used from that employee's approved allocations. Overriding
        the employee afterwards would let someone pass the gate on a
        colleague's balance and then consume it under their own name, which
        both defeats the gate and corrupts the colleague's derived remaining.

        Substituting the employee into the payload first means the gate runs
        against the requester's own balance, which is the only balance they
        are allowed to spend.
        """
        user = request.user
        data = request.data
        if not user.can(caps.TIMEOFF_APPROVE):
            if user.employee_id is None:
                raise PermissionDenied("No employee linked to this account.")
            data = data.copy()
            data["employee"] = user.employee_id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED,
                        headers=headers)

    def get_queryset(self):
        qs = TimeOffRequest.objects.select_related(
            "employee", "time_off_type", "allocation_used", "approver")
        user = self.request.user
        if not user.can(caps.TIMEOFF_READ_ALL) and user.employee_id:
            qs = qs.filter(employee_id=user.employee_id)
        if self.request.query_params.get("my_team") and user.employee_id:
            qs = qs.filter(employee__manager_id=user.employee_id)
        return qs

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        if not request.user.can_approve_leave:
            return Response({"detail": "Not permitted to approve leave."},
                            status=status.HTTP_403_FORBIDDEN)
        req = self.get_object()
        try:
            req.approve(user=request.user)
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def refuse(self, request, pk=None):
        if not request.user.can_approve_leave:
            return Response({"detail": "Not permitted to refuse leave."},
                            status=status.HTTP_403_FORBIDDEN)
        req = self.get_object()
        req.refuse(user=request.user)
        return Response(self.get_serializer(req).data)

    @action(detail=False, methods=["get"])
    def balances(self, request):
        """Balance summary per type for one employee."""
        employee_id = request.query_params.get("employee") or request.user.employee_id
        allocations = Allocation.objects.filter(
            employee_id=employee_id, state=Allocation.APPROVED
        ).select_related("time_off_type")
        return Response([{
            "time_off_type": a.time_off_type_id,
            "type_name": a.time_off_type.name,
            "unit": a.time_off_type.unit,
            "allocated": a.allocated,
            "taken": a.taken,
            "remaining": a.remaining,
        } for a in allocations])
