"""Scoring for final table (ranking) predictions."""

from typing import Optional


def compute_table_points(
    predicted: Optional[list[int]],
    actual: Optional[list[int]],
    points_per_rank: int,
) -> int:
    """
    Award points_per_rank for each rank position where predicted player matches actual.
    """
    if not predicted or not actual or len(predicted) != len(actual):
        return 0
    return sum(
        points_per_rank if predicted[i] == actual[i] else 0
        for i in range(len(actual))
    )


def compute_all_table_scores(
    predictions: dict[int, list[int]],
    actual: list[int],
    points_per_rank: int,
) -> dict[int, int]:
    """user_id -> table points."""
    return {
        uid: compute_table_points(pred, actual, points_per_rank)
        for uid, pred in predictions.items()
    }
