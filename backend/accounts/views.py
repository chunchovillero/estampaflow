from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.middleware.csrf import get_token
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .authentication import clear_auth_cookies, set_auth_cookies
from .serializers import ChangePasswordSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer

class CsrfView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def get(self, request):
        return Response({"csrfToken": get_token(request)})

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        user.email_user("Verifica tu correo de EstampaFlow", f"Verifica tu correo aquí: /verificar-correo/{uid}/{token}")
        refresh = RefreshToken.for_user(user)
        response = Response({"user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)
        set_auth_cookies(response, refresh.access_token, refresh)
        return response

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def post(self, request):
        user = authenticate(request, email=request.data.get("email", "").lower().strip(), password=request.data.get("password"))
        if not user or not user.is_active:
            return Response({"error": {"status": 401, "details": "Correo o contraseña incorrectos."}}, status=401)
        membership = user.memberships.select_related("business").filter(is_active=True).first()
        if membership and membership.business.status != "active":
            return Response({"error": {"status": 403, "details": "La empresa no está activa."}}, status=403)
        refresh = RefreshToken.for_user(user)
        response = Response({"user": UserSerializer(user).data})
        set_auth_cookies(response, refresh.access_token, refresh)
        return response

class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def post(self, request):
        token = request.COOKIES.get("refresh_token")
        if not token:
            return Response({"error": {"status": 401, "details": "Sesión no disponible."}}, status=401)
        try:
            refresh = RefreshToken(token)
            response = Response({"detail": "Sesión renovada."})
            set_auth_cookies(response, refresh.access_token)
            return response
        except Exception:
            return Response({"error": {"status": 401, "details": "Sesión vencida."}}, status=401)

class LogoutView(APIView):
    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_auth_cookies(response)
        return response

class ProfileView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)
    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)

class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Contraseña actualizada."})

class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def post(self, request):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.filter(email=request.data.get("email", "").lower().strip()).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            user.email_user("Recupera tu contraseña de EstampaFlow", f"Usa este enlace para continuar: /restablecer/{uid}/{token}")
        return Response({"detail": "Si el correo existe, enviaremos instrucciones para recuperar la contraseña."})

class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def post(self, request):
        from django.contrib.auth import get_user_model, password_validation
        try:
            user = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(request.data.get("uid", ""))))
        except (ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
            user = None
        if not user or not default_token_generator.check_token(user, request.data.get("token", "")):
            return Response({"error": {"status": 400, "details": "El enlace no es válido o venció."}}, status=400)
        try:
            password_validation.validate_password(request.data.get("password", ""), user)
        except Exception as exc:
            details = getattr(exc, "messages", ["La contraseña no cumple los requisitos."])
            return Response({"error": {"status": 400, "details": {"password": details}}}, status=400)
        user.set_password(request.data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Contraseña restablecida correctamente."})

class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    def post(self, request):
        from django.contrib.auth import get_user_model
        try:
            user = get_user_model().objects.get(pk=force_str(urlsafe_base64_decode(request.data.get("uid", ""))))
        except (ValueError, TypeError, OverflowError, get_user_model().DoesNotExist):
            user = None
        if not user or not default_token_generator.check_token(user, request.data.get("token", "")):
            return Response({"error": {"status": 400, "details": "El enlace no es válido o venció."}}, status=400)
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        return Response({"detail": "Correo verificado correctamente."})
