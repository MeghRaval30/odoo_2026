"""
Self-service and security API.

Three groups of endpoints:

* **`/api/me/…`** — what a person may do to their own account: change their
  password, edit the fields that are theirs to edit, raise a request for the
  ones that are not, and see their own sessions.
* **`/api/profile-change-requests/`** — the HR side of that approval queue.
* **`/api/security/…`** and **`/api/audit/`** — Admin only.

Every write here is audited, because every write here is either identity, money
or access.
"""

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from . import capabilities as caps
from .models import (APPROVAL_FIELDS, AuditLog, DIRECT_FIELDS,
                     NetworkPolicy, ProfileChangeRequest, READ_ONLY_FIELDS,
                     Role, SecuritySetting, User, client_ip)
from .permissions import RequiresCapability
from .security_session import SessionActivity


# ==========================================================================
# My profile
# ==========================================================================

class MyProfileSerializer(serializers.Serializer):
    """
    The employee's own record, split into what they may change and what they
    may only look at. The split is data, not markup — the frontend renders the
    three groups from this response rather than hard-coding field names, so a
    change to the policy shows up in the UI without a frontend edit.
    """

    def to_representation(self, employee):
        def label_map(spec):
            return [{"field": f, "label": lbl, "value": _display(employee, f)}
                    for f, lbl in spec.items()]

        pending = {r.field: r.new_value for r in
                   employee.profile_change_requests.filter(
                       state=ProfileChangeRequest.PENDING)}

        return {
            "employee_id": employee.pk,
            "full_name": employee.full_name,
            "initials": employee.initials,
            "job_title": employee.job_position.name if employee.job_position else None,
            "department": employee.department.name if employee.department else None,
            "manager": employee.manager.full_name if employee.manager else None,
            "work_email": employee.work_email,
            "employee_code": employee.employee_code,
            "date_of_joining": employee.date_of_joining,
            "has_bank_details": employee.has_bank_details,
            "editable": label_map(DIRECT_FIELDS),
            "needs_approval": label_map(APPROVAL_FIELDS),
            "read_only": label_map(READ_ONLY_FIELDS),
            "pending": pending,
            "approval": approval_authority(employee),
        }


#: How a role reads in a sentence about who decides something. The model's own
#: display names are titles for a person ("HR Manager"), not descriptions of an
#: authority, and "Needs HR Manager approval" reads like a job advert.
_APPROVER_WORDS = {
    Role.HR_MANAGER: "HR",
    Role.ADMIN: "an administrator",
}


def approval_authority(employee):
    """
    Who can actually decide this person's change requests.

    Not simply "HR". `ProfileChangeRequest.approve` refuses a reviewer deciding
    their own record, so the answer depends on who is asking: an ordinary
    employee's request can be decided by HR or by an administrator, and the HR
    Manager's own request can only be decided by an administrator. Telling her
    "Needs HR approval" names herself, which is both wrong and misleading about
    where the request has gone.

    Computed from the accounts that actually exist rather than from the role
    table, because two HR Managers can decide each other's requests and one
    cannot decide her own. Returned as data for the same reason the field
    groups above are: the screen should not hold a second copy of this rule.
    """
    holders = [u for u in User.objects.filter(is_active=True)
               .prefetch_related("roles")
               if u.can(caps.PROFILE_APPROVE)]

    eligible = [u for u in holders
                if employee is None or u.employee_id != employee.pk]
    excluded = len(eligible) < len(holders)

    # Ordered by the dictionary above rather than by role code or by whichever
    # account came back first, so the sentence reads the same way every time
    # and reads the way a person would say it: HR before the administrator.
    held = {code for user in eligible for code in user.role_codes}
    seen = {code for code in held if code in _APPROVER_WORDS}
    words = [_APPROVER_WORDS[code] for code in _APPROVER_WORDS if code in seen]

    if not words:
        # A real state, not an impossible one: it happens when the only account
        # holding the capability is the person asking. Say so rather than
        # inventing an approver who does not exist.
        label = "nobody else right now"
    elif len(words) == 1:
        label = words[0]
    else:
        label = " or ".join([", ".join(words[:-1]), words[-1]])

    return {"label": label, "roles": sorted(seen), "self_excluded": excluded,
            "can_be_decided": bool(words)}


