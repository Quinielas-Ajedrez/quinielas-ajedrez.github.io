"""
Evaluator for scoring predictions against actual game results.
"""

from typing import Optional


class Evaluator:
    """Scores predictions using per-result point values (tournament-configurable)."""

    def evaluate(
        self,
        predicted: str,
        actual: Optional[str],
        *,
        points_white_win: int = 1,
        points_black_win: int = 1,
        points_draw: int = 1,
    ) -> int:
        """
        Score a single prediction.
        Returns configured points if correct, 0 if wrong or result unknown.
        """
        if actual is None:
            return 0
        if predicted != actual:
            return 0
        points_map = {
            "1-0": points_white_win,
            "0-1": points_black_win,
            "1/2-1/2": points_draw,
        }
        return points_map.get(actual, 1)

    def compute_scores(
        self,
        predictions: list[tuple[int, int, str]],
        game_results: dict[int, Optional[str]],
        *,
        points_white_win: int = 1,
        points_black_win: int = 1,
        points_draw: int = 1,
    ) -> dict[int, int]:
        """
        Compute total points per user.
        predictions: list of (user_id, game_id, predicted_result)
        game_results: dict of game_id -> actual result (or None)
        """
        scores: dict[int, int] = {}
        for user_id, game_id, predicted in predictions:
            actual = game_results.get(game_id)
            points = self.evaluate(
                predicted,
                actual,
                points_white_win=points_white_win,
                points_black_win=points_black_win,
                points_draw=points_draw,
            )
            scores[user_id] = scores.get(user_id, 0) + points
        return scores
