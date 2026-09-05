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

    def __str__(self):
        return self.email

    # ---- role helpers -----------------------------------------------------

    @property
    def role_codes(self):
        return set(self.roles.values_list("code", flat=True))

    def has_role(self, *codes):
        return bool(self.role_codes & set(codes))

    @property
    def is_admin(self):
        return self.is_superuser or self.has_role(Role.ADMIN)

    @property
    def can_manage_hr(self):
        return self.is_admin or self.has_role(
            Role.HR_MANAGER, Role.PAYROLL_USER, Role.PAYROLL_MANAGER)

    @property
    def can_approve_leave(self):
        return self.can_manage_hr

    @property
    def can_run_payroll(self):
        return self.is_admin or self.has_role(
            Role.PAYROLL_USER, Role.PAYROLL_MANAGER)

    @property
    def can_configure_payroll(self):
        """Payroll User gets read-only on structures and rules (PRD §3.2)."""
        return self.is_admin or self.has_role(Role.PAYROLL_MANAGER)
