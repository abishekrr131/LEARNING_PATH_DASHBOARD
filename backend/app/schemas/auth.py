from __future__ import annotations
from pydantic import BaseModel, Field


class GoogleAuthIn(BaseModel):
    id_token: str = Field(..., description="Google ID Token obtained from Google Identity Services")


class RefreshTokenIn(BaseModel):
    refresh_token: str = Field(..., description="Valid refresh token")


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    picture_url: str | None = None
    has_completed_onboarding: bool
    target_id: int | None = None
    target_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut
