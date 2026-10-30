import unittest

from src.score_manager import ScoreManager


class ScoreManagerTest(unittest.TestCase):
    def test_records_player_wins_and_draws(self):
        score = ScoreManager()
        score.record("p1")
        score.record("p2")
        score.record("draw")

        self.assertEqual(score.score, {"p1": 1, "p2": 1, "draws": 1})
        self.assertEqual(score.rounds, 3)

    def test_reset_clears_all_scores(self):
        score = ScoreManager()
        score.record("p1")
        score.reset()

        self.assertEqual(score.score, {"p1": 0, "p2": 0, "draws": 0})
        self.assertEqual(score.rounds, 0)

    def test_invalid_winner_is_rejected(self):
        with self.assertRaises(ValueError):
            ScoreManager().record("computer")


if __name__ == "__main__":
    unittest.main()
