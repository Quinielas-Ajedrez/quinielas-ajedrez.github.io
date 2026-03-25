"""Tournament endpoints."""

from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db, require_admin, require_super_admin
from ..repository import (
    apply_tournament_patch,
    get_game_prediction_counts_by_game,
    get_table_prediction_for_user,
    get_tournament,
    list_tournaments,
    save_table_prediction,
    save_tournament,
)
from ..schemas import (
    GamePredictionBreakdown,
    TablePredictionCreate,
    TablePredictionGetResponse,
    TablePredictionResponse,
    TournamentImportRequest,
    TournamentListItem,
    TournamentPlayerResponse,
    TournamentPredictionStatisticsResponse,
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
    players_data = [
        TournamentPlayerResponse(id=p.id, name=p.name, name_key=p.name_key)
        for p in t.players
    ]
    return TournamentResponse(
        id=t.id,
        name=t.name,
        rounds=rounds_data,
        points_white_win=t.points_white_win,
        points_black_win=t.points_black_win,
        points_draw=t.points_draw,
        points_table_per_rank=t.points_table_per_rank,
        table_prediction_deadline=t.table_prediction_deadline,
        final_ranking_player_ids=t.final_ranking_player_ids,
        players=players_data,
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
                points_table_per_rank=existing.points_table_per_rank,
                table_prediction_deadline=existing.table_prediction_deadline,
                final_ranking_player_ids=existing.final_ranking_player_ids,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid YAML: {e!s}",
            )
        saved = save_tournament(db, updated)
        return _to_response(saved)

    if body.name is not None:
        updated = replace(existing, name=body.name)
        saved = save_tournament(db, updated)
        return _to_response(saved)

    patch_data = body.model_dump(exclude_unset=True)
    patch_data.pop("yaml_content", None)
    patch_data.pop("name", None)
    if patch_data:
        try:
            saved = apply_tournament_patch(db, tournament_id, patch_data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
        if saved is None:
            raise HTTPException(status_code=404, detail="Tournament not found")
        return _to_response(saved)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Provide name, yaml_content, or fields to update",
    )


@router.post(
    "/{tournament_id}/table-prediction",
    response_model=TablePredictionResponse,
)
def create_table_prediction(
    tournament_id: int,
    body: TablePredictionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> TablePredictionResponse:
    try:
        save_table_prediction(
            db, user.id, tournament_id, body.ranking_player_ids
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    return TablePredictionResponse(ranking_player_ids=body.ranking_player_ids)


@router.get(
    "/{tournament_id}/table-prediction",
    response_model=TablePredictionGetResponse,
)
def read_table_prediction(
    tournament_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> TablePredictionGetResponse:
    t = get_tournament(db, tournament_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    ranking = get_table_prediction_for_user(db, user.id, tournament_id)
    return TablePredictionGetResponse(ranking_player_ids=ranking)


@router.get(
    "/{tournament_id}/prediction-statistics",
    response_model=TournamentPredictionStatisticsResponse,
)
def prediction_statistics(
    tournament_id: int,
    db: Session = Depends(get_db),
    _super=Depends(require_super_admin),
) -> TournamentPredictionStatisticsResponse:
    t = get_tournament(db, tournament_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Tournament not found")
    counts = get_game_prediction_counts_by_game(db, tournament_id)
    games_out: list[GamePredictionBreakdown] = []
    for r in t.rounds:
        for g in r.games:
            if g.is_deleted:
                continue
            c = counts.get(
                g.id,
                {"1-0": 0, "0-1": 0, "1/2-1/2": 0},
            )
            games_out.append(
                GamePredictionBreakdown(
                    game_id=g.id,
                    white_player=g.white_player,
                    black_player=g.black_player,
                    round_name=r.round_name,
                    counts=c,
                )
            )
    return TournamentPredictionStatisticsResponse(games=games_out)
