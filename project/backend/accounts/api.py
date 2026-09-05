"""Auth and user-management API."""

from django.contrib.auth import authenticate
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Role, User
from .permissions import IsAdmin


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name"]


class UserSerializer(serializers.ModelSerializer):
    roles = RoleSerializer(many=True, read_only=True)
    role_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, queryset=Role.objects.all(),
        source="roles", required=False)
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True, default=None)
    password = serializers.CharField(write_only=True, required=False,
                                     allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "email", "employee", "employee_name", "roles",
                  "role_ids", "is_active", "is_staff", "password"]

    def create(self, validated):
        password = validated.pop("password", None) or "demo1234"
        roles = validated.pop("roles", [])
        user = User.objects.create_user(password=password, **validated)
        user.roles.set(roles)
        return user

    def update(self, instance, validated):
        password = validated.pop("password", None)
        roles = validated.pop("roles", None)
        for key, value in validated.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        if roles is not None:
            instance.roles.set(roles)
        return instance


class MeSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    employee_id = serializers.IntegerField(source="employee.id",
                                           read_only=True, default=None)
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True, default=None)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "employee_id", "employee_name", "roles",
                  "permissions"]

    def get_roles(self, obj):
        return list(obj.role_codes)

    def get_permissions(self, obj):
        return {
            "is_admin": obj.is_admin,
            "can_manage_hr": obj.can_manage_hr,
            "can_approve_leave": obj.can_approve_leave,
            "can_run_payroll": obj.can_run_payroll,
            "can_configure_payroll": obj.can_configure_payroll,
        }


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""
    user = authenticate(request, username=email, password=password)
    if user is None:
        return Response({"detail": "Invalid email or password."},
                        status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": MeSerializer(user).data})


@api_view(["POST"])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"detail": "Signed out."})


@api_view(["GET"])
def me_view(request):
    return Response(MeSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """Admin-only user management (PRD-5.1.2)."""

    queryset = User.objects.select_related("employee").prefetch_related("roles")
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    search_fields = ["email", "employee__first_name", "employee__last_name"]
    filterset_fields = ["is_active", "roles__code"]

    def perform_update(self, serializer):
        # A user must never elevate their own roles (PRD-3.2)
        if (serializer.instance == self.request.user
                and "roles" in serializer.validated_data):
            raise serializers.ValidationError(
                {"roles": "You cannot modify your own roles."})
        serializer.save()


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
