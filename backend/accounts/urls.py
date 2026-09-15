from django.urls import path
from .views import ChangePasswordView, CsrfView, LoginView, LogoutView, PasswordResetConfirmView, PasswordResetRequestView, ProfileView, RefreshView, RegisterView, VerifyEmailView

urlpatterns = [
    path("csrf/", CsrfView.as_view()), path("register/", RegisterView.as_view()),
    path("login/", LoginView.as_view()), path("refresh/", RefreshView.as_view()),
    path("logout/", LogoutView.as_view()), path("profile/", ProfileView.as_view()),
    path("change-password/", ChangePasswordView.as_view()), path("password-reset/", PasswordResetRequestView.as_view()),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view()), path("verify-email/", VerifyEmailView.as_view()),
]
