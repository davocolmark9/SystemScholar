from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

class IsExternalInstitution(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated