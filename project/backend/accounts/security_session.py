"""
Per-token activity, so a session can time out and be listed.

Separate from DRF's `Token` because that table is a third party's and adding
columns to it invites trouble on upgrade. One row per live token; the row is
deleted with the token when the session ends.
"""

from django.db import models
from django.utils import timezone


class SessionActivity(models.Model):
    token_key = models.CharField(max_length=40, primary_key=True)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE,
                             related_name="session_activity")
    ip_address = models.CharField(max_length=45, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-last_used"]
        verbose_name_plural = "session activity"

    def __str__(self):
        return f"{self.user.email} — last used {self.last_used:%d-%b %H:%M}"

    def touch(self, address=""):
        """
        Record use. Written at most once a minute — every authenticated
        request passes through here, and an UPDATE on each of them would turn
        a read-only page into a write-heavy one for no gain.
        """
        now = timezone.now()
        if (now - self.last_used).total_seconds() < 60:
            return
        self.last_used = now
        fields = ["last_used"]
        if address and address != self.ip_address:
            self.ip_address = address[:45]
            fields.append("ip_address")
        self.save(update_fields=fields)
