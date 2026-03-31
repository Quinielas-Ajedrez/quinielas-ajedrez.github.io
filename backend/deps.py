"""FastAPI dependencies."""

import os
from datetime import datetime, timedelta
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .repository import get_user_by_id

# JWT config - use env var in production
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"

# Site gate - password required before accessing the app
SITE_PASSWORD = os.getenv("SITE_PASSWORD", "quiniela")
GATE_COOKIE_NAME = "quiniela_gate"
# Fallback when cross-site cookies are blocked (e.g. Safari ITP): same JWT as cookie, sent by client.
GATE_HEADER_NAME = "X-Quiniela-Gate"
GATE_COOKIE_MAX_AGE = 60 * 60 * 24  # 24 hours

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_gate_token() -> str:
    """Create a JWT for the site gate (passes password check)."""
    payload = {"gate": True, "exp": datetime.utcnow() + timedelta(seconds=GATE_COOKIE_MAX_AGE)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_gate_token(token: str | None) -> bool:
    """Verify the gate cookie token."""
    if not token:
        return False
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("gate") is True
    except (JWTError, ValueError):
        return False


def check_site_password(password: str) -> bool:
    """Check if the provided password matches the site gate password."""
    return password == SITE_PASSWORD


def decode_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload.get("sub"))
    except (JWTError, ValueError):
        return None


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Require valid auth. Raises 401 if not logged in."""
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user_id = decode_token(creds.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require admin. Raises 403 if not admin or super-admin."""
    if not user.is_admin and not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_super_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require super-admin. Only super-admins can manage other users."""
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super-admin access required",
        )
    return user
