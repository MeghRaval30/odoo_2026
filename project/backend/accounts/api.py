"""Auth and user-management API."""

from django.contrib.auth import authenticate
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import capabilities as caps
from .models import (AuditLog, LoginAttempt, Role, SecuritySetting, User,
                     client_ip)
from .permissions import IsAdmin
from .security_session import SessionActivity


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
    # The sign-in address and the employee record's work address are two
    # different facts and the mockup's grid gives them two different columns.
    # They are usually the same string and the interesting rows are the ones
    # where they are not.
    employee_code = serializers.CharField(source="employee.employee_code",
                                          read_only=True, default=None)
    employee_work_email = serializers.CharField(source="employee.work_email",
                                                read_only=True, default=None)
    password = serializers.CharField(write_only=True, required=False,
                                     allow_blank=True)

    class Meta:
        model = User
        fields = ["id", "email", "employee", "employee_name", "employee_code",
                  "employee_work_email", "roles", "role_ids", "is_active",
                  "is_staff", "password"]

    def validate_role_ids(self, roles):
        """
        One account, one role.

        The link stays many-to-many and capabilities_for() still unions
        whatever it is given, because the matrix has to behave correctly for
        any set it is handed -- including rows that predate this rule. What
        changed is the assignment path: an administrator picks a single role,
        so an account's authority is legible from one word rather than
        reconstructed from the union of several.

        Enforced here rather than only in the form, because a hidden control
        is not enforcement (PRD-3.1).
        """
        if len(roles) > 1:
            names = ", ".join(r.name for r in roles)
            raise serializers.ValidationError(
                f"An account holds one role, not several. Choose one of: "
                f"{names}.")
        return roles

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
    """
    Everything the client needs to draw itself for this account.

    The navigation tree is built here rather than in the frontend so that the
    menu and the API enforcement read the same table. A menu the user cannot
    use is absent, not disabled — which is what the mockup's access note asks
    for. Hiding is presentation; the permission classes still do the enforcing.
    """

    roles = serializers.SerializerMethodField()
    role_names = serializers.SerializerMethodField()
    employee_id = serializers.IntegerField(source="employee.id",
                                           read_only=True, default=None)
    employee_name = serializers.CharField(source="employee.full_name",
                                          read_only=True, default=None)
    employee_code = serializers.CharField(source="employee.employee_code",
                                          read_only=True, default=None)
    job_title = serializers.CharField(source="employee.job_position.name",
                                      read_only=True, default=None)
    department = serializers.CharField(source="employee.department.name",
                                       read_only=True, default=None)
    permissions = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    navigation = serializers.SerializerMethodField()
    home_dashboard = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "employee_id", "employee_name",
                  "employee_code", "job_title", "department", "roles",
                  "role_names", "permissions", "capabilities", "navigation",
                  "home_dashboard"]

    def get_roles(self, obj):
        return sorted(obj.role_codes)

    def get_role_names(self, obj):
        return list(obj.roles.values_list("name", flat=True))

    def get_capabilities(self, obj):
        return sorted(obj.capabilities)

    def get_navigation(self, obj):
        return caps.navigation_for(obj.capabilities)

    def get_home_dashboard(self, obj):
        return caps.dashboard_for(obj.capabilities)

    def get_permissions(self, obj):
        # Kept alongside `capabilities` because screens written before the
        # matrix existed still read these four flags.
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
    """
    Sign in, with the four checks a payroll system needs before it says yes.

    Order matters. Lockout is checked *before* the password, so a locked account
    reveals nothing about whether the guess was right. The network is checked
    *after* the password, so an attacker outside the office cannot enumerate
    valid addresses without also knowing a password. And the failure message is
    the same for a bad email and a bad password — telling an attacker which half
    they got right halves their work.
    """
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""
    settings_row = SecuritySetting.load()

    locked_for = LoginAttempt.lockout_remaining(email, settings_row)
    if locked_for:
        LoginAttempt.record(request, email, False, "locked out")
        return Response(
            {"detail": f"Too many failed attempts. Try again in "
                       f"{locked_for} minute{'s' if locked_for != 1 else ''}."},
            status=status.HTTP_429_TOO_MANY_REQUESTS)

    user = authenticate(request, username=email, password=password)
    if user is None:
        # Django's backend already refuses a deactivated account, so this branch
        # also covers "correct password, disabled user". The response stays the
        # same generic 401 either way — saying "this account is deactivated"
        # would confirm the address exists, which is an enumeration oracle. The
        # distinction is recorded instead, where an administrator can see it and
        # an attacker cannot.
        disabled = User.objects.filter(email=email, is_active=False).exists()
        LoginAttempt.record(request, email, False,
                            "account disabled" if disabled else "bad credentials")
        if disabled:
            AuditLog.write(request, AuditLog.SIGN_IN_FAILED,
                           f"Sign-in attempted on the deactivated account {email}",
                           actor=None)

        remaining = max(0, settings_row.max_failed_logins
                        - _recent_failures(email, settings_row))
        detail = "Invalid email or password."
        if 0 < remaining <= 2:
            detail += f" {remaining} attempt{'s' if remaining != 1 else ''} left."
        return Response({"detail": detail}, status=status.HTTP_401_UNAUTHORIZED)

    address = client_ip(request)
    allowed, reason = settings_row.network_allows(address, user.role_codes)
    if not allowed:
        LoginAttempt.record(request, email, False, "network not permitted")
        AuditLog.write(request, AuditLog.SIGN_IN_FAILED,
                       f"{email} refused: {reason}", actor=None)
        return Response({"detail": reason}, status=status.HTTP_403_FORBIDDEN)

    # A fresh token per sign-in, so `token.created` is the start of *this*
    # session and the expiry in ExpiringTokenAuthentication means what it says.
    Token.objects.filter(user=user).delete()
    SessionActivity.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    SessionActivity.objects.create(
        token_key=token.key, user=user, ip_address=address[:45],
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300])

    LoginAttempt.record(request, email, True)
    AuditLog.write(request, AuditLog.SIGN_IN,
                   f"{email} signed in from {address or 'unknown address'}",
                   actor=user, target=user)

    return Response({"token": token.key, "user": MeSerializer(user).data})


