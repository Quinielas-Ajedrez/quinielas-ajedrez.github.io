"""Admin endpoints for games and rounds."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, require_admin
from ..repository import (
    get_round_by_id,
    soft_delete_game,
    update_game_result,
    update_round,
)
from ..schemas import GameUpdateRequest, RoundUpdateRequest

router = APIRouter(tags=["admin"])


@router.patch("/games/{game_id}")
def patch_game(
    game_id: int,
    body: GameUpdateRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    if body.result is not None:
        updated = update_game_result(db, game_id, body.result)
        if updated is None:
            raise HTTPException(status_code=404, detail="Game not found")
        return {"id": updated.id, "result": updated.result}
    if body.is_deleted is True:
        ok = soft_delete_game(db, game_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Game not found")
        return {"id": game_id, "is_deleted": True}
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide result or is_deleted=True",
    )


@router.patch("/rounds/{round_id}")
def patch_round(
    round_id: int,
    body: RoundUpdateRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> dict:
    updated = update_round(
        db,
        round_id,
        round_name=body.round_name,
        prediction_deadline=body.prediction_deadline,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Round not found")
    return {
        "id": updated.id,
        "round_name": updated.round_name,
        "prediction_deadline": updated.prediction_deadline,
    }
