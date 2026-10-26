import unittest

from src.config import ROCK, PAPER, SCISSORS, WIN, LOSE, DRAW
from src.game_rules import decide


class RulesTest(unittest.TestCase):
    def test_win(self):
        for p, c in [(ROCK, SCISSORS), (PAPER, ROCK), (SCISSORS, PAPER)]:
            self.assertEqual(decide(p, c), WIN)

    def test_lose(self):
        for p, c in [(ROCK, PAPER), (PAPER, SCISSORS), (SCISSORS, ROCK)]:
            self.assertEqual(decide(p, c), LOSE)

    def test_draw(self):
        for m in (ROCK, PAPER, SCISSORS):
            self.assertEqual(decide(m, m), DRAW)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            decide("UNKNOWN", ROCK)
        with self.assertRaises(ValueError):
            decide(ROCK, None)


if __name__ == "__main__":
    unittest.main()