def _recent_failures(email, settings_row):
    from datetime import timedelta

    from django.utils import timezone
    since = timezone.now() - timedelta(minutes=settings_row.lockout_minutes)
    streak = 0
    for succeeded in (LoginAttempt.objects
                      .filter(email=email, created_at__gte=since)
                      .order_by("-created_at")
                      .values_list("succeeded", flat=True)[:50]):
        if succeeded:
            break
        streak += 1
    return streak


@api_view(["POST"])
def logout_view(request):
    AuditLog.write(request, AuditLog.SIGN_OUT, f"{request.user.email} signed out",
                   target=request.user)
    key = request.auth.key if getattr(request, "auth", None) else None
    if key:
        SessionActivity.objects.filter(token_key=key).delete()
    Token.objects.filter(user=request.user).delete()
    SessionActivity.objects.filter(user=request.user).delete()
    return Response({"detail": "Signed out."})


@api_view(["GET"])
def me_view(request):
    return Response(MeSerializer(request.user).data)


class UserViewSet(viewsets.ModelViewSet):
    """
    Admin-only user management (PRD-5.1.2).

    Four invariants are enforced here, and each one closes a way an
    administrator account could be used to quietly take over the system:

    1. **You cannot change your own roles.** Stated outright in the mockup's
       access note: "Users must not be able to assign or elevate their own
       roles."
    2. **You cannot deactivate or delete yourself.** Locking yourself out is
       recoverable; doing it by accident mid-payrun is not.
    3. **The last active Admin cannot be removed, demoted or disabled.** A
       system with no administrator cannot be repaired through the product.
    4. **Every role change is audited**, naming what was added and removed.
    """

    queryset = User.objects.select_related("employee").prefetch_related("roles")
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    search_fields = ["email", "employee__first_name", "employee__last_name"]
    filterset_fields = ["is_active", "roles__code"]

    # -- invariants ---------------------------------------------------------

    @staticmethod
    def _other_admins(exclude_pk):
        return (User.objects.filter(is_active=True, roles__code=Role.ADMIN)
                .exclude(pk=exclude_pk).distinct().count())

    def _guard(self, instance, validated):
        if instance == self.request.user and "roles" in validated:
            raise serializers.ValidationError(
                {"roles": "You cannot change your own roles. Ask another "
                          "administrator to do it."})

        if instance == self.request.user and validated.get("is_active") is False:
            raise serializers.ValidationError(
                {"is_active": "You cannot deactivate your own account."})

        was_admin = Role.ADMIN in instance.role_codes
        if not was_admin:
            return

        losing_admin = ("roles" in validated
                        and not any(r.code == Role.ADMIN for r in validated["roles"]))
        being_disabled = validated.get("is_active") is False
        if (losing_admin or being_disabled) and not self._other_admins(instance.pk):
            raise serializers.ValidationError(
                {"detail": "This is the only active administrator. Grant the "
                           "Admin role to somebody else before changing it."})

    def perform_create(self, serializer):
        user = serializer.save()
        AuditLog.write(
            self.request, AuditLog.USER_CREATED,
            f"{self.request.user.email} created {user.email} with roles "
            f"{', '.join(sorted(user.role_codes)) or 'none'}", target=user)

    def perform_update(self, serializer):
        instance = serializer.instance
        before_roles = set(instance.role_codes)
        was_active = instance.is_active

        self._guard(instance, serializer.validated_data)
        user = serializer.save()
        user.refresh_capabilities()

        after_roles = set(user.role_codes)
        if before_roles != after_roles:
            added = ", ".join(sorted(after_roles - before_roles)) or "none"
            removed = ", ".join(sorted(before_roles - after_roles)) or "none"
            AuditLog.write(
                self.request, AuditLog.ROLES_CHANGED,
                f"{self.request.user.email} changed {user.email}'s roles — "
                f"added: {added}; removed: {removed}", target=user)
        if was_active and not user.is_active:
            # Deactivating must also end any live session, otherwise the
            # account keeps working until its token happens to expire.
            Token.objects.filter(user=user).delete()
            SessionActivity.objects.filter(user=user).delete()
            AuditLog.write(
                self.request, AuditLog.USER_DEACTIVATED,
                f"{self.request.user.email} deactivated {user.email}; "
                f"active sessions ended", target=user)

    def perform_destroy(self, instance):
        if instance == self.request.user:
            raise serializers.ValidationError(
                {"detail": "You cannot delete your own account."})
        if Role.ADMIN in instance.role_codes and not self._other_admins(instance.pk):
            raise serializers.ValidationError(
                {"detail": "This is the only active administrator and cannot "
                           "be deleted."})
        AuditLog.write(self.request, AuditLog.USER_DEACTIVATED,
                       f"{self.request.user.email} deleted {instance.email}",
                       target=instance)
        instance.delete()

    @action(detail=True, methods=["post"], url_path="reset-password")
    def reset_password(self, request, pk=None):
        """
        An administrator sets a temporary password and ends every session.

        Deliberately not "email them a reset link" — this build has no outbound
        transactional mail for auth, and a fake link would be worse than an
        honest one-time password handed over in person.
        """
        user = self.get_object()
        new = (request.data.get("password") or "").strip()
        minimum = SecuritySetting.load().password_min_length
        if len(new) < minimum:
            return Response(
                {"detail": f"The password must be at least {minimum} characters."},
                status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new)
        user.save(update_fields=["password", "updated_at"])
        Token.objects.filter(user=user).delete()
        SessionActivity.objects.filter(user=user).delete()

        AuditLog.write(request, AuditLog.PASSWORD_CHANGED,
                       f"{request.user.email} reset the password for "
                       f"{user.email}; all sessions ended", target=user)
        return Response({"detail": f"Password reset for {user.email}. "
                                   f"Their sessions have been ended."})

    @action(detail=False, methods=["get"], url_path="capability-matrix")
    def capability_matrix(self, request):
        """
        The whole permission table, for the Users & Roles screen.

        Served from the same module the API enforces with, so the grid an
        administrator reads can never drift from what the server actually does.
        """
        return Response({
            "roles": [{"code": code, "name": name,
                       "capabilities": sorted(caps.ROLE_CAPABILITIES[code])}
                      for code, name in Role.CHOICES],
            "baseline": sorted(caps.BASELINE),
            "all": sorted(caps.ALL_CAPABILITIES),
        })


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
