"""User management endpoints (super-admin only)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db, require_super_admin
from ..repository import get_user_by_id, list_users, save_user
from ..schemas import UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users_route(
    db: Session = Depends(get_db),
    super_admin=Depends(require_super_admin),
) -> list[UserResponse]:
    """List all users. Super-admin only."""
    users = list_users(db)
    return [
        UserResponse(
            id=u.id,
            name=u.name,
            username=u.username,
            is_admin=u.is_admin,
            is_super_admin=u.is_super_admin,
        )
        for u in users
    ]


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    super_admin=Depends(require_super_admin),
) -> UserResponse:
    """Update a user's admin status. Super-admin only. Cannot change is_super_admin."""
    if body.is_admin is None:
        raise HTTPException(status_code=400, detail="Provide is_admin")

    u = get_user_by_id(db, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Super-admin cannot demote themselves from super-admin (we don't expose that)
    # But they can change is_admin. We only update is_admin.
    from ..models import User

    updated = save_user(
        db,
        User(
            id=u.id,
            name=u.name,
            username=u.username,
            password_hash=u.password_hash,
            is_admin=body.is_admin,
            is_super_admin=u.is_super_admin,
        ),
    )
    return UserResponse(
        id=updated.id,
        name=updated.name,
        username=updated.username,
        is_admin=updated.is_admin,
        is_super_admin=updated.is_super_admin,
    )
