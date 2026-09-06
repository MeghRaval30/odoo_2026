"""
The import studio's HTTP surface.

One endpoint here is unlike anything else in this codebase: `analyze` streams.
It does that because the work genuinely takes between four and twenty seconds
-- the local model has to load and then think -- and there are only two honest
things to do with that time. Hide it behind a spinner, or show the work.

Showing the work turns out to be better than hiding it, and not only for
theatre. The operator watches the header row get found, each column get
profiled, the model get asked, and each mapping get decided with its reasons.
By the time the plan appears they already know how it was reached, so reviewing
it is checking a decision they saw made rather than auditing a black box.
"""

import base64
import json
import time

from django.http import StreamingHttpResponse
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from accounts import capabilities as caps
from accounts.permissions import RequiresCapability
from accounts.security import AuditLog
from core.models import Company, Department, JobPosition, WorkLocation
from employees.models import Employee

from . import codes, enrich, importer
from .llm import LocalModel
from .mapper import build_plan, missing_required
from .models import ImportIssue, ImportRun, ImportSource
from .profiler import profile_table
from .readers import read_table
from .schema import FIELDS_BY_KEY, TARGET_FIELDS

CAP = RequiresCapability(read=caps.DATA_IMPORT, write=caps.DATA_IMPORT)

#: How many rows the grid shows. The screen renders the sheet, not the
#: database, and sixty rows is enough to recognise your own file.
GRID_ROWS = 60


# ==========================================================================
# Serializers
# ==========================================================================

class ImportSourceSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source="uploaded_by.email",
                                             read_only=True, default=None)

    class Meta:
        model = ImportSource
        fields = ["id", "name", "original_filename", "byte_size", "sheet_name",
                  "encoding", "row_count", "column_count", "header_row_index",
                  "junk_rows_above", "notes", "uploaded_by_name", "created_at"]


class ImportRunSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source="source.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.email",
                                            read_only=True, default=None)

    class Meta:
        model = ImportRun
        fields = ["id", "source", "source_name", "target", "state", "plan",
                  "stats", "llm_used", "llm_model", "llm_latency_ms",
                  "created_by_name", "created_at", "completed_at", "error"]
        read_only_fields = ["state", "stats", "llm_used", "llm_model",
                            "llm_latency_ms", "completed_at", "error"]


# ==========================================================================
# Health and the field catalogue
# ==========================================================================

@api_view(["GET"])
@permission_classes([CAP])
def health_view(request):
    """
    Everything the setup screen and the import screen need to be honest.

    Called on screen open, which is also where the model gets warmed: paying
    the eleven-second cold load here means the operator pays it while reading
    the page rather than while watching a progress bar.
    """
    model = LocalModel()
    health = model.health(force=request.query_params.get("force") == "1")
    if health.get("available") and request.query_params.get("warm") == "1":
        model.warm()
    return Response({
        "llm": health,
        "fields": [{k: f[k] for k in ("key", "label", "kind", "required",
                                      "group", "hint")}
                   for f in TARGET_FIELDS],
        "code_policy_default": codes.DEFAULT_POLICY,
    })


def _read_upload(request):
    """
    Pull raw bytes out of whichever upload shape the caller used.

    Returns (bytes, filename, error_response). Shared by the primary source
    and by a second file, so both accept a multipart upload and a base64 body
    on the same terms.
    """
    upload = request.FILES.get("file")
    if upload is not None:
        return upload.read(), upload.name, None

    content = request.data.get("content_b64")
    filename = request.data.get("filename") or "upload.csv"
    if not content:
        return None, None, Response(
            {"detail": "Send a file, or content_b64 with a filename."},
            status=status.HTTP_400_BAD_REQUEST)
    try:
        return base64.b64decode(content), filename, None
    except Exception:                           # noqa: BLE001
        return None, None, Response(
            {"detail": "content_b64 is not valid base64."},
            status=status.HTTP_400_BAD_REQUEST)


#: Auto-fixes that supply a field outright, rather than correcting one.
#: Accepting one of these is a source for that field in exactly the way a
#: column or a second file is.
_FIX_SUPPLIES = {"derive_email": "work_email"}


