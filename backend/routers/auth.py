"""Auth endpoints."""

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from ..deps import (
    GATE_COOKIE_MAX_AGE,
    GATE_COOKIE_NAME,
    check_site_password,
    create_access_token,
    create_gate_token,
    get_current_user,
    get_db,
    hash_password,
    require_admin,
    verify_gate_token,
    verify_password,
)
from ..models import User
from ..repository import get_user_by_username, save_user
from ..schemas import BootstrapRequest, LoginRequest, TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Site gate (password required before accessing the app) ---


@router.post("/site-gate")
def submit_site_gate(
    body: dict,
    response: Response,
) -> dict:
    """Submit site password. On success, sets httpOnly cookie and returns 200."""
    password = body.get("password", "")
    if not check_site_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
        )
    token = create_gate_token()
    response.set_cookie(
        key=GATE_COOKIE_NAME,
        value=token,
        max_age=GATE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"ok": True}


@router.get("/site-gate")
def check_site_gate(request: Request) -> dict:
    """Check if the gate cookie is valid. Returns 200 if past the gate, 401 otherwise."""
    token = request.cookies.get(GATE_COOKIE_NAME)
    if not verify_gate_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not past site gate",
        )
    return {"ok": True}


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = get_user_by_username(db, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/logout")
def logout() -> dict:
    """Logout (client should discard token). JWT is stateless so no server-side invalidation."""
    return {"message": "Logged out"}


@router.post("/bootstrap", response_model=UserResponse)
def bootstrap_super_admin(
    body: BootstrapRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Promote a user to super-admin. Requires BOOTSTRAP_SECRET env var.
    Use when Shell is unavailable (e.g. Render free tier).
    """
    secret = os.getenv("BOOTSTRAP_SECRET", "")
    if not secret or body.secret != secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing bootstrap secret",
        )
    user = get_user_by_username(db, body.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    updated = save_user(
        db,
        User(
            id=user.id,
            name=user.name,
            username=user.username,
            password_hash=user.password_hash,
            is_admin=True,
            is_super_admin=True,
        ),
    )
    return UserResponse(
        id=updated.id,
        name=updated.name,
        username=updated.username,
        is_admin=updated.is_admin,
        is_super_admin=updated.is_super_admin,
    )


@router.get("/me", response_model=UserResponse)
def me(user=Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
    )


@router.post("/register", response_model=UserResponse)
def register(
    body: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    if get_user_by_username(db, body.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = save_user(
        db,
        User(
            name=body.name,
            username=body.username,
            password_hash=hash_password(body.password),
            is_admin=body.is_admin,
            is_super_admin=False,
        ),
    )
    return UserResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
    )


@router.post("/users", response_model=UserResponse)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> UserResponse:
    """Create a user (admin only)."""
    if get_user_by_username(db, body.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = save_user(
        db,
        User(
            name=body.name,
            username=body.username,
            password_hash=hash_password(body.password),
            is_admin=body.is_admin,
            is_super_admin=False,
        ),
    )
    return UserResponse(
        id=user.id,
        name=user.name,
        username=user.username,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
    )
