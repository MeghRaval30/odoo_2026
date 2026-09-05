"""Bonds, segments, mass operations and playbooks over HTTP."""

from datetime import date

from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import capabilities as caps
from accounts.permissions import RequiresCapability
from accounts.security import AuditLog
from employees.models import Employee

from . import operations, playbooks
from .compiler import compile_playbook, compile_segment
from .models import (Bond, BondTemplate, BulkOperation, Playbook,
                     PlaybookEvent, Segment)
from .segments import describe, summarise

#: Reading is wide, writing is HR's. A payroll role needs to see a bond's
#: recovery amount to check a run against it and must not be able to issue one.
CAP = RequiresCapability(read=caps.WORKFORCE_READ, write=caps.WORKFORCE_WRITE)


# ==========================================================================
# Segments
# ==========================================================================

class SegmentSerializer(serializers.ModelSerializer):
    description_text = serializers.SerializerMethodField()
    match_count = serializers.SerializerMethodField()

    class Meta:
        model = Segment
        fields = ["id", "name", "description", "criteria", "source",
                  "nl_prompt", "description_text", "match_count", "created_at"]

    def get_description_text(self, obj):
        return describe(obj.criteria)

    def get_match_count(self, obj):
        return obj.resolve().count()


class SegmentViewSet(viewsets.ModelViewSet):
    queryset = Segment.objects.all()
    serializer_class = SegmentSerializer
    permission_classes = [CAP]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user
                        if self.request.user.is_authenticated else None)

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Who does this criteria object match, right now."""
        return Response(summarise(request.data.get("criteria") or {}))

    @action(detail=False, methods=["post"])
    def compile(self, request):
        """
        A sentence in, a proposed rule out.

        The proposal is never executed here. It comes back as criteria the
        operator reads, edits and saves -- and the response carries a live
        count so they can tell straight away whether it matched what they
        meant.
        """
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Describe the group in a sentence."},
                            status=status.HTTP_400_BAD_REQUEST)
        proposal = compile_segment(text)
        proposal["preview"] = summarise(proposal["criteria"])
        return Response(proposal)


# ==========================================================================
# Bonds
# ==========================================================================

class BondTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BondTemplate
        fields = ["id", "name", "description", "duration_months",
                  "recovery_amount", "notice_days", "body", "active"]


class BondSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_email = serializers.CharField(source="employee.work_email", read_only=True)
    template_name = serializers.CharField(source="template.name", read_only=True,
                                          default=None)
    months_served = serializers.SerializerMethodField()
    months_remaining = serializers.SerializerMethodField()
    remaining_liability = serializers.SerializerMethodField()
    days_to_expiry = serializers.SerializerMethodField()
    expiring_soon = serializers.BooleanField(source="is_expiring_soon", read_only=True)
    rendered_body = serializers.SerializerMethodField()

    class Meta:
        model = Bond
        fields = ["id", "employee", "employee_name", "employee_email", "template",
                  "template_name", "state", "start_date", "end_date",
                  "duration_months", "recovery_amount", "notice_days",
                  "signed_at", "signed_name", "breach_date", "breach_note",
                  "months_served", "months_remaining", "remaining_liability",
                  "days_to_expiry", "expiring_soon", "rendered_body"]
        read_only_fields = ["signed_at", "signed_name", "breach_date"]

    def get_months_served(self, obj):
        return obj.months_served()

    def get_months_remaining(self, obj):
        return obj.months_remaining()

    def get_remaining_liability(self, obj):
        return str(obj.remaining_liability())

    def get_days_to_expiry(self, obj):
        return obj.days_to_expiry()

    def get_rendered_body(self, obj):
        return obj.render_body()


class BondTemplateViewSet(viewsets.ModelViewSet):
    queryset = BondTemplate.objects.all()
    serializer_class = BondTemplateSerializer
    permission_classes = [CAP]


class BondViewSet(viewsets.ModelViewSet):
    queryset = Bond.objects.select_related("employee", "template")
    serializer_class = BondSerializer
    permission_classes = [CAP]

    def get_queryset(self):
        qs = super().get_queryset()
        state = self.request.query_params.get("state")
        if state:
            qs = qs.filter(state=state)
        return qs

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user
                        if self.request.user.is_authenticated else None)

    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        bond = self.get_object()
        if bond.state in (Bond.SIGNED, Bond.ACTIVE):
            return Response({"detail": "This bond is already signed."},
                            status=status.HTTP_400_BAD_REQUEST)
        name = (request.data.get("signed_name") or "").strip()
        if not name:
            return Response({"signed_name": "Type the employee's full name."},
                            status=status.HTTP_400_BAD_REQUEST)

        bond.signed_name = name[:160]
        bond.signed_at = timezone.now()
        # Signed and active are the same fact once the term has begun. Keeping
        # both states lets a bond be signed ahead of its start date.
        bond.state = Bond.ACTIVE if bond.start_date <= date.today() else Bond.SIGNED
        bond.save(update_fields=["signed_name", "signed_at", "state", "updated_at"])

        AuditLog.write(request, AuditLog.WORKFORCE_BULK,
                       "Bond signed by %s for %s"
                       % (name, bond.employee.full_name), target=bond)
        return Response(BondSerializer(bond).data)

    @action(detail=False, methods=["get"])
    def expiring(self, request):
        soon = [b for b in self.get_queryset().filter(
            state__in=(Bond.SIGNED, Bond.ACTIVE)) if b.is_expiring_soon]
        return Response(BondSerializer(soon, many=True).data)


# ==========================================================================
# Bulk operations
# ==========================================================================

class BulkOperationSerializer(serializers.ModelSerializer):
    segment_name = serializers.CharField(source="segment.name", read_only=True,
                                         default=None)
    criteria_description = serializers.SerializerMethodField()

    class Meta:
        model = BulkOperation
        fields = ["id", "name", "kind", "state", "segment", "segment_name",
                  "criteria", "criteria_description", "params", "preview",
                  "result", "created_at", "executed_at"]
        read_only_fields = ["state", "preview", "result", "executed_at"]

    def get_criteria_description(self, obj):
        return describe(obj.effective_criteria())


class BulkOperationViewSet(viewsets.ModelViewSet):
    queryset = BulkOperation.objects.select_related("segment")
    serializer_class = BulkOperationSerializer
    permission_classes = [CAP]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user
                        if self.request.user.is_authenticated else None)

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        operation = self.get_object()
        if request.data.get("params"):
            operation.params = request.data["params"]
        result = operations.preview(operation)
        operation.preview = result
        operation.state = BulkOperation.PREVIEWED
        operation.save(update_fields=["preview", "params", "state", "updated_at"])
        return Response(result)

    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        operation = self.get_object()
        if operation.state == BulkOperation.EXECUTED:
            return Response({"detail": "This operation has already run."},
                            status=status.HTTP_400_BAD_REQUEST)
        # Previewing is not optional. It is the record of what was agreed to,
        # and an operation that ran without one cannot be checked afterwards.
        if not operation.preview:
            return Response({"detail": "Preview it before running it."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            result = operations.execute(
                operation,
                actor=request.user if request.user.is_authenticated else None)
        except Exception as exc:                # noqa: BLE001
            operation.state = BulkOperation.FAILED
            operation.result = {"error": str(exc)[:300]}
            operation.save(update_fields=["state", "result", "updated_at"])
            return Response({"detail": "The operation failed: %s" % exc},
                            status=status.HTTP_400_BAD_REQUEST)

        AuditLog.write(request, AuditLog.WORKFORCE_BULK,
                       "%s applied to %d employees"
                       % (operation.get_kind_display(), result.get("matched", 0)),
                       target=operation)
        return Response(result)


# ==========================================================================
# Playbooks
# ==========================================================================

class PlaybookSerializer(serializers.ModelSerializer):
    criteria_description = serializers.SerializerMethodField()
    open_events = serializers.SerializerMethodField()

    class Meta:
        model = Playbook
        fields = ["id", "name", "trigger", "trigger_params", "criteria",
                  "criteria_description", "action", "action_params", "active",
                  "nl_prompt", "last_run", "open_events", "created_at"]
        read_only_fields = ["last_run"]

    def get_criteria_description(self, obj):
        return describe(obj.criteria)

    def get_open_events(self, obj):
        return obj.events.filter(acknowledged=False).count()


class PlaybookEventSerializer(serializers.ModelSerializer):
    playbook_name = serializers.CharField(source="playbook.name", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True, default=None)

    class Meta:
        model = PlaybookEvent
        fields = ["id", "playbook", "playbook_name", "employee", "employee_name",
                  "fired_at", "title", "detail", "acknowledged"]


class PlaybookViewSet(viewsets.ModelViewSet):
    queryset = Playbook.objects.all()
    serializer_class = PlaybookSerializer
    permission_classes = [CAP]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user
                        if self.request.user.is_authenticated else None)

    @action(detail=False, methods=["post"])
    def compile(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Describe the reminder in a sentence."},
                            status=status.HTTP_400_BAD_REQUEST)
        proposal = compile_playbook(text)
        proposal["preview"] = summarise(proposal["criteria"])
        return Response(proposal)

    @action(detail=True, methods=["post"], url_path="dry-run")
    def dry_run(self, request, pk=None):
        """Who this rule would fire for today, without recording anything."""
        return Response(playbooks.evaluate(self.get_object(), commit=False))

    @action(detail=False, methods=["post"], url_path="run-due")
    def run_due(self, request):
        return Response(playbooks.run_all(commit=True))


class PlaybookEventViewSet(viewsets.ModelViewSet):
    queryset = PlaybookEvent.objects.select_related("playbook", "employee")
    serializer_class = PlaybookEventSerializer
    permission_classes = [CAP]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("open") == "1":
            qs = qs.filter(acknowledged=False)
        return qs

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        event = self.get_object()
        event.acknowledged = True
        event.save(update_fields=["acknowledged"])
        return Response(PlaybookEventSerializer(event).data)
