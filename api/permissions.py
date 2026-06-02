from rest_framework import permissions
from rest_framework_simplejwt.authentication import JWTAuthentication

class IsExternalInstitution(permissions.BasePermission):
    """
    Custom permission to only allow external institutions with valid JWT.
    """
    def has_permission(self, request, view):
        # Check if request has valid JWT authentication
        auth = JWTAuthentication()
        try:
            auth_result = auth.authenticate(request)
            if auth_result is not None:
                request.user, request.auth = auth_result
                return True
        except Exception:
            pass
        return False
