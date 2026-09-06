"""
The HTTP surface for importing historical payslips.

Deliberately smaller than `api.py`. That module streams its analysis because
the employee import genuinely waits on a language model and the honest thing to
do with fifteen seconds is show the work. This one is rules-only and answers in
milliseconds, so it is a plain request and response -- a progress theatre over
work that has already finished would be a lie about where the time went.

The upload itself is not re-implemented. A file is a file: `/api/intel/sources/`
already reads, sniffs, de-junks and stores one, and a payslip run points at an
`ImportSource` exactly as an employee run does. Only the interpretation
differs, which is the seam this module sits on.
"""

from django.db import transaction
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from accounts import capabilities as caps
from accounts.permissions import RequiresCapability
from accounts.security import AuditLog
from core.models import Company
from payroll.models import SalaryStructure

from . import importer, payslips
from . import payslip_schema as ps
from .models import ImportRun, ImportSource
from .profiler import profile_table

CAP = RequiresCapability(read=caps.DATA_IMPORT, write=caps.DATA_IMPORT)

#: How many preview rows travel to the screen. The operator is checking a
#: decision, not reading a ledger; beyond this the table stops being reviewable
#: and the summary counts carry the meaning instead.
PREVIEW_ROWS = 60


def _company():
    return Company.objects.order_by("id").first()


def _serialise_row(row):
    """One evaluated row, with Decimals rendered as strings for the wire."""
    check = row["check"]
    return {
        "row": row["row"],
        "employee_id": row["employee_id"],
        "employee_name": row["employee_name"],
        "matched_by": row["matched_by"],
        "match_note": row["match_note"],
        "period_label": row["period_label"],
        "period_start": row["period_start"].isoformat() if row["period_start"] else None,
        "period_end": row["period_end"].isoformat() if row["period_end"] else None,
        "components": [
            {
                "key": key,
                "label": ps.FIELDS_BY_KEY[key]["label"],
                "code": ps.FIELDS_BY_KEY[key]["code"],
                "category": ps.FIELDS_BY_KEY[key]["category"],
                "amount": str(amount),
            }
            for key, amount in sorted(
                row["components"].items(),
                key=lambda kv: ps.FIELDS_BY_KEY[kv[0]]["sequence"])
        ],
        "check": {
            "ok": check["ok"],
            "message": check["message"],
            "earnings": str(check["earnings"]),
            "deductions": str(check["deductions"]),
            "computed_net": str(check["computed_net"]),
            "stated_net": str(check["stated_net"]) if check["stated_net"] is not None else None,
            "stated_gross": str(check["stated_gross"]) if check["stated_gross"] is not None else None,
            "stated_deductions": (str(check["stated_deductions"])
                                  if check["stated_deductions"] is not None else None),
            "net_delta": str(check["net_delta"]) if check["net_delta"] is not None else None,
            "gross_delta": str(check["gross_delta"]) if check["gross_delta"] is not None else None,
        },
        "worked_days": str(row["worked_days"]) if row["worked_days"] is not None else None,
        "lop_days": str(row["lop_days"]) if row["lop_days"] is not None else None,
        "problems": row["problems"],
        "warnings": row["warnings"],
        "importable": row["importable"],
    }


def _serialise_summary(summary):
    out = dict(summary)
    out["total_net"] = str(summary["total_net"])
    return out


class PayslipRunSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    row_count = serializers.IntegerField(source="source.row_count", read_only=True)

    class Meta:
        model = ImportRun
        fields = ["id", "source", "source_name", "row_count", "state", "plan",
                  "stats", "error", "created_at", "completed_at"]
        read_only_fields = ["state", "stats", "error", "completed_at"]


