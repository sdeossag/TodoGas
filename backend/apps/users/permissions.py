from rest_framework.permissions import BasePermission

from .models import User


class IsAdmin(BasePermission):
    """Solo usuarios con rol ADMIN."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.ADMIN)


class IsAdminOrSup(BasePermission):
    """ADMIN o SUP (supervisor)."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.SUP)
        )


class IsTechnician(BasePermission):
    """Solo técnicos (TEC)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.TEC)


class IsAdminOrSupOrTec(BasePermission):
    """ADMIN, SUP o TEC — excluye CLI."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and request.user.role in (User.Role.ADMIN, User.Role.SUP, User.Role.TEC)
        )


class IsClient(BasePermission):
    """Solo clientes externos (CLI)."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == User.Role.CLI)


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level: el propio usuario o un ADMIN.
    Usar con get_object() en vistas de detalle.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == User.Role.ADMIN:
            return True
        return obj == request.user