def _display(employee, field):
    value = getattr(employee, field, None)
    if value is None:
        return ""
    if hasattr(value, "full_name"):
        return value.full_name
    if hasattr(value, "name"):
        return value.name
    return str(value)


def _require_employee(request):
    employee = getattr(request.user, "employee", None)
    if employee is None:
        raise serializers.ValidationError(
            {"detail": "This account is not linked to an employee record, so "
                       "there is no profile to show. An administrator can link "
                       "it from Users & Roles."})
    return employee


@api_view(["GET"])
def my_profile_view(request):
    return Response(MyProfileSerializer().to_representation(_require_employee(request)))


@api_view(["PATCH"])
def my_profile_update_view(request):
    """
    Apply changes to the fields an employee owns.

    Anything outside `DIRECT_FIELDS` is refused by name rather than silently
    dropped — a caller who posts `bank_account_number` here is either confused
    or probing, and both deserve an answer.
    """
    employee = _require_employee(request)

    unknown = set(request.data) - set(DIRECT_FIELDS)
    if unknown:
        gated = sorted(unknown & set(APPROVAL_FIELDS))
        detail = f"These fields cannot be edited directly: {', '.join(sorted(unknown))}."
        if gated:
            detail += (f" {', '.join(gated)} must be raised as a change "
                       f"request for {approval_authority(employee)['label']} "
                       f"to approve.")
        return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

    changed = []
    for field, value in request.data.items():
        before = getattr(employee, field, "")
        if str(before or "") != str(value or ""):
            setattr(employee, field, value or "")
            changed.append(f"{DIRECT_FIELDS[field]}: '{before or '—'}' → '{value or '—'}'")

    if changed:
        employee.save(update_fields=list(request.data) + ["updated_at"])
        AuditLog.write(request, AuditLog.PROFILE_EDITED,
                       f"{employee.full_name} — " + "; ".join(changed),
                       target=employee)

    return Response(MyProfileSerializer().to_representation(employee))


@api_view(["POST"])
def my_profile_request_view(request):
    """
    Raise an approval-gated change.

    One row per field, so HR can approve a corrected surname and refuse a bank
    account in the same sitting. An existing pending request for the same field
    is replaced rather than duplicated — otherwise a user could bury a reviewer
    in near-identical rows and hope one gets waved through.
    """
    employee = _require_employee(request)
    field = request.data.get("field")
    new_value = (request.data.get("new_value") or "").strip()
    reason = (request.data.get("reason") or "").strip()

    if field not in APPROVAL_FIELDS:
        return Response(
            {"detail": f"'{field}' is not a field that can be changed by request. "
                       f"Options are: {', '.join(sorted(APPROVAL_FIELDS))}."},
            status=status.HTTP_400_BAD_REQUEST)
    if not new_value:
        return Response({"detail": "A new value is required."},
                        status=status.HTTP_400_BAD_REQUEST)

    old_value = _display(employee, field)
    if old_value == new_value:
        return Response({"detail": f"{APPROVAL_FIELDS[field]} is already that value."},
                        status=status.HTTP_400_BAD_REQUEST)

    employee.profile_change_requests.filter(
        field=field, state=ProfileChangeRequest.PENDING
    ).update(state=ProfileChangeRequest.CANCELLED)

    change = ProfileChangeRequest.objects.create(
        employee=employee, requested_by=request.user, field=field,
        old_value=old_value[:200], new_value=new_value[:200], reason=reason)

    AuditLog.write(
        request, AuditLog.PROFILE_CHANGE_REQUESTED,
        f"{employee.full_name} requested {APPROVAL_FIELDS[field]} "
        f"'{old_value or '—'}' → '{new_value}'"
        + (" (SENSITIVE)" if change.is_sensitive else ""),
        target=change)

    return Response(ProfileChangeRequestSerializer(change).data,
                    status=status.HTTP_201_CREATED)


