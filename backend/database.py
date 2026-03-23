"""
Database setup and SQLAlchemy ORM models for persistence.
Uses PostgreSQL when DATABASE_URL is set (e.g. on Render), otherwise SQLite.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, create_engine, text
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

    rounds: Mapped[list["RoundModel"]] = relationship(
        "RoundModel",
        back_populates="tournament",
        order_by="RoundModel.round_number",
        cascade="all, delete-orphan",
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


def get_db():
    """Dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
