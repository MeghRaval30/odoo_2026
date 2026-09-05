"""
Payroll API — structures, rules, the two-step payrun wizard, and the
Compute / Validate / Mark Paid / Send Payslips action bar.
"""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CanConfigurePayroll, CanRunPayroll
from employees.models import Employee

from . import engine
from .models import (Payrun, Payslip, PayslipLine, PayslipWarning,
                     SalaryRule, SalaryStructure)


# ==========================================================================
# Configuration
# ==========================================================================

class SalaryRuleSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display",
                                             read_only=True)
    computation_display = serializers.CharField(source="get_computation_display",
                                                read_only=True)
    structure_name = serializers.CharField(source="structure.name",
                                           read_only=True)

    class Meta:
        model = SalaryRule
        fields = ["id", "structure", "structure_name", "name", "code",
                  "category", "category_display", "sequence", "computation",
                  "computation_display", "amount", "percentage",
                  "percentage_base", "formula", "condition", "quantity",
                  "appears_on_payslip", "is_employer_cost", "active"]


class SalaryStructureSerializer(serializers.ModelSerializer):
    rules = SalaryRuleSerializer(many=True, read_only=True)
    rule_count = serializers.IntegerField(read_only=True)
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SalaryStructure
        fields = ["id", "name", "code", "company", "active", "rules",
                  "rule_count", "employee_count"]


# ==========================================================================
# Payslips
# ==========================================================================

class PayslipLineSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display",
                                             read_only=True)

    class Meta:
        model = PayslipLine
        fields = ["id", "name", "code", "category", "category_display",
                  "sequence", "quantity", "rate", "amount"]


class PayslipWarningSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True, default=None)
    code_display = serializers.CharField(source="get_code_display",
                                         read_only=True)

    class Meta:
        model = PayslipWarning
        fields = ["id", "payrun", "payslip", "employee", "employee_name",
                  "code", "code_display", "message", "severity"]


class PayslipListSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True)
    department_name = serializers.CharField(source="employee.department.name",
                                            read_only=True, default=None)
    basic = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    gross = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    warning_codes = serializers.SerializerMethodField()

    class Meta:
        model = Payslip
        fields = ["id", "number", "employee", "employee_name",
                  "department_name", "payrun", "period_start", "period_end",
                  "worked_days", "basic", "gross", "net", "state",
                  "warning_codes"]

    def get_warning_codes(self, obj):
        return [w.code for w in obj.warnings.all()]


class PayslipDetailSerializer(PayslipListSerializer):
    lines = PayslipLineSerializer(many=True, read_only=True)
    warnings = PayslipWarningSerializer(many=True, read_only=True)
    contract_reference = serializers.CharField(source="contract.reference",
                                               read_only=True, default=None)
    contract_wage = serializers.DecimalField(source="contract.wage",
                                             max_digits=12, decimal_places=2,
                                             read_only=True, default=None)
    structure_name = serializers.CharField(source="salary_structure.name",
                                           read_only=True)
    allowances = serializers.DecimalField(max_digits=12, decimal_places=2,
                                          read_only=True)
    deductions = serializers.DecimalField(max_digits=12, decimal_places=2,
                                          read_only=True)

    class Meta(PayslipListSerializer.Meta):
        fields = PayslipListSerializer.Meta.fields + [
            "contract", "contract_reference", "contract_wage",
            "salary_structure", "structure_name", "expected_days", "lop_days",
            "overtime_hours", "allowances", "deductions", "lines", "warnings"]


# ==========================================================================
# Payrun
# ==========================================================================

class PayrunSerializer(serializers.ModelSerializer):
    structure_name = serializers.CharField(source="salary_structure.name",
                                           read_only=True)
    payslip_count = serializers.IntegerField(read_only=True)
    warning_count = serializers.IntegerField(read_only=True)
    error_count = serializers.IntegerField(read_only=True)
    total_net = serializers.DecimalField(max_digits=14, decimal_places=2,
                                         read_only=True)
    total_gross = serializers.DecimalField(max_digits=14, decimal_places=2,
                                           read_only=True)
    state_display = serializers.CharField(source="get_state_display",
                                          read_only=True)
    can_compute = serializers.BooleanField(read_only=True)
    can_validate = serializers.BooleanField(read_only=True)
    can_mark_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Payrun
        fields = ["id", "name", "company", "salary_structure",
                  "structure_name", "period_start", "period_end",
                  "employee_type", "state", "state_display", "payslip_count",
                  "warning_count", "error_count", "total_net", "total_gross",
                  "can_compute", "can_validate", "can_mark_paid",
                  "computed_at", "validated_at", "paid_at"]


class SalaryStructureViewSet(viewsets.ModelViewSet):
    queryset = SalaryStructure.objects.prefetch_related("rules")
    serializer_class = SalaryStructureSerializer
    permission_classes = [CanConfigurePayroll]
    filterset_fields = ["company", "active"]
    search_fields = ["name", "code"]