@api_view(["POST"])
def change_password_view(request):
    """
    Change your own password.

    The current password is required even though the caller is already
    authenticated: without it, a borrowed unlocked laptop becomes a permanent
    account takeover. Every other session is signed out on success, so if the
    change was prompted by a suspected compromise it actually ends it.
    """
    current = request.data.get("current_password") or ""
    new = request.data.get("new_password") or ""
    confirm = request.data.get("confirm_password") or ""
    user = request.user

    if not user.check_password(current):
        AuditLog.write(request, AuditLog.SIGN_IN_FAILED,
                       f"{user.email} gave the wrong current password when "
                       f"changing it", target=user)
        return Response({"detail": "Your current password is not correct."},
                        status=status.HTTP_400_BAD_REQUEST)
    if new != confirm:
        return Response({"detail": "The two new passwords do not match."},
                        status=status.HTTP_400_BAD_REQUEST)
    if new == current:
        return Response({"detail": "The new password must be different from "
                                   "the current one."},
                        status=status.HTTP_400_BAD_REQUEST)

    minimum = SecuritySetting.load().password_min_length
    if len(new) < minimum:
        return Response(
            {"detail": f"The password must be at least {minimum} characters."},
            status=status.HTTP_400_BAD_REQUEST)
    try:
        validate_password(new, user)
    except DjangoValidationError as exc:
        return Response({"detail": " ".join(exc.messages)},
                        status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new)
    user.save(update_fields=["password", "updated_at"])

    Token.objects.filter(user=user).delete()
    SessionActivity.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)

    AuditLog.write(request, AuditLog.PASSWORD_CHANGED,
                   f"{user.email} changed their own password; all other "
                   f"sessions signed out", target=user)

    return Response({"detail": "Password changed. Other sessions were signed out.",
                     "token": token.key})


@api_view(["GET"])
def my_sessions_view(request):
    """Where this account is currently signed in — the user's own audit."""
    rows = SessionActivity.objects.filter(user=request.user)
    here = request.auth.key if getattr(request, "auth", None) else None
    return Response([{
        "ip_address": s.ip_address,
        "user_agent": s.user_agent,
        "started_at": s.started_at,
        "last_used": s.last_used,
        "current": s.token_key == here,
    } for s in rows])


# ==========================================================================
# The approval queue
# ==========================================================================

class ProfileChangeRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    field_label = serializers.CharField(read_only=True)
    is_sensitive = serializers.BooleanField(read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.email",
                                             read_only=True, default=None)

    class Meta:
        model = ProfileChangeRequest
        fields = ["id", "employee", "employee_name", "field", "field_label",
                  "old_value", "new_value", "reason", "state", "is_sensitive",
                  "reviewed_by", "reviewed_by_name", "reviewed_at",
                  "review_note", "created_at"]
        read_only_fields = fields


class ProfileChangeRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read is scoped: HR sees the whole queue, everyone else sees only their own.

    Writes do not happen here — a request is raised through `/api/me/profile/
    request/` and decided through the two actions below, because both carry
    invariants that a generic update would let through.
    """

    serializer_class = ProfileChangeRequestSerializer
    filterset_fields = ["state", "employee", "field"]
    ordering_fields = ["created_at", "state"]

    def get_queryset(self):
        qs = (ProfileChangeRequest.objects
              .select_related("employee", "requested_by", "reviewed_by"))
        user = self.request.user
        if user.can(caps.PROFILE_APPROVE):
            return qs
        employee_id = getattr(user, "employee_id", None)
        return qs.filter(employee_id=employee_id) if employee_id else qs.none()

    def _decide(self, request, pk, approving):
        change = self.get_object()
        if not request.user.can(caps.PROFILE_APPROVE):
            return Response({"detail": "You cannot decide profile change requests."},
                            status=status.HTTP_403_FORBIDDEN)
        note = (request.data.get("note") or "").strip()
        try:
            if approving:
                change.approve(request.user, note)
            else:
                change.refuse(request.user, note)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.write(
            request, AuditLog.PROFILE_CHANGE_DECIDED,
            f"{request.user.email} {'approved' if approving else 'refused'} "
            f"{change.employee.full_name}'s {change.field_label} change "
            f"'{change.old_value or '—'}' → '{change.new_value}'"
            + (" (SENSITIVE)" if change.is_sensitive else ""),
            target=change)
        return Response(self.get_serializer(change).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._decide(request, pk, True)

    @action(detail=True, methods=["post"])
    def refuse(self, request, pk=None):
        return self._decide(request, pk, False)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Withdraw your own pending request."""
        change = self.get_object()
        if getattr(request.user, "employee_id", None) != change.employee_id:
            return Response({"detail": "You can only withdraw your own request."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            change.cancel()
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(change).data)


# ==========================================================================
# Security administration
# ==========================================================================

class NetworkPolicySerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True,
                                      default="All accounts")

    class Meta:
        model = NetworkPolicy
        fields = ["id", "name", "cidr", "role", "role_name", "description",
                  "is_active", "created_at"]

    def validate(self, attrs):
        policy = NetworkPolicy(**{**{f: getattr(self.instance, f, None)
                                     for f in ("name", "cidr", "role")},
                                  **attrs})
        policy.clean()
        return attrs


