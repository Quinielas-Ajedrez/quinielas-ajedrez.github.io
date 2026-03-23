"""
YAML parsing helper for importing tournaments.
"""

import yaml
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Game, Round, Tournament

# Supported game result values
GAME_RESULTS = ("1-0", "0-1", "1/2-1/2")


def _parse_datetime(value: str) -> datetime:
    """Parse ISO-style datetime string."""
    # Support common formats
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {value!r}")


def _parse_game(data: dict[str, Any]) -> Game:
    """Parse a game dict from YAML into a Game dataclass."""
    white = data.get("white_player") or data.get("white")
    black = data.get("black_player") or data.get("black")
    if not white or not black:
        raise ValueError(f"Game must have white and black players: {data}")

    white_rating = data.get("white_rating", 0)
    black_rating = data.get("black_rating", 0)
    if not isinstance(white_rating, int):
        white_rating = int(white_rating)
    if not isinstance(black_rating, int):
        black_rating = int(black_rating)

    result = data.get("result")
    if result is not None and result not in GAME_RESULTS:
        raise ValueError(f"Invalid result {result!r}. Must be one of {GAME_RESULTS}")

    return Game(
        white_player=str(white),
        black_player=str(black),
        white_rating=white_rating,
        black_rating=black_rating,
        result=result,
    )


def _parse_round(data: dict[str, Any]) -> Round:
    """Parse a round dict from YAML into a Round dataclass."""
    round_number = data.get("round_number") or data.get("number")
    if round_number is None:
        raise ValueError(f"Round must have round_number or number: {data}")
    round_number = int(round_number)

    deadline = data.get("prediction_deadline")
    if not deadline:
        raise ValueError(f"Round must have prediction_deadline: {data}")
    if isinstance(deadline, str):
        deadline = _parse_datetime(deadline)
    elif not isinstance(deadline, datetime):
        raise ValueError(f"Invalid prediction_deadline: {deadline}")

    round_name = data.get("round_name", "")

    games_data = data.get("games", [])
    games = [_parse_game(g) for g in games_data]

    return Round(
        round_number=round_number,
        prediction_deadline=deadline,
        round_name=round_name,
        games=games,
    )


def parse_tournament_yaml(content: str | Path) -> Tournament:
    """
    Parse YAML content or file path into a Tournament dataclass.

    Expected YAML format:
        name: "Tournament Name"
        rounds:
          - round_number: 1
            round_name: "Round 1"   # optional, defaults to "Round {n}"
            prediction_deadline: "2025-04-01T14:00:00"
            games:
              - white_player: "Player A"
                black_player: "Player B"
                white_rating: 2750
                black_rating: 2720
              - white: "Player C"   # aliases supported
                black: "Player D"
                white_rating: 2680
                black_rating: 2700

    Raises:
        ValueError: If the YAML structure is invalid.
    """
    if isinstance(content, Path):
        content = content.read_text(encoding="utf-8")
    elif isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8")

    data = yaml.safe_load(content)
    if not data or not isinstance(data, dict):
        raise ValueError("YAML must contain a mapping/dict")

    name = data.get("name")
    if not name:
        raise ValueError("Tournament must have a name")

    rounds_data = data.get("rounds", [])
    if not isinstance(rounds_data, list):
        raise ValueError("rounds must be a list")

    rounds = [_parse_round(r) for r in rounds_data]
    return Tournament(name=str(name), rounds=rounds)
