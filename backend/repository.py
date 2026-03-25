"""
Repository layer: converts between dataclasses and ORM, provides persistence operations.
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Literal, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .database import (
    GameModel,
    PredictionModel,
    RoundModel,
    SessionLocal,
    TablePredictionModel,
    TournamentModel,
    TournamentPlayerModel,
    UserModel,
    init_db,
)
from .models import Game, Prediction, Round, Tournament, TournamentPlayer, User

GameResult = Literal["1-0", "0-1", "1/2-1/2"]


def normalize_player_name(name: str) -> str:
    """Lowercase, trim, collapse internal whitespace for deduplication."""
    return " ".join(name.strip().lower().split())


# --- Conversion: ORM -> dataclass ---


def _game_to_dataclass(m: GameModel) -> Game:
    return Game(
        id=m.id,
        white_player=m.white_player,
        black_player=m.black_player,
        white_rating=m.white_rating,
        black_rating=m.black_rating,
        result=m.result,
        is_deleted=m.is_deleted,
        deleted_at=m.deleted_at,
    )


def _round_to_dataclass(m: RoundModel) -> Round:
    games = [_game_to_dataclass(g) for g in m.games]
    return Round(
        id=m.id,
        round_number=m.round_number,
        round_name=m.round_name,
        prediction_deadline=m.prediction_deadline,
        games=games,
    )


def _player_to_dataclass(m: TournamentPlayerModel) -> TournamentPlayer:
    return TournamentPlayer(id=m.id, name=m.name, name_key=m.name_key)


def _tournament_to_dataclass(m: TournamentModel) -> Tournament:
    rounds = [_round_to_dataclass(r) for r in m.rounds]
    players = sorted(
        [_player_to_dataclass(p) for p in m.players],
        key=lambda p: p.name_key,
    )
    fr = getattr(m, "final_ranking_player_ids", None)
    final_ids = list(fr) if fr else None
    return Tournament(
        id=m.id,
        name=m.name,
        rounds=rounds,
        points_white_win=getattr(m, "points_white_win", 1) or 1,
        points_black_win=getattr(m, "points_black_win", 1) or 1,
        points_draw=getattr(m, "points_draw", 1) or 1,
        points_table_per_rank=getattr(m, "points_table_per_rank", 1) or 1,
        table_prediction_deadline=getattr(m, "table_prediction_deadline", None),
        final_ranking_player_ids=final_ids,
        players=players,
    )


def _user_to_dataclass(m: UserModel) -> User:
    return User(
        id=m.id,
        name=m.name,
        username=m.username,
        password_hash=m.password_hash,
        is_admin=m.is_admin,
        is_super_admin=getattr(m, "is_super_admin", False),
    )


def _prediction_to_dataclass(m: PredictionModel) -> Prediction:
    return Prediction(
        id=m.id,
        user_id=m.user_id,
        game_id=m.game_id,
        predicted_result=m.predicted_result,
    )


# --- Conversion: dataclass -> ORM ---


def _game_to_model(game: Game, round_id: int) -> GameModel:
    return GameModel(
        id=game.id,
        round_id=round_id,
        white_player=game.white_player,
        black_player=game.black_player,
        white_rating=game.white_rating,
        black_rating=game.black_rating,
        result=game.result,
        is_deleted=game.is_deleted,
        deleted_at=game.deleted_at,
    )


def _round_to_model(round_obj: Round, tournament_id: int) -> RoundModel:
    round_model = RoundModel(
        id=round_obj.id,
        tournament_id=tournament_id,
        round_number=round_obj.round_number,
        round_name=round_obj.round_name,
        prediction_deadline=round_obj.prediction_deadline,
    )
    round_model.games = [
        _game_to_model(g, 0) for g in round_obj.games
    ]  # round_id set when round is persisted
    return round_model


# --- Tournament operations ---


def sync_tournament_players(session: Session, tournament_id: int) -> None:
    """
    Upsert canonical players from game names; wire game FKs.
    If the set of players (by normalized name) changes, clears table predictions
    and final ranking.
    """
    t = session.get(TournamentModel, tournament_id)
    if t is None:
        return

    key_to_display: dict[str, str] = {}
    for r in t.rounds:
        for g in r.games:
            if g.white_player:
                k = normalize_player_name(g.white_player)
                key_to_display.setdefault(k, g.white_player.strip())
            if g.black_player:
                k = normalize_player_name(g.black_player)
                key_to_display.setdefault(k, g.black_player.strip())

    existing_rows = list(
        session.scalars(
            select(TournamentPlayerModel).where(
                TournamentPlayerModel.tournament_id == tournament_id
            )
        ).all()
    )
    snapshot = {p.name_key: p for p in existing_rows}
    required_keys = set(key_to_display.keys())
    keys_before = set(snapshot.keys())

    if keys_before != required_keys:
        session.execute(
            delete(TablePredictionModel).where(
                TablePredictionModel.tournament_id == tournament_id
            )
        )
        t.final_ranking_player_ids = None

    for key in sorted(required_keys):
        display = key_to_display[key]
        if key in snapshot:
            p = snapshot[key]
            if p.name != display:
                p.name = display
        else:
            p = TournamentPlayerModel(
                tournament_id=tournament_id, name=display, name_key=key
            )
            session.add(p)

    session.flush()

    for _, p in list(snapshot.items()):
        if p.name_key not in required_keys:
            session.delete(p)

    session.flush()

    rows = list(
        session.scalars(
            select(TournamentPlayerModel).where(
                TournamentPlayerModel.tournament_id == tournament_id
            )
        ).all()
    )
    key_to_id = {p.name_key: p.id for p in rows}
    for r in t.rounds:
        for g in r.games:
            if g.white_player:
                nk = normalize_player_name(g.white_player)
                g.white_player_id = key_to_id.get(nk)
            else:
                g.white_player_id = None
            if g.black_player:
                nk = normalize_player_name(g.black_player)
                g.black_player_id = key_to_id.get(nk)
            else:
                g.black_player_id = None


def save_tournament(session: Session, tournament: Tournament) -> Tournament:
    """
    Save a tournament to the database. Creates or updates.
    Returns the tournament with IDs populated.
    """
    if tournament.id is not None:
        return _update_tournament(session, tournament)

    t = TournamentModel(
        name=tournament.name,
        points_white_win=tournament.points_white_win,
        points_black_win=tournament.points_black_win,
        points_draw=tournament.points_draw,
        points_table_per_rank=tournament.points_table_per_rank,
        table_prediction_deadline=tournament.table_prediction_deadline,
        final_ranking_player_ids=tournament.final_ranking_player_ids,
    )
    session.add(t)
    session.flush()

    for round_obj in tournament.rounds:
        r = RoundModel(
            tournament_id=t.id,
            round_number=round_obj.round_number,
            round_name=round_obj.round_name,
            prediction_deadline=round_obj.prediction_deadline,
        )
        session.add(r)
        session.flush()

        for game in round_obj.games:
            g = GameModel(
                round_id=r.id,
                white_player=game.white_player,
                black_player=game.black_player,
                white_rating=game.white_rating,
                black_rating=game.black_rating,
                result=game.result,
                is_deleted=game.is_deleted,
                deleted_at=game.deleted_at,
            )
            session.add(g)

    session.flush()
    sync_tournament_players(session, t.id)
    session.commit()
    session.refresh(t)
    return _tournament_to_dataclass(t)


def _update_tournament(session: Session, tournament: Tournament) -> Tournament:
    """Update an existing tournament by ID."""
    t = session.get(TournamentModel, tournament.id)
    if t is None:
        raise ValueError(f"Tournament with id {tournament.id} not found")

    t.name = tournament.name
    t.points_white_win = tournament.points_white_win
    t.points_black_win = tournament.points_black_win
    t.points_draw = tournament.points_draw
    t.points_table_per_rank = tournament.points_table_per_rank
    t.table_prediction_deadline = tournament.table_prediction_deadline
    t.final_ranking_player_ids = tournament.final_ranking_player_ids

    # Update rounds and games - for simplicity we replace all
    # (In a full implementation you might do a smarter merge)
    for existing_round in list(t.rounds):
        session.delete(existing_round)

    session.flush()

    for round_obj in tournament.rounds:
        r = RoundModel(
            tournament_id=t.id,
            round_number=round_obj.round_number,
            round_name=round_obj.round_name,
            prediction_deadline=round_obj.prediction_deadline,
        )
        session.add(r)
        session.flush()

        for game in round_obj.games:
            g = GameModel(
                round_id=r.id,
                white_player=game.white_player,
                black_player=game.black_player,
                white_rating=game.white_rating,
                black_rating=game.black_rating,
                result=game.result,
                is_deleted=game.is_deleted,
                deleted_at=game.deleted_at,
            )
            session.add(g)

    session.flush()
    sync_tournament_players(session, t.id)
    session.commit()
    session.refresh(t)
    return _tournament_to_dataclass(t)


def get_tournament(session: Session, tournament_id: int) -> Optional[Tournament]:
    """Get a tournament by ID."""
    t = session.get(TournamentModel, tournament_id)
    return _tournament_to_dataclass(t) if t else None


def patch_tournament_scoring(
    session: Session,
    tournament_id: int,
    *,
    points_white_win: Optional[int] = None,
    points_black_win: Optional[int] = None,
    points_draw: Optional[int] = None,
) -> Optional[Tournament]:
    """Update only scoring fields. Returns None if tournament not found."""
    t = session.get(TournamentModel, tournament_id)
    if t is None:
        return None
    if points_white_win is not None:
        t.points_white_win = points_white_win
    if points_black_win is not None:
        t.points_black_win = points_black_win
    if points_draw is not None:
        t.points_draw = points_draw
    session.commit()
    session.refresh(t)
    return _tournament_to_dataclass(t)


def list_tournaments(session: Session) -> list[Tournament]:
    """List all tournaments."""
    ts = session.scalars(
        select(TournamentModel).order_by(TournamentModel.id)
    ).all()
    return [_tournament_to_dataclass(t) for t in ts]


def _delete_predictions_for_game_ids(session: Session, game_ids: list[int]) -> None:
    """Remove predictions before games are deleted (game_id is NOT NULL; ORM may try to nullify)."""
    if not game_ids:
        return
    session.execute(delete(PredictionModel).where(PredictionModel.game_id.in_(game_ids)))


def delete_tournament(session: Session, tournament_id: int) -> bool:
    """Delete a tournament and cascaded rounds, games, predictions, players, etc."""
    t = session.get(TournamentModel, tournament_id)
    if t is None:
        return False
    game_ids = list(
        session.scalars(
            select(GameModel.id)
            .join(RoundModel, GameModel.round_id == RoundModel.id)
            .where(RoundModel.tournament_id == tournament_id)
        ).all()
    )
    _delete_predictions_for_game_ids(session, game_ids)
    session.delete(t)
    session.commit()
    return True


def delete_round(session: Session, round_id: int, tournament_id: int) -> bool:
    """
    Delete a round and its games (and predictions). Renumbers remaining rounds
    to 1..n and syncs canonical tournament players from remaining games.
    """
    r = session.get(RoundModel, round_id)
    if r is None or r.tournament_id != tournament_id:
        return False
    game_ids = list(
        session.scalars(select(GameModel.id).where(GameModel.round_id == round_id)).all()
    )
    _delete_predictions_for_game_ids(session, game_ids)
    session.delete(r)
    session.flush()
    remaining = session.scalars(
        select(RoundModel)
        .where(RoundModel.tournament_id == tournament_id)
        .order_by(RoundModel.round_number)
    ).all()
    for i, round_obj in enumerate(remaining, start=1):
        round_obj.round_number = i
    session.flush()
    sync_tournament_players(session, tournament_id)
    session.commit()
    return True


# --- User operations ---


def save_user(session: Session, user: User) -> User:
    """Save a user. Creates or updates."""
    if user.id is not None:
        u = session.get(UserModel, user.id)
        if u:
            u.name = user.name
            u.username = user.username
            u.password_hash = user.password_hash
            u.is_admin = user.is_admin
            u.is_super_admin = user.is_super_admin
            session.commit()
            session.refresh(u)
            return _user_to_dataclass(u)
    u = UserModel(
        name=user.name,
        username=user.username,
        password_hash=user.password_hash,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
    )
    session.add(u)
    session.commit()
    session.refresh(u)
    return _user_to_dataclass(u)


def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    u = session.get(UserModel, user_id)
    return _user_to_dataclass(u) if u else None


def list_users(session: Session) -> list[User]:
    """List all users."""
    users = session.scalars(select(UserModel).order_by(UserModel.id)).all()
    return [_user_to_dataclass(u) for u in users]


def get_user_by_username(session: Session, username: str) -> Optional[User]:
    """Get user by username."""
    u = session.scalars(
        select(UserModel).where(UserModel.username == username)
    ).first()
    return _user_to_dataclass(u) if u else None


# --- Game operations (soft-delete, update result) ---


def get_game_with_round(
    session: Session, game_id: int
) -> Optional[tuple[Game, Round]]:
    """Get a game and its round, or None if not found."""
    g = session.get(GameModel, game_id)
    if g is None:
        return None
    game = _game_to_dataclass(g)
    round_obj = _round_to_dataclass(g.round)
    return (game, round_obj)


def soft_delete_game(session: Session, game_id: int) -> bool:
    """Soft-delete a game. Returns True if found and deleted."""
    from datetime import datetime

    g = session.get(GameModel, game_id)
    if g is None:
        return False
    g.is_deleted = True
    g.deleted_at = datetime.utcnow()
    session.commit()
    return True


def get_round_by_id(session: Session, round_id: int) -> Optional[Round]:
    """Get a round by ID."""
    r = session.get(RoundModel, round_id)
    return _round_to_dataclass(r) if r else None


def update_round(
    session: Session,
    round_id: int,
    *,
    round_name: Optional[str] = None,
    prediction_deadline: Optional[datetime] = None,
) -> Optional[Round]:
    """Update a round. Returns updated Round or None if not found."""
    r = session.get(RoundModel, round_id)
    if r is None:
        return None
    if round_name is not None:
        r.round_name = round_name
    if prediction_deadline is not None:
        r.prediction_deadline = prediction_deadline
    session.commit()
    session.refresh(r)
    return _round_to_dataclass(r)


def update_game_result(
    session: Session, game_id: int, result: GameResult
) -> Optional[Game]:
    """Update a game's result. Returns the updated Game or None if not found."""
    g = session.get(GameModel, game_id)
    if g is None:
        return None
    g.result = result
    session.commit()
    session.refresh(g)
    return _game_to_dataclass(g)


