"""Tournament endpoints."""

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db, require_admin
from ..repository import (
    get_tournament,
    list_tournaments,
    patch_tournament_scoring,
    save_tournament,
)
from ..schemas import (
    TournamentImportRequest,
    TournamentListItem,
    TournamentResponse,
    TournamentUpdateRequest,
)
from ..yaml_parser import parse_tournament_yaml

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def _to_response(t):
    rounds_data = []
    for r in t.rounds:
        games_data = [
            {
                "id": g.id,
                "white_player": g.white_player,
                "black_player": g.black_player,
                "white_rating": g.white_rating,
                "black_rating": g.black_rating,
                "result": g.result,
                "is_deleted": g.is_deleted,
            }
            for g in r.games
            if not g.is_deleted
        ]
        rounds_data.append(
            {
                "id": r.id,
                "round_number": r.round_number,
                "round_name": r.round_name,
                "prediction_deadline": r.prediction_deadline,
                "games": games_data,
            }
        )
    return TournamentResponse(
        id=t.id,
        name=t.name,
        rounds=rounds_data,
        points_white_win=t.points_white_win,
        points_black_win=t.points_black_win,
        points_draw=t.points_draw,
    )


@router.get("", response_model=list[TournamentListItem])
def list_tournaments_route(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[TournamentListItem]:
    tournaments = list_tournaments(db)
    return [TournamentListItem(id=t.id, name=t.name) for t in tournaments]


@router.get("/{tournament_id}", response_model=TournamentResponse)
def get_tournament_route(
    tournament_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> TournamentResponse:
    t = get_tournament(db, tournament_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return _to_response(t)


@router.post("/import", response_model=TournamentResponse)
def import_tournament(
    body: TournamentImportRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> TournamentResponse:
    try:
        tournament = parse_tournament_yaml(body.yaml_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid YAML: {e!s}",
        )
    saved = save_tournament(db, tournament)
    return _to_response(saved)


@router.put("/{tournament_id}", response_model=TournamentResponse)
def update_tournament(
    tournament_id: int,
    body: TournamentUpdateRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> TournamentResponse:
    existing = get_tournament(db, tournament_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Tournament not found")

    updated = existing

    if body.yaml_content is not None:
        try:
            parsed = parse_tournament_yaml(body.yaml_content)
            from ..models import Tournament

            updated = Tournament(
                id=tournament_id,
                name=parsed.name,
                rounds=parsed.rounds,
                points_white_win=existing.points_white_win,
                points_black_win=existing.points_black_win,
                points_draw=existing.points_draw,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML: {e!s}",
            )

    if body.name is not None:
        updated = replace(updated, name=body.name)

    if body.points_white_win is not None:
        updated = replace(updated, points_white_win=body.points_white_win)
    if body.points_black_win is not None:
        updated = replace(updated, points_black_win=body.points_black_win)
    if body.points_draw is not None:
        updated = replace(updated, points_draw=body.points_draw)

    if body.yaml_content is not None or body.name is not None:
        saved = save_tournament(db, updated)
        return _to_response(saved)

    if (
        body.points_white_win is not None
        or body.points_black_win is not None
        or body.points_draw is not None
    ):
        saved = patch_tournament_scoring(
            db,
            tournament_id,
            points_white_win=body.points_white_win,
            points_black_win=body.points_black_win,
            points_draw=body.points_draw,
        )
        if saved is None:
            raise HTTPException(status_code=404, detail="Tournament not found")
        return _to_response(saved)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide name, yaml_content, or scoring fields",
    )
