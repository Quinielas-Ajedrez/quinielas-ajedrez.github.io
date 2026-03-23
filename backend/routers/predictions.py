"""Prediction endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..repository import (
    get_game_with_round,
    get_tournament,
    get_user_predictions_for_round,
    save_prediction,
)
from ..schemas import PredictionCreate, PredictionResponse

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.post("", response_model=PredictionResponse)
def create_prediction(
    body: PredictionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> PredictionResponse:
    pair = get_game_with_round(db, body.game_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Game not found")

    game, round_obj = pair
    if game.is_deleted:
        raise HTTPException(status_code=404, detail="Game not found")

    if datetime.utcnow() > round_obj.prediction_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Prediction deadline has passed",
        )

    pred = save_prediction(db, user.id, body.game_id, body.predicted_result)
    return PredictionResponse(
        id=pred.id,
        user_id=pred.user_id,
        game_id=pred.game_id,
        predicted_result=pred.predicted_result,
    )


@router.get("", response_model=list[PredictionResponse])
def list_my_predictions(
    round_id: int | None = None,
    tournament_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[PredictionResponse]:
    if round_id is not None:
        preds = get_user_predictions_for_round(db, round_id, user.id)
    elif tournament_id is not None:
        t = get_tournament(db, tournament_id)
        if t is None:
            raise HTTPException(status_code=404, detail="Tournament not found")
        preds = []
        for r in t.rounds:
            preds.extend(get_user_predictions_for_round(db, r.id, user.id))
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide round_id or tournament_id",
        )

    return [
        PredictionResponse(
            id=p.id,
            user_id=p.user_id,
            game_id=p.game_id,
            predicted_result=p.predicted_result,
        )
        for p in preds
    ]
