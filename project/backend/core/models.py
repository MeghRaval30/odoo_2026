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
