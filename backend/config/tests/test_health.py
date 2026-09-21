import pytest
from django.urls import reverse
from uuid import UUID


pytestmark = pytest.mark.django_db


def test_health_reports_api_and_database_available(client):
    response = client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response["X-Request-ID"])


def test_request_id_accepts_safe_correlation_value(client):
    response = client.get(reverse("health"), HTTP_X_REQUEST_ID="local-smoke-123")

    assert response["X-Request-ID"] == "local-smoke-123"


def test_request_id_replaces_unsafe_header_value(client):
    response = client.get(reverse("health"), HTTP_X_REQUEST_ID="unsafe value\nforged")

    assert response["X-Request-ID"] != "unsafe value\nforged"
    UUID(response["X-Request-ID"])
