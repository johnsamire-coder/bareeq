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


class IsManagerOrSupervisor(_RolePermission):
    roles = (User.Role.MANAGER, User.Role.SUPERVISOR)


def zone_ids_of(user):
    """None = every zone (manager); else the supervisor's zones."""
    if user.role == User.Role.MANAGER:
        return None
    profile = getattr(user, "supervisor_profile", None)
    return list(profile.zones.values_list("id", flat=True)) if profile else []


def limit_to_zones(qs, user, field="zone"):
    ids = zone_ids_of(user)
    return qs if ids is None else qs.filter(**{f"{field}__in": ids})
