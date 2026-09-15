from rest_framework.permissions import BasePermission

def get_membership(user):
    if not user or not user.is_authenticated:
        return None
    return user.memberships.select_related("business").filter(is_active=True).first()

class HasActiveBusiness(BasePermission):
    message = "No tienes una empresa activa asociada."
    def has_permission(self, request, view):
        membership = get_membership(request.user)
        return bool(membership and membership.business.status == "active")

class IsBusinessOwner(HasActiveBusiness):
    message = "Solo el propietario puede realizar esta acción."
    def has_permission(self, request, view):
        membership = get_membership(request.user)
        return bool(membership and membership.business.status == "active" and membership.role == "owner")

