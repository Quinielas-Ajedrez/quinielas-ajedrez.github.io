"""Leaderboard endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..schemas import LeaderboardEntry, LeaderboardResponse
from ..evaluator import Evaluator
from ..repository import get_predictions_for_tournament, get_tournament, get_user_by_id

router = APIRouter(prefix="/tournaments", tags=["leaderboard"])


@router.get("/{tournament_id}/leaderboard", response_model=LeaderboardResponse)
def get_leaderboard(
    tournament_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> LeaderboardResponse:
    """Get leaderboard for a tournament using Evaluator scoring."""
    t = get_tournament(db, tournament_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    game_results = {}
    for r in t.rounds:
        for g in r.games:
            if not g.is_deleted:
                game_results[g.id] = g.result

    predictions = get_predictions_for_tournament(db, tournament_id)
    evaluator = Evaluator()
    scores = evaluator.compute_scores(
        predictions,
        game_results,
        points_white_win=t.points_white_win,
        points_black_win=t.points_black_win,
        points_draw=t.points_draw,
    )

    entries = []
    for uid, points in sorted(scores.items(), key=lambda x: -x[1]):
        u = get_user_by_id(db, uid)
        if u:
            entries.append(
                LeaderboardEntry(
                    user_id=u.id,
                    username=u.username,
                    name=u.name,
                    points=points,
                )
            )

    return LeaderboardResponse(entries=entries)
