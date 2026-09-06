"""
Security models — network policy, sign-in throttling, and the audit trail.

A payroll system is a money system, and the interesting attacks on one are not
exotic. They are: point somebody's salary at your own bank account, punch a
clock you were not at, approve your own leave, hand yourself a role you were not
given, and sign in from somewhere you should not be. Everything in this module
exists to close one of those.

The controls that live *here* are the ones that need stored state. The rest —
"you cannot approve your own request", "you cannot grant a role you do not
hold" — are invariants enforced at the point of action, because a check that
runs anywhere other than where the write happens is a check somebody will
eventually route around.
"""

import ipaddress
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


def client_ip(request) -> str:
    """
    The caller's address.

    `X-Forwarded-For` is only consulted when the request actually arrived
    through a proxy we trust, because the header is attacker-controlled: a
    system that always believes it lets anyone claim to be on the office
    network by setting one header. `TRUSTED_PROXY_COUNT` in settings says how
    many hops to peel; the default of zero means the header is ignored entirely.
    """
    from django.conf import settings

    hops = getattr(settings, "TRUSTED_PROXY_COUNT", 0)
    if hops:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        chain = [p.strip() for p in forwarded.split(",") if p.strip()]
        if len(chain) >= hops:
            return chain[-hops]
    return request.META.get("REMOTE_ADDR", "") or ""


# ==========================================================================
# Where people may sign in from
# ==========================================================================

class NetworkPolicy(TimeStampedModel):
    """
    An address range sign-in is permitted from — "only on the office Wi-Fi".

    Stored as CIDR so a single row covers a whole network. A policy can be
    scoped to one role, which is the realistic shape of this rule: payroll staff
    are pinned to the office because they can move money, while an employee
    checking their payslip on a phone is not. With no active policy at all the
    system is open — a half-configured allowlist that locks everybody out on
    first deploy is worse than no allowlist.
    """

    name = models.CharField(max_length=80)
    cidr = models.CharField(
        max_length=64,
        help_text="IPv4 or IPv6 network, e.g. 192.168.1.0/24 or 203.0.113.7/32")
    role = models.ForeignKey("accounts.Role", on_delete=models.CASCADE,
                             null=True, blank=True, related_name="network_policies",
                             help_text="Leave empty to apply to every account.")
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["role__code", "name"]
        verbose_name_plural = "network policies"

    def __str__(self):
        scope = self.role.name if self.role else "All accounts"
        return f"{self.name} ({self.cidr}) — {scope}"

    def clean(self):
        try:
            ipaddress.ip_network(self.cidr, strict=False)
        except ValueError as exc:
            raise ValidationError({"cidr": f"Not a valid network: {exc}"})

    def contains(self, address: str) -> bool:
        try:
            return (ipaddress.ip_address(address)
                    in ipaddress.ip_network(self.cidr, strict=False))
        except ValueError:
            return False


class SecuritySetting(TimeStampedModel):
    """
    One row. The knobs an Admin can turn without a deploy.

    A singleton rather than settings.py because the person who needs to relax
    the lockout at 2am during a demo is an administrator with a browser, not
    someone with shell access.
    """

    enforce_network_policy = models.BooleanField(
        default=False,
        help_text="Refuse sign-in from outside the configured networks.")
    enforce_network_on_punch = models.BooleanField(
        default=True,
        help_text="Refuse attendance check-in from outside those networks, "
                  "even when general sign-in is unrestricted.")
    max_failed_logins = models.PositiveIntegerField(default=5)
    lockout_minutes = models.PositiveIntegerField(default=15)
    session_idle_minutes = models.PositiveIntegerField(
        default=480, help_text="Sign a token out after this long without use.")
    session_max_hours = models.PositiveIntegerField(
        default=24, help_text="Absolute lifetime of a token, however active.")
    password_min_length = models.PositiveIntegerField(default=8)
    bind_session_to_ip = models.BooleanField(
        default=False,
        help_text="Invalidate a token if it is presented from a new address.")

    class Meta:
        verbose_name = "security settings"
        verbose_name_plural = "security settings"

    def __str__(self):
        return "Security settings"

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    # -- the network decision ----------------------------------------------

    def network_allows(self, address, role_codes, *, for_punch=False):
        """
        (allowed, reason) for an address, given the roles being exercised.

        A policy scoped to a role only constrains holders of that role. If a
        user holds several roles and *any* unscoped policy exists, the unscoped
        set applies to them too. The rule is: collect every policy that applies
        to this person; if none apply, allow; otherwise the address must fall
        inside at least one.
        """
        enforcing = self.enforce_network_policy or (
            for_punch and self.enforce_network_on_punch)
        if not enforcing:
            return True, ""
        if not address:
            return False, "Your network address could not be determined."

        policies = list(NetworkPolicy.objects.filter(is_active=True)
                        .select_related("role"))
        applicable = [p for p in policies
                      if p.role is None or p.role.code in role_codes]
        if not applicable:
            return True, ""

        if any(p.contains(address) for p in applicable):
            return True, ""

        names = ", ".join(sorted({p.name for p in applicable}))
        # Name the action that was actually refused. A punch refused with the
        # words "sign-in" reads as though the session is about to end.
        action = "Checking in or out" if for_punch else "Sign-in"
        return False, (f"{action} from {address} is not permitted. This account "
                       f"is restricted to: {names}.")


# ==========================================================================
# Sign-in attempts and lockout
# ==========================================================================