# --- Prediction operations ---


def save_prediction(
    session: Session, user_id: int, game_id: int, predicted_result: GameResult
) -> Prediction:
    """Save or replace a user's prediction for a game (one per user per game)."""
    existing = session.scalars(
        select(PredictionModel).where(
            PredictionModel.user_id == user_id,
            PredictionModel.game_id == game_id,
        )
    ).first()
    if existing:
        existing.predicted_result = predicted_result
        session.commit()
        session.refresh(existing)
        return _prediction_to_dataclass(existing)

    p = PredictionModel(
        user_id=user_id,
        game_id=game_id,
        predicted_result=predicted_result,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return _prediction_to_dataclass(p)


def get_user_predictions_for_round(
    session: Session, round_id: int, user_id: int
) -> list[Prediction]:
    """Get a user's predictions for games in a round."""
    preds = session.scalars(
        select(PredictionModel)
        .join(GameModel)
        .where(
            GameModel.round_id == round_id,
            PredictionModel.user_id == user_id,
        )
    ).all()
    return [_prediction_to_dataclass(p) for p in preds]


def get_predictions_for_round(
    session: Session, round_id: int
) -> list[Prediction]:
    """Get all predictions for games in a round."""
    preds = session.scalars(
        select(PredictionModel)
        .join(GameModel)
        .where(GameModel.round_id == round_id)
    ).all()
    return [_prediction_to_dataclass(p) for p in preds]


def get_prediction(
    session: Session, user_id: int, game_id: int
) -> Optional[Prediction]:
    """Get a user's prediction for a game."""
    p = session.scalars(
        select(PredictionModel).where(
            PredictionModel.user_id == user_id,
            PredictionModel.game_id == game_id,
        )
    ).first()
    return _prediction_to_dataclass(p) if p else None


def get_predictions_for_tournament(
    session: Session, tournament_id: int
) -> list[tuple[int, int, str]]:
    """
    Get all predictions for games in a tournament.
    Returns list of (user_id, game_id, predicted_result).
    """
    preds = session.scalars(
        select(PredictionModel)
        .join(GameModel, PredictionModel.game_id == GameModel.id)
        .join(RoundModel, GameModel.round_id == RoundModel.id)
        .where(
            RoundModel.tournament_id == tournament_id,
            GameModel.is_deleted == False,
        )
    ).unique().all()
    return [(p.user_id, p.game_id, p.predicted_result) for p in preds]


# --- Table predictions & admin patches ---

ALLOWED_TOURNAMENT_PATCH_KEYS = frozenset(
    {
        "points_white_win",
        "points_black_win",
        "points_draw",
        "points_table_per_rank",
        "table_prediction_deadline",
        "final_ranking_player_ids",
    }
)


def get_tournament_player_ids(session: Session, tournament_id: int) -> set[int]:
    ids = session.scalars(
        select(TournamentPlayerModel.id).where(
            TournamentPlayerModel.tournament_id == tournament_id
        )
    ).all()
    return set(ids)


def assert_valid_final_ranking(
    session: Session, tournament_id: int, ids: list[int]
) -> None:
    valid = get_tournament_player_ids(session, tournament_id)
    if set(ids) != valid or len(ids) != len(valid):
        raise ValueError(
            "Final ranking must list each tournament player exactly once"
        )


def get_table_prediction_for_user(
    session: Session, user_id: int, tournament_id: int
) -> Optional[list[int]]:
    row = session.scalars(
        select(TablePredictionModel).where(
            TablePredictionModel.user_id == user_id,
            TablePredictionModel.tournament_id == tournament_id,
        )
    ).first()
    return list(row.ranking_player_ids) if row else None


def get_table_predictions_map(
    session: Session, tournament_id: int
) -> dict[int, list[int]]:
    rows = session.scalars(
        select(TablePredictionModel).where(
            TablePredictionModel.tournament_id == tournament_id
        )
    ).all()
    return {r.user_id: list(r.ranking_player_ids) for r in rows}


def save_table_prediction(
    session: Session,
    user_id: int,
    tournament_id: int,
    ranking_player_ids: list[int],
) -> TablePredictionModel:
    t = session.get(TournamentModel, tournament_id)
    if t is None:
        raise ValueError("Tournament not found")
    if t.table_prediction_deadline is None:
        raise ValueError("Table prediction is not open (admin must set a deadline)")
    if datetime.utcnow() > t.table_prediction_deadline:
        raise ValueError("Table prediction deadline has passed")
    assert_valid_final_ranking(session, tournament_id, ranking_player_ids)

    existing = session.scalars(
        select(TablePredictionModel).where(
            TablePredictionModel.user_id == user_id,
            TablePredictionModel.tournament_id == tournament_id,
        )
    ).first()
    if existing:
        existing.ranking_player_ids = ranking_player_ids
        session.commit()
        session.refresh(existing)
        return existing
    row = TablePredictionModel(
        user_id=user_id,
        tournament_id=tournament_id,
        ranking_player_ids=ranking_player_ids,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def apply_tournament_patch(
    session: Session, tournament_id: int, patch: dict[str, Any]
) -> Optional[Tournament]:
    """Apply allowed tournament fields from patch (e.g. model_dump(exclude_unset))."""
    t = session.get(TournamentModel, tournament_id)
    if t is None:
        return None
    for k, v in patch.items():
        if k not in ALLOWED_TOURNAMENT_PATCH_KEYS:
            continue
        if k == "final_ranking_player_ids" and v is not None:
            assert_valid_final_ranking(session, tournament_id, list(v))
        setattr(t, k, v)
    session.commit()
    session.refresh(t)
    return _tournament_to_dataclass(t)


def get_game_prediction_counts_by_game(
    session: Session, tournament_id: int
) -> dict[int, dict[str, int]]:
    """For each game id, count predictions by result string."""
    preds = session.scalars(
        select(PredictionModel)
        .join(GameModel, PredictionModel.game_id == GameModel.id)
        .join(RoundModel, GameModel.round_id == RoundModel.id)
        .where(
            RoundModel.tournament_id == tournament_id,
            GameModel.is_deleted == False,  # noqa: E712
        )
    ).all()
    by_game: dict[int, Counter[str]] = defaultdict(Counter)
    for p in preds:
        by_game[p.game_id][p.predicted_result] += 1
    out: dict[int, dict[str, int]] = {}
    for gid, ctr in by_game.items():
        out[gid] = {
            "1-0": ctr.get("1-0", 0),
            "0-1": ctr.get("0-1", 0),
            "1/2-1/2": ctr.get("1/2-1/2", 0),
        }
    return out
