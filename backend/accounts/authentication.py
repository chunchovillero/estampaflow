from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication

class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        header = self.get_header(request)
        raw_token = self.get_raw_token(header) if header else request.COOKIES.get("access_token")
        if raw_token is None:
            return None
        if not header and request.method not in ("GET", "HEAD", "OPTIONS"):
            check = CSRFCheck(lambda req: None)
            check.process_request(request)
            reason = check.process_view(request, None, (), {})
            if reason:
                raise PermissionDenied(f"Falló la validación CSRF: {reason}")
        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token

def set_auth_cookies(response, access, refresh=None):
    common = {"httponly": True, "secure": settings.JWT_COOKIE_SECURE, "samesite": "Lax", "path": "/"}
    response.set_cookie("access_token", str(access), max_age=900, **common)
    if refresh is not None:
        response.set_cookie("refresh_token", str(refresh), max_age=604800, **common)

def clear_auth_cookies(response):
    response.delete_cookie("access_token", path="/", samesite="Lax")
    response.delete_cookie("refresh_token", path="/", samesite="Lax")

