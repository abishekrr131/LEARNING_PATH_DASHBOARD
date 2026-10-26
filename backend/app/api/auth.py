from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from backend.app.core.config import settings
from backend.app.core.security import create_access_token, create_refresh_token, decode_token
from backend.app.db.session import get_db
from backend.app.models.core import User, LearnerProfile, CareerTarget
from backend.app.schemas.auth import GoogleAuthIn, RefreshTokenIn, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/google", response_model=TokenResponse)
def google_sign_in(payload: GoogleAuthIn, db: Session = Depends(get_db)):
    """Authenticate via Google ID token.

    Verifies signature, audience, issuer, and expiry.
    Upserts user record and returns JWT access + refresh tokens.
    MOCK_GOOGLE_AUTH is strictly refused if ENV == 'production'.
    """
    token_str = payload.id_token.strip()

    email: str | None = None
    name: str | None = None
    sub: str | None = None
    picture: str | None = None

    # Test harness guard for automated offline tests (strictly refused in production)
    if token_str.startswith("mock-google-token-"):
        if settings.ENV.lower() == "production":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mock Google authentication is strictly prohibited in production.",
            )
        raw_id = token_str.replace("mock-google-token-", "").strip() or "learner@gmail.com"
        email = raw_id if "@" in raw_id else f"{raw_id}@gmail.com"
        name = email.split("@")[0].replace(".", " ").replace("_", " ").title()
        sub = f"google-sub-{abs(hash(email)) % 100000000000000000000:021d}"
        picture = f"https://api.dicebear.com/7.x/bottts/svg?seed={email}"
    else:
        # Standard Google OAuth2 Token Verification
        try:
            id_info = id_token.verify_oauth2_token(
                token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
            email = id_info.get("email")
            name = id_info.get("name", email.split("@")[0] if email else "Google Learner")
            sub = id_info.get("sub")
            picture = id_info.get("picture")

            if not email or not sub:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Google ID token does not contain a verified email address or subject identifier.",
                )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google token verification failed: {str(e)}",
            )

    # Optional ALLOWED_EMAILS restriction
    if settings.ALLOWED_EMAILS:
        allowed = [e.strip().lower() for e in settings.ALLOWED_EMAILS.split(",") if e.strip()]
        if allowed and email.lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Google account '{email}' is not authorized to access this deployment.",
            )

    # Upsert user record with google_sub
    user = db.query(User).filter((User.google_sub == sub) | (User.email == email)).first()
    if not user:
        user = User(
            email=email,
            name=name,
            google_sub=sub,
            picture_url=picture,
            role="learner",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = name
        user.picture_url = picture
        if sub:
            user.google_sub = sub
        db.commit()
        db.refresh(user)

    # Check onboarding status
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == user.id).first()
    has_completed_onboarding = bool(profile and profile.target_id)
    target_id = profile.target_id if profile else None
    target_name = None
    if target_id:
        target = db.query(CareerTarget).filter(CareerTarget.id == target_id).first()
        target_name = target.name if target else None

    # Issue session tokens
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    user_out = UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        picture_url=user.picture_url,
        has_completed_onboarding=has_completed_onboarding,
        target_id=target_id,
        target_name=target_name,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user_out,
    )


@router.post("/refresh", response_model=dict)
def refresh_token(payload: RefreshTokenIn, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new short-lived access token."""
    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided token is not a refresh token",
        )

    user_id = decoded.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    new_access_token = create_access_token(
        {"sub": str(user.id), "email": user.email, "role": user.role}
    )
    return {"access_token": new_access_token, "token_type": "bearer"}
