import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

def test_register_creates_owner_and_business():
    client = APIClient()
    response = client.post("/api/v1/auth/register/", {"business_name": "Tinta Sur", "first_name": "Ana", "last_name": "Pérez", "email": "ana@example.cl", "password": "Marea-Violeta-4821"}, format="json")
    assert response.status_code == 201
    user = get_user_model().objects.get(email="ana@example.cl")
    membership = user.memberships.select_related("business").get()
    assert membership.role == "owner"
    assert membership.business.name == "Tinta Sur"
    assert "access_token" in response.cookies and response.cookies["access_token"]["httponly"]

def test_login_and_profile():
    user = get_user_model().objects.create_user(username="ana@example.cl", email="ana@example.cl", password="Marea-Violeta-4821")
    client = APIClient()
    response = client.post("/api/v1/auth/login/", {"email": user.email, "password": "Marea-Violeta-4821"}, format="json")
    assert response.status_code == 200
    client.cookies = response.cookies
    assert client.get("/api/v1/auth/profile/").status_code == 200

def test_invalid_login_does_not_reveal_account():
    response = APIClient().post("/api/v1/auth/login/", {"email": "nadie@example.cl", "password": "incorrecta"}, format="json")
    assert response.status_code == 401
    assert response.data["error"]["details"] == "Correo o contraseña incorrectos."

def test_password_reset_confirm_changes_password():
    user = get_user_model().objects.create_user(username="ana@example.cl", email="ana@example.cl", password="Marea-Violeta-4821")
    response = APIClient().post("/api/v1/auth/password-reset/confirm/", {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": default_token_generator.make_token(user), "password": "Nueva-Marea-7392"}, format="json")
    user.refresh_from_db()
    assert response.status_code == 200
    assert user.check_password("Nueva-Marea-7392")

def test_email_verification_marks_user_as_verified():
    user = get_user_model().objects.create_user(username="ana@example.cl", email="ana@example.cl", password="Marea-Violeta-4821")
    response = APIClient().post("/api/v1/auth/verify-email/", {"uid": urlsafe_base64_encode(force_bytes(user.pk)), "token": default_token_generator.make_token(user)}, format="json")
    user.refresh_from_db()
    assert response.status_code == 200
    assert user.email_verified is True
