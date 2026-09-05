"""Core reference API — holidays.

Holidays already drive payroll: `payroll/engine.py` excludes them from expected
working days, which feeds Loss of Pay. They were seeded but had no endpoint, so
the one piece of reference data with a direct payroll consequence was the one
piece nobody could edit.
"""

from rest_framework import serializers, viewsets

from accounts import capabilities as caps
from accounts.permissions import RequiresCapability

from .models import Holiday


class HolidaySerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Holiday
        fields = ["id", "name", "date", "company", "company_name"]

    def validate(self, attrs):
        """Surface the per-company uniqueness guard as a readable error."""
        company = attrs.get("company") or getattr(self.instance, "company", None)
        date = attrs.get("date") or getattr(self.instance, "date", None)
        clash = Holiday.objects.filter(company=company, date=date)
        if self.instance is not None:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                {"date": "This company already has a holiday on that date."})
        return attrs


class HolidayViewSet(viewsets.ModelViewSet):
    queryset = Holiday.objects.select_related("company")
    serializer_class = HolidaySerializer
    permission_classes = [RequiresCapability(write=caps.REFERENCE_WRITE)]
    filterset_fields = ["company"]
    search_fields = ["name"]
    ordering_fields = ["date", "name"]
