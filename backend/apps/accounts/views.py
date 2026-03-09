"""Views for accounts app."""

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Role, WarehouseStaff
from .serializers import (
    ChangePasswordSerializer,
    ProfileSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
    WarehouseStaffSerializer,
)

User = get_user_model()


class IsAdminOrManager(permissions.BasePermission):
    """Allow access only to admin or manager users."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_manager


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for user accounts.
    Restricted to admin and manager roles.
    """

    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManager]
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["created_at", "email", "first_name"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def perform_destroy(self, instance):
        # Soft delete: deactivate instead of removing
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Reactivate a deactivated user."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=["is_active"])
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        """Admin-initiated password reset."""
        user = self.get_object()
        new_password = request.data.get("new_password")
        if not new_password or len(new_password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save()
        return Response({"status": "Password has been reset."})


class ProfileView(generics.RetrieveUpdateAPIView):
    """View and update the current user's profile."""

    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """Change the current user's password."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save()
        return Response(
            {"status": "Password updated successfully."},
            status=status.HTTP_200_OK,
        )


class RoleViewSet(viewsets.ModelViewSet):
    """CRUD operations for custom roles."""

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManager]
    search_fields = ["name"]


class WarehouseStaffViewSet(viewsets.ModelViewSet):
    """Manage warehouse staff assignments."""

    queryset = WarehouseStaff.objects.select_related(
        "user", "warehouse", "custom_role"
    ).all()
    serializer_class = WarehouseStaffSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrManager]
    filterset_fields = ["warehouse", "user", "is_active"]
    search_fields = ["user__email", "user__first_name", "user__last_name"]

    @action(detail=False, methods=["get"])
    def my_assignments(self, request):
        """List the current user's warehouse assignments."""
        assignments = self.queryset.filter(user=request.user, is_active=True)
        serializer = self.get_serializer(assignments, many=True)
        return Response(serializer.data)
