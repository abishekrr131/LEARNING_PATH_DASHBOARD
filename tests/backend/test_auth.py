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
    assert data["user"]["email"] == "priya_sharma@gmail.com"
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


def test_verified_google_identity_persists_sub_and_profile(client, db_session, monkeypatch):
    """Verifies that a genuine Google ID token processed through id_token.verify_oauth2_token
    saves sub, email, name, and picture_url to the database.
    """
    from google.oauth2 import id_token
    from backend.app.models.core import User

    fake_id_info = {
        "iss": "https://accounts.google.com",
        "sub": "109283746592837465019",
        "email": "verified.aspirant@gmail.com",
        "email_verified": True,
        "name": "Verified Aspirant",
        "picture": "https://lh3.googleusercontent.com/a/custom-avatar=s96-c",
        "aud": settings.GOOGLE_CLIENT_ID,
    }

    # Mock Google's network token verification
    monkeypatch.setattr(
        id_token,
        "verify_oauth2_token",
        lambda token, request, audience: fake_id_info if audience == settings.GOOGLE_CLIENT_ID else None
    )

    resp = client.post(
        "/api/auth/google",
        json={"id_token": "real-signed-google-id-token-jwt"}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["user"]["email"] == "verified.aspirant@gmail.com"
    assert data["user"]["name"] == "Verified Aspirant"
    assert data["user"]["picture_url"] == "https://lh3.googleusercontent.com/a/custom-avatar=s96-c"

    # Verify database persistence
    user_row = db_session.query(User).filter(User.email == "verified.aspirant@gmail.com").first()
    assert user_row is not None
    assert user_row.google_sub == "109283746592837465019"
    assert user_row.name == "Verified Aspirant"
    assert user_row.picture_url == "https://lh3.googleusercontent.com/a/custom-avatar=s96-c"


def test_invalid_google_id_token_returns_401(client, monkeypatch):
    """Rejects malformed, expired, or audience-mismatched Google ID tokens with 401."""
    from google.oauth2 import id_token

    def mock_verify_fail(token, request, audience):
        raise ValueError("Token signature verification failed: invalid key ID")

    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify_fail)

    resp = client.post(
        "/api/auth/google",
        json={"id_token": "forged-or-expired-token"}
    )
    assert resp.status_code == 401
    assert "Google token verification failed" in resp.json()["detail"]

