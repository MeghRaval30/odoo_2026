"""
User accounts and roles.

Accounts are separate entities from Employee records but linked one-to-one
(PRD-3.3). An Employee may exist with no account; an account requires an
employee link. Users cannot modify their own roles (PRD-3.2).
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from core.models import TimeStampedModel


class Role(models.Model):
    """The five personas from PRD §3.1."""

    EMPLOYEE = "EMPLOYEE"
    HR_MANAGER = "HR_MANAGER"
    PAYROLL_USER = "PAYROLL_USER"
    PAYROLL_MANAGER = "PAYROLL_MANAGER"
    ADMIN = "ADMIN"

    CHOICES = [
        (EMPLOYEE, "Employee"),
        (HR_MANAGER, "HR Manager"),
        (PAYROLL_USER, "HR Payroll User"),
        (PAYROLL_MANAGER, "HR Payroll Manager"),
        (ADMIN, "Admin"),
    ]

    code = models.CharField(max_length=20, choices=CHOICES, unique=True)
    name = models.CharField(max_length=60)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        user = self.create_user(email, password, **extra)
        admin_role, _ = Role.objects.get_or_create(
            code=Role.ADMIN, defaults={"name": "Admin"})
        user.roles.add(admin_role)
        return user


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    email = models.EmailField(unique=True)
    employee = models.OneToOneField(
        "employees.Employee", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="user_account")
    roles = models.ManyToManyField(Role, blank=True, related_name="users")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._capability_cache = None

    def __str__(self):
        return self.email

    def refresh_capabilities(self):
        """Drop the cache — call after changing this user's roles."""
        self._capability_cache = None

    # ---- role helpers -----------------------------------------------------

    @property
    def role_codes(self):
        return set(self.roles.values_list("code", flat=True))

    def has_role(self, *codes):
        return bool(self.role_codes & set(codes))

    @property
    def capabilities(self):
        """
        Everything this account may do — the union over every role it holds.

        A user may hold several roles (the mockup's access note says so
        explicitly), so this is a union and never a "highest role wins" lookup:
        HR Manager + Payroll User has to behave as the sum of both.

        Cached per instance because permission classes ask repeatedly within one
        request, and each miss is a query.
        """
        from .capabilities import capabilities_for
        if self._capability_cache is None:
            codes = self.role_codes
            if self.is_superuser:
                codes = codes | {Role.ADMIN}
            self._capability_cache = capabilities_for(codes)
        return self._capability_cache

    def can(self, *capabilities):
        """True if the account holds *any* of the capabilities named."""
        return bool(self.capabilities.intersection(capabilities))

    # ---- legacy shorthands ------------------------------------------------
    # Kept because the permission classes and the existing suite read them.
    # Each is now a view onto the capability matrix rather than its own copy of
    # the rules, so there is still exactly one place a role is defined.

    @property
    def is_admin(self):
        from . import capabilities as caps
        return self.can(caps.USER_MANAGE)

    @property
    def can_manage_hr(self):
        from . import capabilities as caps
        return self.can(caps.EMPLOYEE_WRITE)

    @property
    def can_approve_leave(self):
        from . import capabilities as caps
        return self.can(caps.TIMEOFF_APPROVE)

    @property
    def can_run_payroll(self):
        from . import capabilities as caps
        return self.can(caps.PAYRUN_WRITE)

    @property
    def can_configure_payroll(self):
        """Payroll User gets read-only on structures and rules (PRD §3.2)."""
        from . import capabilities as caps
        return self.can(caps.SALARY_CONFIG_WRITE)


# ==========================================================================
# Security and self-service models
# ==========================================================================
#
# Defined in their own modules to keep this file about identity, and re-exported
# here so `accounts.models` stays the single import path Django and the rest of
# the codebase expect.

from .security import (  # noqa: E402,F401  (import position is deliberate)
    AuditLog, LoginAttempt, NetworkPolicy, SecuritySetting, client_ip,
)
from .selfservice import (  # noqa: E402,F401
    APPROVAL_FIELDS, DIRECT_FIELDS, READ_ONLY_FIELDS, SENSITIVE_FIELDS,
    ProfileChangeRequest,
)
