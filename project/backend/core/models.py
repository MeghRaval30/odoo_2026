"""Organisation master data: company, department, position, location, holidays."""

from django.db import models


class TimeStampedModel(models.Model):
    """Audit columns on every table (data-model.md §2)."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(TimeStampedModel):
    name = models.CharField(max_length=200)
    currency = models.CharField(max_length=3, default="INR")
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "companies"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(TimeStampedModel):
    name = models.CharField(max_length=120)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="departments")
    manager = models.ForeignKey("employees.Employee", on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name="managed_departments")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"],
                                    name="uniq_department_per_company"),
        ]

    def __str__(self):
        return self.name


class JobPosition(TimeStampedModel):
    name = models.CharField(max_length=120)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name="positions")
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="job_positions")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WorkLocation(TimeStampedModel):
    name = models.CharField(max_length=120)
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="work_locations")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Holiday(TimeStampedModel):
    """Excluded from leave duration and from expected working days."""

    name = models.CharField(max_length=120)
    date = models.DateField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE,
                                related_name="holidays")

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(fields=["company", "date"],
                                    name="uniq_holiday_per_company_date"),
        ]

    def __str__(self):
        return f"{self.name} ({self.date})"


class Branding(TimeStampedModel):
    """
    Whose company this is, as the interface shows it.

    A single row. `load()` returns it, creating it on first use, because the
    question "what is our logo" must always have an answer -- a shell that has
    to handle a missing branding row would end up with a second, hard-coded
    idea of the product's name, and the two would drift.

    The images are base64 in the row rather than files on disk, following the
    same reasoning as `ImportSource`: a demo that gets reseeded and a machine
    that gets swapped both survive it, and there is no media directory to lose.
    They are small -- a logo that needs more than a couple of hundred kilobytes
    is the wrong asset for a 46px top bar.

    `watermark_b64` is optional and falls back to the logo. The two are
    separate fields rather than one, because a mark that reads well at 28px in
    a dark bar is often not the mark that reads well at 40% of the viewport
    behind a table -- but most companies have only the one file, and requiring
    two would mean most installations have no watermark at all.
    """

    #: The name beside the logo. The product's name is the default rather than
    #: the customer's, because an unconfigured install should say what the
    #: software is, not present itself as somebody's company.
    app_name = models.CharField(max_length=60, default="PeoplePay360")
    company_name = models.CharField(max_length=120, blank=True)

    logo_b64 = models.TextField(blank=True)
    logo_mime = models.CharField(max_length=40, blank=True)
    logo_filename = models.CharField(max_length=255, blank=True)

    watermark_b64 = models.TextField(blank=True)
    watermark_mime = models.CharField(max_length=40, blank=True)
    watermark_filename = models.CharField(max_length=255, blank=True)

    #: How strongly the background mark shows, in percent. Kept as an integer
    #: because it is a setting somebody types, not a computed opacity.
    watermark_opacity = models.PositiveSmallIntegerField(default=4)

    updated_by = models.ForeignKey("accounts.User", null=True, blank=True,
                                   on_delete=models.SET_NULL,
                                   related_name="branding_updates")

    class Meta:
        verbose_name_plural = "branding"

    def __str__(self):
        return self.company_name or self.app_name

    @classmethod
    def load(cls):
        return cls.objects.first() or cls.objects.create()

    def data_uri(self, which="logo"):
        """The image as the browser consumes it, or empty when unset."""
        content = getattr(self, "%s_b64" % which, "")
        mime = getattr(self, "%s_mime" % which, "") or "image/png"
        return "data:%s;base64,%s" % (mime, content) if content else ""