class NetworkPolicyViewSet(viewsets.ModelViewSet):
    queryset = NetworkPolicy.objects.select_related("role")
    serializer_class = NetworkPolicySerializer
    permission_classes = [RequiresCapability(read=caps.SECURITY_MANAGE,
                                             write=caps.SECURITY_MANAGE,
                                             delete=caps.SECURITY_MANAGE)]

    def perform_create(self, serializer):
        policy = serializer.save()
        AuditLog.write(self.request, AuditLog.SECURITY_CHANGED,
                       f"Network policy added: {policy}", target=policy)

    def perform_update(self, serializer):
        policy = serializer.save()
        AuditLog.write(self.request, AuditLog.SECURITY_CHANGED,
                       f"Network policy updated: {policy}", target=policy)

    def perform_destroy(self, instance):
        AuditLog.write(self.request, AuditLog.SECURITY_CHANGED,
                       f"Network policy removed: {instance}", target=instance)
        instance.delete()


class SecuritySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySetting
        exclude = ["id", "created_at", "updated_at"]


@api_view(["GET", "PATCH"])
def security_settings_view(request):
    """
    The one settings row.

    A read is allowed to anyone who can manage security; the caller's own
    address is included, because the first thing an administrator needs when
    writing a network rule is to know what address they are on — getting that
    wrong is how you lock yourself out of your own system.
    """
    if not request.user.can(caps.SECURITY_MANAGE):
        return Response({"detail": "Security settings are Admin-only."},
                        status=status.HTTP_403_FORBIDDEN)

    row = SecuritySetting.load()
    if request.method == "PATCH":
        serializer = SecuritySettingSerializer(row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Turning enforcement on from an address no policy covers would lock the
        # administrator out of the system they just configured. Refuse, and say
        # what to add.
        if serializer.validated_data.get("enforce_network_policy") and \
                not row.enforce_network_policy:
            address = client_ip(request)
            probe = SecuritySetting(enforce_network_policy=True)
            allowed, _ = probe.network_allows(address, request.user.role_codes)
            if not allowed:
                return Response(
                    {"detail": f"You are connected from {address}, which no active "
                               f"network policy covers. Add a policy for it first, "
                               f"or you will be locked out the moment this is saved."},
                    status=status.HTTP_400_BAD_REQUEST)

        row = serializer.save()
        AuditLog.write(request, AuditLog.SECURITY_CHANGED,
                       f"{request.user.email} updated security settings: "
                       + ", ".join(sorted(serializer.validated_data)),
                       target=row)

    data = SecuritySettingSerializer(row).data
    data["your_ip_address"] = client_ip(request)
    return Response(data)


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display",
                                           read_only=True)

    class Meta:
        model = AuditLog
        fields = ["id", "actor", "actor_email", "action", "action_display",
                  "summary", "target_type", "target_id", "ip_address",
                  "created_at"]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only by construction — there is no endpoint that edits the trail."""

    queryset = AuditLog.objects.select_related("actor")
    serializer_class = AuditLogSerializer
    permission_classes = [RequiresCapability(read=caps.AUDIT_READ)]
    filterset_fields = ["action", "actor"]
    search_fields = ["summary", "actor_email", "ip_address"]
    ordering_fields = ["created_at"]
