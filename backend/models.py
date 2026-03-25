"""
Data models for the chess tournament prediction system.
Uses dataclasses with typed fields for simplicity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional

# Type alias for game/prediction outcomes
GameResult = Literal["1-0", "0-1", "1/2-1/2"]


@dataclass
class User:
    """A user who can log in and make predictions."""

    name: str
    username: str
    password_hash: str
    is_admin: bool = False
    is_super_admin: bool = False
    id: Optional[int] = None


@dataclass
class Game:
    """A chess game with white and black players and their ratings."""

    white_player: str
    black_player: str
    white_rating: int
    black_rating: int
    result: Optional[GameResult] = None
    id: Optional[int] = None
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None


@dataclass
class Round:
    """A round containing games to predict and a deadline for predictions."""

    round_number: int
    prediction_deadline: datetime
    round_name: str = ""
    games: List[Game] = field(default_factory=list)
    id: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.round_name:
            self.round_name = f"Round {self.round_number}"


@dataclass
class TournamentPlayer:
    """Canonical player in a tournament (stable id for table predictions)."""

    id: int
    name: str
    name_key: str


@dataclass
class Tournament:
    """A tournament containing multiple rounds."""

    name: str
    rounds: List[Round] = field(default_factory=list)
    id: Optional[int] = None
    # Points awarded when prediction matches actual result (defaults: 1 each)
    points_white_win: int = 1  # 1-0
    points_black_win: int = 1  # 0-1
    points_draw: int = 1  # 1/2-1/2
    points_table_per_rank: int = 1  # per correct position in final table prediction
    table_prediction_deadline: Optional[datetime] = None
    final_ranking_player_ids: Optional[List[int]] = None  # actual final order (1st .. last)
    players: List["TournamentPlayer"] = field(default_factory=list)


@dataclass
class Prediction:
    """A user's prediction for a specific game outcome."""

    user_id: int
    game_id: int
    predicted_result: GameResult
    id: Optional[int] = None