class LoginAttempt(models.Model):
    """
    Every sign-in, successful or not.

    Failures are counted per email *and* per address, so neither spraying one
    password across many accounts nor hammering one account goes unnoticed. The
    successes are kept too — "when did this account last sign in, and from
    where" is the first question asked after any incident.
    """

    email = models.CharField(max_length=254, db_index=True)
    ip_address = models.CharField(max_length=45, db_index=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    succeeded = models.BooleanField(default=False)
    reason = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "created_at"])]

    def __str__(self):
        verdict = "ok" if self.succeeded else "failed"
        return f"{self.email} {verdict} from {self.ip_address}"

    @classmethod
    def record(cls, request, email, succeeded, reason=""):
        return cls.objects.create(
            email=(email or "").lower()[:254],
            ip_address=client_ip(request)[:45],
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
            succeeded=succeeded, reason=reason[:120])

    @classmethod
    def lockout_remaining(cls, email, settings_row):
        """
        Minutes left on a lockout, or 0.

        The window resets on success: a correct password clears the streak, so
        somebody who mistypes four times and then gets it right is not punished
        an hour later for the next typo.
        """
        if not settings_row.max_failed_logins:
            return 0
        since = timezone.now() - timedelta(minutes=settings_row.lockout_minutes)
        recent = list(cls.objects
                      .filter(email=(email or "").lower(), created_at__gte=since)
                      .order_by("-created_at")
                      .values_list("succeeded", "created_at")[:50])

        streak = []
        for succeeded, at in recent:
            if succeeded:
                break
            streak.append(at)

        if len(streak) < settings_row.max_failed_logins:
            return 0
        unlock_at = streak[0] + timedelta(minutes=settings_row.lockout_minutes)
        remaining = (unlock_at - timezone.now()).total_seconds() / 60
        return max(0, int(remaining) + 1)


# ==========================================================================
# Audit trail
# ==========================================================================

class AuditLog(models.Model):
    """
    Append-only record of anything that changes money, access or identity.

    Deliberately not a generic model-history table. A log that records
    everything is a log nobody reads; this one records the handful of actions
    that would matter in a dispute — who approved what, who changed whose bank
    account, who granted which role, whose attendance was corrected by hand.
    """

    SIGN_IN = "SIGN_IN"
    SIGN_IN_FAILED = "SIGN_IN_FAILED"
    SIGN_OUT = "SIGN_OUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    ROLES_CHANGED = "ROLES_CHANGED"
    USER_CREATED = "USER_CREATED"
    USER_DEACTIVATED = "USER_DEACTIVATED"
    PROFILE_EDITED = "PROFILE_EDITED"
    PROFILE_CHANGE_REQUESTED = "PROFILE_CHANGE_REQUESTED"
    PROFILE_CHANGE_DECIDED = "PROFILE_CHANGE_DECIDED"
    ATTENDANCE_PUNCH = "ATTENDANCE_PUNCH"
    ATTENDANCE_CORRECTED = "ATTENDANCE_CORRECTED"
    TIMEOFF_DECIDED = "TIMEOFF_DECIDED"
    PAYRUN_STATE = "PAYRUN_STATE"
    SECURITY_CHANGED = "SECURITY_CHANGED"
    DATA_IMPORTED = "DATA_IMPORTED"
    BRANDING_CHANGED = "BRANDING_CHANGED"
    WORKFORCE_BULK = "WORKFORCE_BULK"

    ACTIONS = [
        (SIGN_IN, "Signed in"), (SIGN_IN_FAILED, "Sign-in refused"),
        (SIGN_OUT, "Signed out"), (PASSWORD_CHANGED, "Password changed"),
        (ROLES_CHANGED, "Roles changed"), (USER_CREATED, "User created"),
        (USER_DEACTIVATED, "User deactivated"),
        (PROFILE_EDITED, "Profile edited"),
        (PROFILE_CHANGE_REQUESTED, "Profile change requested"),
        (PROFILE_CHANGE_DECIDED, "Profile change decided"),
        (ATTENDANCE_PUNCH, "Attendance punch"),
        (ATTENDANCE_CORRECTED, "Attendance corrected"),
        (TIMEOFF_DECIDED, "Time off decided"),
        (PAYRUN_STATE, "Payrun state change"),
        (SECURITY_CHANGED, "Security settings changed"),
        (DATA_IMPORTED, "Roster imported"),
        (BRANDING_CHANGED, "Branding changed"),
        (WORKFORCE_BULK, "Bulk workforce operation"),
    ]

    actor = models.ForeignKey("accounts.User", on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="audit_entries")
    actor_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=32, choices=ACTIONS, db_index=True)
    summary = models.CharField(max_length=300)
    target_type = models.CharField(max_length=40, blank=True)
    target_id = models.CharField(max_length=40, blank=True)
    ip_address = models.CharField(max_length=45, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action", "created_at"])]

    def __str__(self):
        return f"{self.created_at:%d-%b %H:%M} {self.action} — {self.summary}"

    @classmethod
    def write(cls, request, action, summary, actor=None, target=None):
        """
        Record one entry. Never raises — an audit failure must not take down
        the action being audited, but it must be visible in the server log.
        """
        try:
            user = actor if actor is not None else getattr(request, "user", None)
            if user is not None and not getattr(user, "is_authenticated", False):
                user = None
            return cls.objects.create(
                actor=user,
                actor_email=(getattr(user, "email", "") or "")[:254],
                action=action, summary=summary[:300],
                target_type=type(target).__name__ if target is not None else "",
                target_id=str(getattr(target, "pk", "") or "")[:40],
                ip_address=client_ip(request)[:45] if request is not None else "")
        except Exception as exc:  # pragma: no cover — logging must not break flow
            import logging
            logging.getLogger(__name__).warning("audit write failed: %s", exc)
            return None
