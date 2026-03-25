"""Pydantic schemas for API request/response."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

GameResult = Literal["1-0", "0-1", "1/2-1/2"]


# --- Auth ---


class LoginRequest(BaseModel):
    username: str
    password: str


class BootstrapRequest(BaseModel):
    """Promote a user to super-admin (requires BOOTSTRAP_SECRET)."""
    secret: str
    username: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    is_admin: bool = False
    is_super_admin: bool = False


class UserResponse(BaseModel):
    id: int
    name: str
    username: str
    is_admin: bool
    is_super_admin: bool = False


class UserUpdateRequest(BaseModel):
    is_admin: Optional[bool] = None


# --- Tournaments ---


class GameResponse(BaseModel):
    id: int
    white_player: str
    black_player: str
    white_rating: int
    black_rating: int
    result: Optional[str] = None
    is_deleted: bool = False


class RoundResponse(BaseModel):
    id: int
    round_number: int
    round_name: str
    prediction_deadline: datetime
    games: list[GameResponse]


class TournamentPlayerResponse(BaseModel):
    id: int
    name: str
    name_key: str


class TournamentResponse(BaseModel):
    id: int
    name: str
    rounds: list[RoundResponse]
    points_white_win: int = 1
    points_black_win: int = 1
    points_draw: int = 1
    points_table_per_rank: int = 1
    table_prediction_deadline: Optional[datetime] = None
    final_ranking_player_ids: Optional[list[int]] = None
    players: list[TournamentPlayerResponse] = []


class TournamentListItem(BaseModel):
    id: int
    name: str


class TournamentImportRequest(BaseModel):
    yaml_content: str = Field(..., description="YAML content of the tournament")


class TournamentUpdateRequest(BaseModel):
    name: Optional[str] = None
    yaml_content: Optional[str] = None
    points_white_win: Optional[int] = Field(None, ge=0, description="Points for correct 1-0")
    points_black_win: Optional[int] = Field(None, ge=0, description="Points for correct 0-1")
    points_draw: Optional[int] = Field(None, ge=0, description="Points for correct draw")
    points_table_per_rank: Optional[int] = Field(
        None, ge=0, description="Points per correct rank in final table prediction"
    )
    table_prediction_deadline: Optional[datetime] = None
    final_ranking_player_ids: Optional[list[int]] = None


# --- Predictions ---


class PredictionCreate(BaseModel):
    game_id: int
    predicted_result: GameResult


class PredictionResponse(BaseModel):
    id: int
    user_id: int
    game_id: int
    predicted_result: str


# --- Admin: Games & Rounds ---


class GameUpdateRequest(BaseModel):
    result: Optional[GameResult] = None
    is_deleted: Optional[bool] = None


class RoundUpdateRequest(BaseModel):
    round_name: Optional[str] = None
    prediction_deadline: Optional[datetime] = None


# --- Leaderboard ---


class LeaderboardEntry(BaseModel):
    user_id: int
    username: str
    name: str
    points: int


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]


# --- Table prediction ---


class TablePredictionCreate(BaseModel):
    ranking_player_ids: list[int]


class TablePredictionResponse(BaseModel):
    ranking_player_ids: list[int]


class TablePredictionGetResponse(BaseModel):
    ranking_player_ids: Optional[list[int]] = None


# --- Super-admin statistics ---


class GamePredictionBreakdown(BaseModel):
    game_id: int
    white_player: str
    black_player: str
    round_name: str
    counts: dict[str, int]


class TournamentPredictionStatisticsResponse(BaseModel):
    games: list[GamePredictionBreakdown]
