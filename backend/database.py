"""
Database setup and SQLAlchemy ORM models for persistence.
Uses PostgreSQL when DATABASE_URL is set (e.g. on Render), otherwise SQLite.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class UserModel(Base):
    """ORM model for users."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_super_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    predictions: Mapped[list["PredictionModel"]] = relationship(
        "PredictionModel", back_populates="user"
    )


class TournamentModel(Base):
    """ORM model for tournaments."""

    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    points_white_win: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    points_black_win: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    points_draw: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    points_table_per_rank: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    table_prediction_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    final_ranking_player_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    rounds: Mapped[list["RoundModel"]] = relationship(
        "RoundModel",
        back_populates="tournament",
        order_by="RoundModel.round_number",
        cascade="all, delete-orphan",
    )
    players: Mapped[list["TournamentPlayerModel"]] = relationship(
        "TournamentPlayerModel",
        back_populates="tournament",
        cascade="all, delete-orphan",
    )
    table_predictions: Mapped[list["TablePredictionModel"]] = relationship(
        "TablePredictionModel",
        back_populates="tournament",
        cascade="all, delete-orphan",
    )


class TournamentPlayerModel(Base):
    """Canonical player in a tournament (from YAML games, deduped by normalized name)."""

    __tablename__ = "tournament_players"
    __table_args__ = (
        UniqueConstraint("tournament_id", "name_key", name="uq_tournament_player_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_key: Mapped[str] = mapped_column(String(255), nullable=False)

    tournament: Mapped["TournamentModel"] = relationship(
        "TournamentModel", back_populates="players"
    )


class TablePredictionModel(Base):
    """User's predicted final ranking (ordered list of player ids)."""

    __tablename__ = "table_predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "tournament_id", name="uq_user_tournament_table_pred"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False
    )
    ranking_player_ids: Mapped[list] = mapped_column(JSON, nullable=False)

    tournament: Mapped["TournamentModel"] = relationship(
        "TournamentModel", back_populates="table_predictions"
    )


class RoundModel(Base):
    """ORM model for rounds."""

    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    round_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prediction_deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    tournament: Mapped["TournamentModel"] = relationship(
        "TournamentModel", back_populates="rounds"
    )
    games: Mapped[list["GameModel"]] = relationship(
        "GameModel",
        back_populates="round",
        cascade="all, delete-orphan",
    )


class GameModel(Base):
    """ORM model for games."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    round_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    white_player: Mapped[str] = mapped_column(String(255), nullable=False)
    black_player: Mapped[str] = mapped_column(String(255), nullable=False)
    white_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tournament_players.id", ondelete="SET NULL"), nullable=True
    )
    black_player_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tournament_players.id", ondelete="SET NULL"), nullable=True
    )
    white_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    black_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    round: Mapped["RoundModel"] = relationship("RoundModel", back_populates="games")
    predictions: Mapped[list["PredictionModel"]] = relationship(
        "PredictionModel", back_populates="game"
    )


class PredictionModel(Base):
    """ORM model for predictions."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False
    )
    predicted_result: Mapped[str] = mapped_column(String(10), nullable=False)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="predictions")
    game: Mapped["GameModel"] = relationship("GameModel", back_populates="predictions")


# Database URL - PostgreSQL when set (persistent), else SQLite (ephemeral on free tier)
_database_url = os.getenv("DATABASE_URL")
if _database_url:
    # Render and others use postgres://, SQLAlchemy wants postgresql://
    if _database_url.startswith("postgres://"):
        _database_url = _database_url.replace("postgres://", "postgresql://", 1)
    DATABASE_URL = _database_url
    _connect_args = {}
else:
    DATABASE_DIR = Path(__file__).resolve().parent.parent / "data"
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{DATABASE_DIR / 'quiniela.db'}"
    _connect_args = {"check_same_thread": False}

# Engine and session factory
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    _migrate_add_is_super_admin()
    _migrate_add_tournament_scoring()
    _migrate_add_tournament_table_and_players()


def _migrate_add_is_super_admin() -> None:
    """Add is_super_admin column if it doesn't exist (for existing databases)."""
    is_postgres = "postgresql" in DATABASE_URL
    default_val = "FALSE" if is_postgres else "0"
    with engine.connect() as conn:
        try:
            conn.execute(
                text(f"ALTER TABLE users ADD COLUMN is_super_admin BOOLEAN DEFAULT {default_val}")
            )
            conn.commit()
        except Exception:
            conn.rollback()
            # Column likely already exists


def _migrate_add_tournament_scoring() -> None:
    """Add points_* columns to tournaments if missing."""
    for col in ("points_white_win", "points_black_win", "points_draw"):
        with engine.connect() as conn:
            try:
                conn.execute(
                    text(
                        f"ALTER TABLE tournaments ADD COLUMN {col} INTEGER NOT NULL DEFAULT 1"
                    )
                )
                conn.commit()
            except Exception:
                conn.rollback()


def _migrate_add_tournament_table_and_players() -> None:
    """Add table prediction columns and game player FK columns for existing DBs."""
    is_pg = "postgresql" in DATABASE_URL

    def run(sql: str) -> None:
        with engine.connect() as conn:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()

    if is_pg:
        run(
            "ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS points_table_per_rank INTEGER NOT NULL DEFAULT 1"
        )
        run(
            "ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS table_prediction_deadline TIMESTAMP"
        )
        run(
            "ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS final_ranking_player_ids JSONB"
        )
        run(
            "ALTER TABLE games ADD COLUMN IF NOT EXISTS white_player_id INTEGER REFERENCES tournament_players(id) ON DELETE SET NULL"
        )
        run(
            "ALTER TABLE games ADD COLUMN IF NOT EXISTS black_player_id INTEGER REFERENCES tournament_players(id) ON DELETE SET NULL"
        )
    else:
        for stmt in (
            "ALTER TABLE tournaments ADD COLUMN points_table_per_rank INTEGER NOT NULL DEFAULT 1",
            "ALTER TABLE tournaments ADD COLUMN table_prediction_deadline DATETIME",
            "ALTER TABLE tournaments ADD COLUMN final_ranking_player_ids TEXT",
            "ALTER TABLE games ADD COLUMN white_player_id INTEGER",
            "ALTER TABLE games ADD COLUMN black_player_id INTEGER",
        ):
            run(stmt)


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
