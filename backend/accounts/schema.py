from drf_spectacular.extensions import OpenApiAuthenticationExtension

class CookieJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class="accounts.authentication.CookieJWTAuthentication"
    name="cookieJWT"
    def get_security_definition(self,auto_schema):
        return {"type":"apiKey","in":"cookie","name":"access_token","description":"JWT de acceso enviado en cookie HttpOnly. Las escrituras también requieren X-CSRFToken."}