class SalaryRuleViewSet(viewsets.ModelViewSet):
    queryset = SalaryRule.objects.select_related("structure")
    serializer_class = SalaryRuleSerializer
    permission_classes = [CanConfigurePayroll]
    filterset_fields = ["structure", "category", "computation", "active"]
    search_fields = ["name", "code"]
    ordering_fields = ["sequence", "name"]


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [CanRunPayroll]
    filterset_fields = ["payrun", "employee", "state", "employee__department"]
    search_fields = ["number", "employee__first_name", "employee__last_name"]

    def get_queryset(self):
        qs = (Payslip.objects
              .select_related("employee", "employee__department", "contract",
                              "salary_structure", "payrun")
              .prefetch_related("lines", "warnings"))
        user = self.request.user
        if not user.can_run_payroll and user.employee_id:
            qs = qs.filter(employee_id=user.employee_id)
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return PayslipListSerializer
        return PayslipDetailSerializer

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """Print Payslip — returns the rendered PDF (PRD-5.9.4)."""
        from .pdf import render_payslip_pdf
        payslip = self.get_object()
        return render_payslip_pdf(payslip)


class PayrunViewSet(viewsets.ModelViewSet):
    queryset = Payrun.objects.select_related("salary_structure", "company")
    serializer_class = PayrunSerializer
    permission_classes = [CanRunPayroll]
    filterset_fields = ["state", "company", "salary_structure"]
    search_fields = ["name"]
    ordering_fields = ["period_start", "name"]

    # -- the two-step wizard (PRD-5.8) -------------------------------------

    @action(detail=False, methods=["post"], url_path="eligible-employees")
    def eligible_employees(self, request):
        """
        Wizard step 2 — list employees matching the step 1 scope.

        Deliberately creates nothing: the payrun exists only after
        `create_with_employees` is called (PRD-5.8.1, PRD-5.8.2).
        """
        employee_type = request.data.get("employee_type") or ""
        structure_id = request.data.get("salary_structure")
        period_start = request.data.get("period_start")
        period_end = request.data.get("period_end")

        qs = Employee.objects.filter(active=True).select_related(
            "department", "working_schedule")
        if employee_type:
            qs = qs.filter(employee_type=employee_type)

        rows = []
        for emp in qs:
            contract = emp.contract_for_period(period_start, period_end) \
                if period_start and period_end else emp.current_contract
            if structure_id and contract and \
                    str(contract.salary_structure_id) != str(structure_id):
                continue
            rows.append({
                "id": emp.id,
                "name": emp.full_name,
                "department": emp.department.name if emp.department else None,
                "working_hours": (f"{emp.working_schedule.hours_per_week} hours/week"
                                  if emp.working_schedule else None),
                "start_date": contract.start_date if contract else None,
                "wage": contract.wage if contract else None,
                "has_contract": contract is not None,
                "reviewed": contract is not None and emp.has_bank_details,
            })
        return Response(rows)

    @action(detail=False, methods=["post"], url_path="create-with-employees")
    def create_with_employees(self, request):
        """Wizard step 2 confirm — this is where the payrun is finally created."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payrun = serializer.save(created_by=request.user)

        ids = request.data.get("employee_ids") or []
        employees = Employee.objects.filter(id__in=ids)
        engine.create_payrun_payslips(payrun, employees)

        return Response(self.get_serializer(payrun).data,
                        status=status.HTTP_201_CREATED)

    # -- action bar (PRD-5.8.5) --------------------------------------------

    @action(detail=True, methods=["post"])
    def compute(self, request, pk=None):
        payrun = self.get_object()
        try:
            engine.compute_payrun(payrun)
        except ValueError as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(payrun).data)

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        payrun = self.get_object()
        try:
            engine.validate_payrun(payrun)
        except ValueError as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(payrun).data)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        payrun = self.get_object()
        try:
            engine.mark_payrun_paid(payrun)
        except ValueError as exc:
            return Response({"detail": str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(payrun).data)

    @action(detail=True, methods=["post"], url_path="send-payslips")
    def send_payslips(self, request, pk=None):
        """Bulk email each employee their own payslip (PRD-5.9.5)."""
        from .mail import send_payrun_payslips
        payrun = self.get_object()
        sent, skipped = send_payrun_payslips(payrun)
        return Response({"sent": sent, "skipped": skipped,
                         "detail": f"{sent} payslip(s) sent, {skipped} skipped."})

    @action(detail=True, methods=["get"])
    def payslips(self, request, pk=None):
        qs = self.get_object().payslips.select_related(
            "employee", "employee__department").prefetch_related("warnings")
        return Response(PayslipListSerializer(qs, many=True).data)

    @action(detail=True, methods=["get"])
    def warnings(self, request, pk=None):
        qs = self.get_object().warnings.select_related("employee")
        return Response(PayslipWarningSerializer(qs, many=True).data)
