import pytest
from backend.app.core.config import settings


def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "palp-api"


def test_google_mock_auth_flow(client):
    settings.ENV = "development"
    settings.MOCK_GOOGLE_AUTH = True

    response = client.post(
        "/api/auth/google",
        json={"id_token": "mock-google-token-priya_sharma"}
    )
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "priya_sharma@test.palp.internal"
    assert data["user"]["name"] == "Priya Sharma"
    assert data["user"]["has_completed_onboarding"] is False


def test_production_guard_refuses_mock_google_auth(client):
    original_env = settings.ENV
    try:
        settings.ENV = "production"
        response = client.post(
            "/api/auth/google",
            json={"id_token": "mock-google-token-attacker"}
        )
        assert response.status_code == 403
        assert "Mock Google authentication is strictly prohibited in production" in response.json()["detail"]
    finally:
        settings.ENV = original_env


def test_refresh_token_flow(client):
    # First sign in to obtain tokens
    auth_resp = client.post(
        "/api/auth/google",
        json={"id_token": "mock-google-token-refresh_tester"}
    )
    assert auth_resp.status_code == 200
    refresh_token = auth_resp.json()["refresh_token"]

    # Exchange refresh token
    refresh_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()
    assert refresh_resp.json()["token_type"] == "bearer"
