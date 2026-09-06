"""
What an import leaves behind.

An import is not a button, it is a record. Three things are kept: the file as it
arrived, the plan that was approved, and every issue found along the way. That
combination is what makes the operation auditable -- six months later somebody
can ask why an employee's wage is what it is and the answer is a stored plan
saying "column 5, currency stripped, divided by twelve, approved by Sara on the
sixth".

The plan is a JSON blob rather than a table of rows on purpose. It is written
once by the mapper, edited by the operator, and read back whole; normalising it
into columns and transforms and votes would buy queries nobody runs and cost
the ability to hand the whole thing to the screen in one response.
"""

from django.conf import settings
from django.db import models

from core.models import TimeStampedModel


class ImportSource(TimeStampedModel):
    """A file somebody uploaded, kept exactly as it arrived."""

    name = models.CharField(max_length=200)
    original_filename = models.CharField(max_length=255)
    #: Base64 of the original bytes. Small files, and keeping them in the row
    #: means an import is reproducible from the database alone -- no media
    #: directory to lose, which matters for a demo that gets reseeded.
    content_b64 = models.TextField()
    byte_size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL,
                                    related_name="import_sources")
    sheet_name = models.CharField(max_length=120, blank=True)
    encoding = models.CharField(max_length=24, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    column_count = models.PositiveIntegerField(default=0)
    header_row_index = models.PositiveIntegerField(default=0)
    junk_rows_above = models.PositiveIntegerField(default=0)
    notes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class ImportRun(TimeStampedModel):
    DRAFT = "DRAFT"
    PROFILED = "PROFILED"
    MAPPED = "MAPPED"
    PREVIEWED = "PREVIEWED"
    IMPORTING = "IMPORTING"
    DONE = "DONE"
    FAILED = "FAILED"
    STATES = [
        (DRAFT, "Draft"), (PROFILED, "Profiled"), (MAPPED, "Mapped"),
        (PREVIEWED, "Previewed"), (IMPORTING, "Importing"),
        (DONE, "Done"), (FAILED, "Failed"),
    ]

    source = models.ForeignKey(ImportSource, on_delete=models.CASCADE,
                               related_name="runs")
    target = models.CharField(max_length=40, default="employees")
    state = models.CharField(max_length=12, choices=STATES, default=DRAFT)

    plan = models.JSONField(default=dict, blank=True)
    stats = models.JSONField(default=dict, blank=True)

    #: Recorded rather than inferred. Whether the model ran is a fact about
    #: this run, and a run done on rules alone must still say so a year later.
    llm_used = models.BooleanField(default=False)
    llm_model = models.CharField(max_length=80, blank=True)
    llm_latency_ms = models.PositiveIntegerField(null=True, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="import_runs")
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s (%s)" % (self.source.name, self.get_state_display())

    @property
    def mapped_columns(self):
        return [c for c in (self.plan.get("columns") or []) if c.get("field")]


class ImportIssue(models.Model):
    ERROR = "error"
    WARNING = "warning"
    SEVERITIES = [(ERROR, "Error"), (WARNING, "Warning")]

    run = models.ForeignKey(ImportRun, on_delete=models.CASCADE,
                            related_name="issues")
    row_index = models.IntegerField(default=-1)
    column = models.CharField(max_length=80, blank=True)
    severity = models.CharField(max_length=8, choices=SEVERITIES, default=WARNING)
    code = models.CharField(max_length=40)
    message = models.CharField(max_length=300)
    suggestion = models.CharField(max_length=300, blank=True)
    auto_fix = models.CharField(max_length=40, blank=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["severity", "row_index"]

    def __str__(self):
        return "%s row %d: %s" % (self.code, self.row_index, self.message)
