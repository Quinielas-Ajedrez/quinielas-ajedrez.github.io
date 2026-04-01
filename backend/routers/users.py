"""User management endpoints (super-admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, hash_password, require_super_admin
from ..models import User
from ..repository import delete_user, get_user_by_id, list_users, save_user
from ..schemas import UserPasswordSetRequest, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


def _delete_user_if_allowed(
    user_id: int, db: Session, current: User
) -> None:
    if current.id is not None and user_id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    ok = delete_user(db, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")


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


@router.post("/{user_id}/password", response_model=UserResponse)
def set_user_password(
    user_id: int,
    body: UserPasswordSetRequest,
    db: Session = Depends(get_db),
    super_admin=Depends(require_super_admin),
) -> UserResponse:
    """Set a user's login password. Super-admin only."""
    u = get_user_by_id(db, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")

    updated = save_user(
        db,
        User(
            id=u.id,
            name=u.name,
            username=u.username,
            password_hash=hash_password(body.password),
            is_admin=u.is_admin,
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_route(
    user_id: int,
    current: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> None:
    """Remove a user and their predictions. Super-admin only; cannot delete yourself."""
    _delete_user_if_allowed(user_id, db, current)


@router.post("/{user_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
def post_delete_user(
    user_id: int,
    current: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> None:
    """Same as DELETE /{user_id}; for proxies that block DELETE."""
    _delete_user_if_allowed(user_id, db, current)
