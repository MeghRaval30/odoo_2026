"""
Token authentication with a lifetime, and a network check on every request.

DRF's stock token never expires. For a system that can move payroll that is not
good enough: a token copied off a laptop in March still works in September. This
subclass adds three things, all driven by the Admin-editable security row —

* an **idle timeout**, so an abandoned session dies on its own;
* an **absolute lifetime**, so even a busy session is re-authenticated daily;
* a **live network check**, so walking off the permitted Wi-Fi ends the session
  rather than merely blocking the next sign-in. Checking the network only at
  sign-in would make the whole control a formality — you would authenticate on
  the office network and then use the token from anywhere.

Optionally the token is also **bound to the address it was issued to**, which
turns a stolen token into a dead one unless the thief is on the same network.
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .security import SecuritySetting, client_ip


class TokenSession:
    """Where a token was last used. One row per token, created on first use."""


class ExpiringTokenAuthentication(TokenAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result

        settings_row = SecuritySetting.load()
        now = timezone.now()

        # -- absolute lifetime ------------------------------------------------
        if settings_row.session_max_hours:
            age = now - token.created
            if age > timedelta(hours=settings_row.session_max_hours):
                token.delete()
                raise AuthenticationFailed(
                    "This session has expired. Please sign in again.")

        # -- idle timeout -----------------------------------------------------
        # `last_used` lives on the session row rather than on the token so that
        # DRF's own table stays untouched and `token.created` keeps meaning
        # "when this session began".
        from .security_session import SessionActivity
        activity, _ = SessionActivity.objects.get_or_create(
            token_key=token.key,
            defaults={"user": user, "ip_address": client_ip(request)[:45]})

        if settings_row.session_idle_minutes:
            idle = now - activity.last_used
            if idle > timedelta(minutes=settings_row.session_idle_minutes):
                activity.delete()
                token.delete()
                raise AuthenticationFailed(
                    "Signed out after a period of inactivity. Please sign in again.")

        # -- address binding --------------------------------------------------
        address = client_ip(request)
        if settings_row.bind_session_to_ip and activity.ip_address and \
                address and address != activity.ip_address:
            activity.delete()
            token.delete()
            raise AuthenticationFailed(
                "This session was opened from a different network. "
                "Please sign in again.")

        # -- the network must still permit this account -----------------------
        allowed, reason = settings_row.network_allows(address, user.role_codes)
        if not allowed:
            raise AuthenticationFailed(reason)

        activity.touch(address)
        return user, token
