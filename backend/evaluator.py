"""
Evaluator for scoring predictions against actual game results.
"""

from typing import Optional


class Evaluator:
    """Scores predictions against actual results. Basic: 1 point for correct, 0 for incorrect."""

    def evaluate(self, predicted: str, actual: Optional[str]) -> int:
        """
        Score a single prediction.
        Returns 1 if correct, 0 if incorrect or if actual result is not yet known.
        """
        if actual is None:
            return 0
        return 1 if predicted == actual else 0

    def compute_scores(
        self,
        predictions: list[tuple[int, int, str]],
        game_results: dict[int, Optional[str]],
    ) -> dict[int, int]:
        """
        Compute total points per user.
        predictions: list of (user_id, game_id, predicted_result)
        game_results: dict of game_id -> actual result (or None)
        Returns dict of user_id -> total points
        """
        scores: dict[int, int] = {}
        for user_id, game_id, predicted in predictions:
            actual = game_results.get(game_id)
            points = self.evaluate(predicted, actual)
            scores[user_id] = scores.get(user_id, 0) + points
        return scores
