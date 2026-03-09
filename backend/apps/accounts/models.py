"""User, Role, and WarehouseStaff models for WarehouseIQ."""

import uuid

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager that uses email as the unique identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model using email as the primary identifier."""

    class RoleChoices(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Warehouse Manager"
        STAFF = "staff", "Warehouse Staff"
        VIEWER = "viewer", "Viewer"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None
    email = models.EmailField("email address", unique=True, db_index=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.STAFF,
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_admin(self):
        return self.role == self.RoleChoices.ADMIN or self.is_superuser

    @property
    def is_manager(self):
        return self.role in (self.RoleChoices.ADMIN, self.RoleChoices.MANAGER)


class Role(models.Model):
    """
    Custom roles with granular permissions beyond the basic role choices.
    Allows warehouse-specific permission sets.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    can_manage_inventory = models.BooleanField(default=False)
    can_receive_stock = models.BooleanField(default=False)
    can_pick_orders = models.BooleanField(default=False)
    can_ship_orders = models.BooleanField(default=False)
    can_manage_warehouses = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    can_manage_settings = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class WarehouseStaff(models.Model):
    """
    Associates a user with a specific warehouse and role.
    A user can be staff at multiple warehouses with different roles.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="warehouse_assignments",
    )
    warehouse = models.ForeignKey(
        "warehouses.Warehouse",
        on_delete=models.CASCADE,
        related_name="staff_assignments",
    )
    custom_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_members",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the user's primary warehouse assignment.",
    )
    assigned_zones = models.ManyToManyField(
        "warehouses.Zone",
        blank=True,
        related_name="assigned_staff",
        help_text="Zones this staff member is assigned to work in.",
    )
    started_at = models.DateField(auto_now_add=True)
    ended_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "warehouse")
        ordering = ["-created_at"]
        verbose_name = "Warehouse Staff"
        verbose_name_plural = "Warehouse Staff"

    def __str__(self):
        return f"{self.user.full_name} @ {self.warehouse.name}"