class PayslipImportRunViewSet(viewsets.ModelViewSet):
    """
    A payslip import, from a stored file to written payslips.

    Scoped to `target="payslips"` at the queryset rather than filtered in each
    action, so an employee run's id cannot be handed to `commit` here and be
    interpreted under the wrong schema. The two importers write different
    things; letting them share an id space by accident is not worth the one
    saved line.
    """

    serializer_class = PayslipRunSerializer
    permission_classes = [CAP]

    def get_queryset(self):
        return (ImportRun.objects.filter(target="payslips")
                .select_related("source", "created_by"))

    def perform_create(self, serializer):
        serializer.save(
            target="payslips",
            created_by=self.request.user if self.request.user.is_authenticated else None)

    # -- read the file ------------------------------------------------------

    @action(detail=True, methods=["post"])
    def analyze(self, request, pk=None):
        """Profile every column, propose a field for each, and say why."""
        run = self.get_object()
        table = importer.load_table(run.source)
        profiles = profile_table(table)
        plan = payslips.build_plan(table, profiles)

        run.plan = plan
        run.state = ImportRun.MAPPED
        run.llm_used = False
        run.save(update_fields=["plan", "state", "llm_used", "updated_at"])

        mapped = [c for c in plan["columns"] if c["field"]]
        return Response({
            "plan": plan,
            "profiles": profiles,
            "summary": {
                "headers": len(plan["columns"]),
                "mapped": len(mapped),
                "unmapped": len(plan["columns"]) - len(mapped),
                "rows": table.row_count,
            },
            "message": ("Read %d headers. Mapped %d on the payroll vocabulary."
                        % (len(plan["columns"]), len(mapped))),
        })

    @action(detail=True, methods=["patch"], url_path="plan")
    def edit_plan(self, request, pk=None):
        """
        The operator overruling the mapping, or naming the month themselves.

        Re-runs the uniqueness pass and the gap check on the edited plan rather
        than trusting what the screen sent. The screen's copy of the rules and
        the server's copy will drift; only one of them decides.
        """
        run = self.get_object()
        plan = dict(run.plan or {})
        columns = list(plan.get("columns") or [])

        for change in request.data.get("columns") or []:
            index = change.get("index")
            for column in columns:
                if column["index"] == index:
                    field = change.get("field") or None
                    if field and field not in ps.FIELDS_BY_KEY:
                        return Response({"detail": "Unknown field %r." % field},
                                        status=status.HTTP_400_BAD_REQUEST)
                    column["field"] = field
                    column["confidence"] = 1.0 if field else 0.0
                    column["reason"] = ("set by the operator" if field
                                        else "cleared by the operator")
                    break

        if "period_override" in request.data:
            override = (request.data.get("period_override") or "").strip()
            if override and not payslips.parse_month(override):
                return Response(
                    {"detail": "That is not a month I can read. Try 'December 2025'."},
                    status=status.HTTP_400_BAD_REQUEST)
            plan["period_override"] = override or None

        payslips._enforce_uniqueness(columns)
        plan["columns"] = columns
        plan["gaps"] = ps.missing_required(columns)
        run.plan = plan
        run.save(update_fields=["plan", "updated_at"])
        return Response(plan)

    # -- dry run and commit -------------------------------------------------

    def _evaluate(self, run):
        table = importer.load_table(run.source)
        rows = payslips.evaluate(table, run.plan, _company(),
                                 period_override=run.plan.get("period_override"))
        return rows, payslips.summarise(rows)

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        run = self.get_object()
        if not run.plan:
            return Response({"detail": "Analyse the file first."},
                            status=status.HTTP_400_BAD_REQUEST)
        gaps = ps.missing_required(run.plan.get("columns") or [])
        if gaps:
            return Response(
                {"detail": gaps[0]["why"], "gaps": gaps},
                status=status.HTTP_400_BAD_REQUEST)

        rows, summary = self._evaluate(run)
        run.state = ImportRun.PREVIEWED
        run.stats = _serialise_summary(summary)
        run.save(update_fields=["state", "stats", "updated_at"])
        return Response({
            "summary": _serialise_summary(summary),
            "rows": [_serialise_row(r) for r in rows[:PREVIEW_ROWS]],
            "truncated": max(0, len(rows) - PREVIEW_ROWS),
        })

    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        run = self.get_object()
        if not run.plan:
            return Response({"detail": "Analyse the file first."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Claimed in one statement, for the reason recorded on the employee
        # importer's commit: a double-click sends two requests milliseconds
        # apart, and read-then-write lets both through. Here the second would
        # find every row blocked by the duplicate guard and report "0 payslips
        # imported" over the top of a run that had just written sixty.
        claimed = (ImportRun.objects
                   .filter(pk=run.pk)
                   .exclude(state__in=(ImportRun.IMPORTING, ImportRun.DONE))
                   .update(state=ImportRun.IMPORTING))
        if not claimed:
            run.refresh_from_db()
            return Response(
                {"detail": ("This run is already being imported."
                            if run.state == ImportRun.IMPORTING
                            else "This run has already been imported.")},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            rows, summary = self._evaluate(run)
            if not summary["importable"]:
                raise ValueError("No row on this sheet can be imported yet.")
            with transaction.atomic():
                created = payslips.commit(
                    rows, _company(),
                    actor=request.user if request.user.is_authenticated else None)
        except Exception as exc:                # noqa: BLE001
            run.state = ImportRun.FAILED
            run.error = str(exc)[:500]
            run.save(update_fields=["state", "error", "updated_at"])
            return Response({"detail": "Import failed: %s" % exc},
                            status=status.HTTP_400_BAD_REQUEST)

        from django.utils import timezone
        run.state = ImportRun.DONE
        run.completed_at = timezone.now()
        run.stats = dict(_serialise_summary(summary), created=created)
        run.save(update_fields=["state", "completed_at", "stats", "updated_at"])

        AuditLog.write(
            request, AuditLog.DATA_IMPORTED,
            "Imported %d historical payslips across %d payruns from %s"
            % (created["payslips"], created["payruns"], run.source.name),
            target=run)

        return Response({
            "created": created,
            "summary": _serialise_summary(summary),
            "rows": [_serialise_row(r) for r in rows[:PREVIEW_ROWS]],
        })


@api_view(["GET"])
@permission_classes([CAP])
def payslip_fields_view(request):
    """The vocabulary, for the screen's field picker."""
    return Response([
        {
            "key": f["key"], "label": f["label"], "kind": f["kind"],
            "group": f["group"], "hint": f["hint"],
            "category": f.get("category"), "code": f.get("code"),
        }
        for f in ps.PAYSLIP_FIELDS
    ])


@api_view(["GET"])
@permission_classes([CAP])
def payslip_import_health_view(request):
    """Whether this import can run at all, and what it would file against."""
    structure = SalaryStructure.objects.filter(active=True).order_by("id").first()
    return Response({
        "ready": structure is not None,
        "structure": structure.name if structure else None,
        "detail": ("Imported payslips will be filed against %s." % structure.name
                   if structure else
                   "There is no active salary structure to file payslips against."),
        "fields": len(ps.PAYSLIP_FIELDS),
        "components": len(ps.COMPONENT_FIELDS),
    })
