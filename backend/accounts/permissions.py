from rest_framework.permissions import BasePermission

from .models import User


class _RolePermission(BasePermission):
    roles = ()

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role in self.roles)


class IsCustomer(_RolePermission):
    roles = (User.Role.CUSTOMER,)


class IsTechnician(_RolePermission):
    roles = (User.Role.TECHNICIAN,)


class IsManager(_RolePermission):
    roles = (User.Role.MANAGER,)
