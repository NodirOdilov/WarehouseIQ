"""Serializers for accounts app."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Role, WarehouseStaff

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Full user serializer for admin/profile views."""

    full_name = serializers.ReadOnlyField()
    warehouse_assignments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "avatar",
            "is_active",
            "warehouse_assignments_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_warehouse_assignments_count(self, obj):
        return obj.warehouse_assignments.filter(is_active=True).count()


class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new users."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "password",
            "password_confirm",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing users."""

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "phone",
            "role",
            "avatar",
            "is_active",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change."""

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."}
            )
        return attrs


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for custom roles."""

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "can_manage_inventory",
            "can_receive_stock",
            "can_pick_orders",
            "can_ship_orders",
            "can_manage_warehouses",
            "can_view_reports",
            "can_manage_users",
            "can_manage_settings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class WarehouseStaffSerializer(serializers.ModelSerializer):
    """Serializer for warehouse staff assignments."""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    role_name = serializers.CharField(
        source="custom_role.name", read_only=True, default=None
    )

    class Meta:
        model = WarehouseStaff
        fields = [
            "id",
            "user",
            "user_name",
            "user_email",
            "warehouse",
            "warehouse_name",
            "custom_role",
            "role_name",
            "is_primary",
            "assigned_zones",
            "started_at",
            "ended_at",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "started_at", "created_at", "updated_at"]


class ProfileSerializer(serializers.ModelSerializer):
    """Serializer for the current user's profile."""

    full_name = serializers.ReadOnlyField()
    warehouses = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "role",
            "avatar",
            "warehouses",
            "created_at",
        ]
        read_only_fields = ["id", "email", "role", "created_at"]

    def get_warehouses(self, obj):
        assignments = obj.warehouse_assignments.filter(is_active=True).select_related(
            "warehouse"
        )
        return [
            {
                "id": str(a.warehouse.id),
                "name": a.warehouse.name,
                "is_primary": a.is_primary,
            }
            for a in assignments
        ]
