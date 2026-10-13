from __future__ import annotations
import datetime as dt
from typing import Any
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.session import get_db
from backend.app.models.core import User

security_scheme = HTTPBearer(auto_error=False)


def create_access_token(data: dict[str, Any], expires_delta: dt.timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = dt.datetime.now(dt.timezone.utc) + (
        expires_delta or dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    secret = settings.SECRET_KEY or settings.JWT_SECRET
    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any], expires_delta: dt.timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = dt.datetime.now(dt.timezone.utc) + (
        expires_delta or dt.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    secret = settings.SECRET_KEY or settings.JWT_SECRET
    return jwt.encode(to_encode, secret, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        secret = settings.SECRET_KEY or settings.JWT_SECRET
        payload = jwt.decode(token, secret, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    auth: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(auth.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