def missing_required_after(plan):
    """
    Which required fields are still unsourced once everything is counted.

    Three things can supply a field: a column in the primary file, a second
    file joined onto it, and an auto-fix the operator has accepted. They are
    the same kind of answer, so they are pooled here and the question is
    answered once.

    That pooling is the whole point. The screen briefly had its own version of
    this -- it showed "Work email: building addresses from each person's name"
    with a green tick, next to a rail insisting work email was still needed and
    a Preview button that stayed disabled. Two places answering one question is
    how that happens.
    """
    columns = list(plan.get("columns") or [])
    for entry in (plan.get("enrichments") or []):
        for field in (entry.get("fields") or []):
            columns.append({"field": field})
    for fix in (plan.get("apply_fixes") or []):
        supplied = _FIX_SUPPLIES.get(fix)
        if supplied:
            columns.append({"field": supplied})
    return missing_required(columns)


# ==========================================================================
# Sources
# ==========================================================================

class ImportSourceViewSet(viewsets.ModelViewSet):
    queryset = ImportSource.objects.select_related("uploaded_by")
    serializer_class = ImportSourceSerializer
    permission_classes = [CAP]

    def _ingest(self, request, raw, filename, name=None):
        table = read_table(raw, filename)
        if not table.headers:
            return Response(
                {"detail": "That file has no readable columns."},
                status=status.HTTP_400_BAD_REQUEST)

        source = ImportSource.objects.create(
            name=name or filename,
            original_filename=filename,
            content_b64=base64.b64encode(raw).decode("ascii"),
            byte_size=len(raw),
            uploaded_by=request.user if request.user.is_authenticated else None,
            sheet_name=table.sheet_name or "",
            encoding=table.encoding or "",
            row_count=table.row_count,
            column_count=table.column_count,
            header_row_index=table.header_row_index,
            junk_rows_above=table.junk_rows_above,
            notes=table.notes,
        )
        payload = ImportSourceSerializer(source).data
        payload["grid"] = _grid(table)
        return Response(payload, status=status.HTTP_201_CREATED)

    def create(self, request, *args, **kwargs):
        raw, filename, error = _read_upload(request)
        if error:
            return error
        return self._ingest(request, raw, filename)

    @action(detail=True, methods=["get"])
    def grid(self, request, pk=None):
        source = self.get_object()
        return Response(_grid(importer.load_table(source)))


def _grid(table):
    """The sheet as the screen draws it, junk rows included and labelled."""
    return {
        "headers": table.headers,
        "rows": table.rows[:GRID_ROWS],
        "raw_rows": [list(r) for r in table.raw_rows[:table.header_row_index + 1]],
        "header_row_index": table.header_row_index,
        "junk_rows_above": table.junk_rows_above,
        "total_rows": table.row_count,
        "notes": table.notes,
    }


# ==========================================================================
# Runs
# ==========================================================================

def _known_values(company):
    """What the database already calls things, so an import joins rather than duplicates."""
    return {
        "department": list(Department.objects.filter(company=company)
                           .values_list("name", flat=True)),
        "job_position": list(JobPosition.objects.filter(company=company)
                             .values_list("name", flat=True)),
        "work_location": list(WorkLocation.objects.filter(company=company)
                              .values_list("name", flat=True)),
    }


class ImportRunViewSet(viewsets.ModelViewSet):
    queryset = ImportRun.objects.select_related("source", "created_by")
    serializer_class = ImportRunSerializer
    permission_classes = [CAP]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user
                        if self.request.user.is_authenticated else None)

    # -- the streaming analysis ------------------------------------------

    @action(detail=True, methods=["get"])
    def analyze(self, request, pk=None):
        run = self.get_object()
        company = Company.objects.order_by("id").first()
        known = _known_values(company)

        def events():
            def sse(stage, message, progress, payload=None):
                body = {"stage": stage, "message": message,
                        "progress": round(progress, 3)}
                if payload is not None:
                    body["payload"] = payload
                return "data: %s\n\n" % json.dumps(body, default=str)

            try:
                started = time.time()
                yield sse("start", "Reading %s" % run.source.original_filename, 0.02)

                table = importer.load_table(run.source)
                yield sse("structure", _structure_message(table), 0.10, {
                    "header_row_index": table.header_row_index,
                    "junk_rows_above": table.junk_rows_above,
                    "notes": table.notes,
                    "columns": table.column_count,
                    "rows": table.row_count,
                })

                model = LocalModel()
                use_model = model.available()
                # With no model the deterministic path finishes in about forty
                # milliseconds, which reads as a failure rather than as speed.
                # A small pause per column on that path only lets the operator
                # actually see the same reasoning they would otherwise miss.
                pace = 0.0 if use_model else 0.14

                profiles = []
                for i, header in enumerate(table.headers):
                    column = [(r[i] if i < len(r) else "") for r in table.rows]
                    from .profiler import profile_column
                    profile = profile_column(i, header, column)
                    profiles.append(profile)
                    yield sse("profiling", "Reading %r" % header,
                              0.12 + 0.28 * ((i + 1) / max(table.column_count, 1)),
                              {"index": i, "profile": profile})
                    if pace:
                        time.sleep(pace)

                yield sse("model_start",
                          ("Asking %s to read %d headers"
                           % (model.resolve(), len(profiles)))
                          if use_model else
                          "No local model available; matching on rules alone",
                          0.42, {"model": model.resolve(), "available": use_model})

                queue = []
                plan = build_plan(table, profiles,
                                  model=model if use_model else None,
                                  known_values=known,
                                  on_event=queue.append)

                total = max(len(queue), 1)
                for n, event in enumerate(queue, 1):
                    yield sse(event["stage"], event.get("message", ""),
                              0.5 + 0.38 * (n / total), event.get("payload"))
                    if pace:
                        time.sleep(pace)

                run.plan = plan
                run.state = ImportRun.MAPPED
                run.llm_used = bool(plan["llm"].get("used"))
                run.llm_model = plan["llm"].get("model") or ""
                run.llm_latency_ms = plan["llm"].get("latency_ms")
                run.save(update_fields=["plan", "state", "llm_used", "llm_model",
                                        "llm_latency_ms", "updated_at"])

                summary = plan["summary"]
                yield sse("done",
                          "Read %d headers, mapped %d automatically, %d need review"
                          % (summary["columns"], summary["auto"], summary["review"]),
                          1.0, {"plan": plan,
                                "elapsed_ms": int((time.time() - started) * 1000)})
            except Exception as exc:            # noqa: BLE001 - the stream must end
                run.state = ImportRun.FAILED
                run.error = str(exc)[:500]
                run.save(update_fields=["state", "error", "updated_at"])
                yield sse("error", "Analysis failed: %s" % exc, 1.0)

        response = StreamingHttpResponse(events(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    # -- editing the plan -------------------------------------------------

    @action(detail=True, methods=["get", "patch"])
    def plan(self, request, pk=None):
        run = self.get_object()
        if request.method == "GET":
            return Response(run.plan)

        plan = run.plan or {}
        body = request.data

        if "column" in body:
            index = int(body["column"])
            for col in plan.get("columns", []):
                if col["index"] != index:
                    continue
                if "field" in body:
                    field = body["field"] or None
                    if field and field not in FIELDS_BY_KEY:
                        return Response({"detail": "Unknown field %r." % field},
                                        status=status.HTTP_400_BAD_REQUEST)
                    # An operator override is recorded as its own verdict. It
                    # outranks every voter, and the plan should say who decided.
                    col["field"] = field
                    col["decision"] = "auto" if field else "unmapped"
                    col["verdict"] = "operator"
                    col["confidence"] = 1.0 if field else 0.0
                    col["note"] = "Set by hand."
                    if field:
                        from .transforms import preview_transforms, suggest_transforms
                        col["transforms"] = suggest_transforms(field, col["profile"])
                        before, after = preview_transforms(
                            col["profile"].get("sample") or [], col["transforms"])
                        col["sample_before"], col["sample_after"] = before, after
                    else:
                        col["transforms"] = []
                        col["sample_after"] = []
                if "transforms" in body:
                    col["transforms"] = body["transforms"]
                break
            plan["missing_required"] = missing_required_after(plan)
            plan["unmapped_columns"] = [c["index"] for c in plan.get("columns", [])
                                        if not c.get("field")]

        if "apply_fixes" in body:
            plan["apply_fixes"] = [f for f in (body["apply_fixes"] or [])
                                   if f in _FIX_SUPPLIES or f == "skip_row"]
            plan["missing_required"] = missing_required_after(plan)

        if "value_map" in body:
            wanted = body["value_map"]
            for vm in plan.get("value_maps", []):
                if vm.get("column") != int(wanted.get("column", -1)):
                    continue
                overrides = wanted.get("pairs") or {}
                for pair in vm.get("pairs", []):
                    if pair["from"] in overrides:
                        pair["to"] = overrides[pair["from"]]
                        pair["source"] = "operator"
                        pair["status"] = "matched" if pair["to"] else "new"

        summary = plan.get("summary") or {}
        cols = plan.get("columns", [])
        summary.update({
            "columns": len(cols),
            "auto": sum(1 for c in cols if c["decision"] == "auto"),
            "review": sum(1 for c in cols if c["decision"] == "review"),
            "unmapped": sum(1 for c in cols if c["decision"] == "unmapped"),
        })
        plan["summary"] = summary

        run.plan = plan
        run.save(update_fields=["plan", "updated_at"])
        return Response(plan)

    # -- a second file ----------------------------------------------------

    @action(detail=True, methods=["post"])
    def enrich(self, request, pk=None):
        """
        Attach a second file and work out how it completes the first.

        Takes the same upload shapes as a primary source. The response is the
        whole enrichment -- the join it found, what matched, and which fields
        the supplement will fill -- so the screen can show the operator the
        join before they accept it.
        """
        run = self.get_object()
        if not run.plan:
            return Response({"detail": "Analyse the first file before adding a second."},
                            status=status.HTTP_400_BAD_REQUEST)

        raw, filename, error = _read_upload(request)
        if error:
            return error

        supplement_table = read_table(raw, filename)
        if not supplement_table.headers:
            return Response({"detail": "That file has no readable columns."},
                            status=status.HTTP_400_BAD_REQUEST)

        source = ImportSource.objects.create(
            name=filename, original_filename=filename,
            content_b64=base64.b64encode(raw).decode("ascii"),
            byte_size=len(raw),
            uploaded_by=request.user if request.user.is_authenticated else None,
            sheet_name=supplement_table.sheet_name or "",
            encoding=supplement_table.encoding or "",
            row_count=supplement_table.row_count,
            column_count=supplement_table.column_count,
            header_row_index=supplement_table.header_row_index,
            junk_rows_above=supplement_table.junk_rows_above,
            notes=supplement_table.notes)

        primary_table = importer.load_table(run.source)
        already = {c["field"] for c in (run.plan.get("columns") or [])
                   if c.get("field")}
        for previous in (run.plan.get("enrichments") or []):
            already |= set(previous.get("fields") or [])

        model = LocalModel()
        entry = enrich.build_enrichment(
            primary_table, supplement_table, profile_table(supplement_table),
            source, already,
            model=model if model.available() else None,
            known_values=_known_values(Company.objects.order_by("id").first()))

        if not entry.get("join"):
            source.delete()
            return Response(
                {"detail": "Nothing in that file matches the first one. It "
                           "needs a column of ids, emails or names in common."},
                status=status.HTTP_400_BAD_REQUEST)

        plan = run.plan
        plan.setdefault("enrichments", []).append(entry)
        plan["missing_required"] = missing_required_after(plan)
        run.plan = plan
        run.save(update_fields=["plan", "updated_at"])

        entry["grid"] = _grid(supplement_table)
        return Response(entry)

    @action(detail=True, methods=["delete"], url_path=r"enrich/(?P<index>\d+)")
    def drop_enrichment(self, request, pk=None, index=None):
        run = self.get_object()
        plan = run.plan or {}
        entries = plan.get("enrichments") or []
        try:
            entries.pop(int(index))
        except (ValueError, IndexError):
            return Response({"detail": "No such second file."},
                            status=status.HTTP_404_NOT_FOUND)
        plan["enrichments"] = entries
        plan["missing_required"] = missing_required_after(plan)
        run.plan = plan
        run.save(update_fields=["plan", "updated_at"])
        return Response(plan)

    # -- how employees are numbered ---------------------------------------

    @action(detail=True, methods=["post"], url_path="code-policy")
    def code_policy_view(self, request, pk=None):
        """
        Set the numbering scheme, and show what it produces.

        Previewed against the real rows rather than against an example,
        because the year comes from each person's joining date and a scheme
        that looks right on a made-up row can still be wrong on a real one.
        """
        run = self.get_object()
        if not run.plan:
            return Response({"detail": "Analyse the file first."},
                            status=status.HTTP_400_BAD_REQUEST)

        policy = codes.normalise_policy(request.data.get("policy") or {})
        plan = run.plan
        plan["code_policy"] = policy
        run.plan = plan
        run.save(update_fields=["plan", "updated_at"])

        table = importer.load_table(run.source)
        records, _ = importer.build_records(table, plan)
        existing = set(Employee.objects.values_list("employee_code", flat=True))
        return Response({
            "policy": policy,
            "description": codes.describe(policy),
            "examples": codes.preview(records, policy, existing),
            "next_sequence": codes.next_sequence(policy)
            if policy["mode"] == "generate" else None,
        })

    # -- dry run and commit -----------------------------------------------

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        run = self.get_object()
        if not run.plan:
            return Response({"detail": "Analyse the file first."},
                            status=status.HTTP_400_BAD_REQUEST)
        result = importer.run(
            run.source, run.plan, commit=False,
            apply_fixes=(request.data.get("apply_fixes")
                         if "apply_fixes" in request.data
                         else run.plan.get("apply_fixes")) or [],
            email_domain=request.data.get("email_domain"))
        run.state = ImportRun.PREVIEWED
        run.save(update_fields=["state", "updated_at"])
        return Response(result)

    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        run = self.get_object()
        if not run.plan:
            return Response({"detail": "Analyse the file first."},
                            status=status.HTTP_400_BAD_REQUEST)
        # Claim the run in one statement rather than checking and then
        # setting. A double-click sends two commits a few milliseconds apart,
        # and read-then-write let both through: the second passed the check
        # while the first was still inside its transaction, then failed every
        # row on the unique email and reported "0 employees imported" over the
        # top of a run that had just created eleven. The database decides who
        # got there first.
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
        run.state = ImportRun.IMPORTING
        try:
            result = importer.run(
                run.source, run.plan, commit=True,
                actor=request.user if request.user.is_authenticated else None,
                apply_fixes=(request.data.get("apply_fixes")
                             if "apply_fixes" in request.data
                             else run.plan.get("apply_fixes")) or [],
                email_domain=request.data.get("email_domain"))
        except Exception as exc:                # noqa: BLE001
            run.state = ImportRun.FAILED
            run.error = str(exc)[:500]
            run.save(update_fields=["state", "error", "updated_at"])
            return Response({"detail": "Import failed: %s" % exc},
                            status=status.HTTP_400_BAD_REQUEST)

        ImportIssue.objects.filter(run=run).delete()
        ImportIssue.objects.bulk_create([
            ImportIssue(run=run, row_index=i["row"], column=i["column"],
                        severity=i["severity"], code=i["code"],
                        message=i["message"][:300],
                        suggestion=i["suggestion"][:300],
                        auto_fix=i.get("auto_fix", "")[:40])
            for i in result["issues"][:500]])

        importer.finish(run, result)

        created = result["created"]
        AuditLog.write(
            request, AuditLog.DATA_IMPORTED,
            "Imported %d employees and %d contracts from %s"
            % (created["employees"], created["contracts"], run.source.name),
            target=run)
        return Response(result)


@api_view(["GET"])
@permission_classes([CAP])
def fields_view(request):
    return Response([{k: f[k] for k in ("key", "label", "kind", "required",
                                        "group", "hint")}
                     for f in TARGET_FIELDS])


def _structure_message(table):
    if table.junk_rows_above:
        return ("Header found on line %d; %d row%s above it ignored"
                % (table.header_row_index + 1, table.junk_rows_above,
                   "" if table.junk_rows_above == 1 else "s"))
    return "Header on the first line, %d columns" % table.column_count
