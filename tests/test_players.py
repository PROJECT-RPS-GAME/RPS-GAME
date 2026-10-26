import unittest
from types import SimpleNamespace as H

from src.players import assign_hands
from src.pointer import pinch_ratio


def hand(x, area=0.1):
    return H(wrist_x=x, area=area)


class PlayersTest(unittest.TestCase):
    def test_cpu_uses_largest(self):
        a, b = hand(0.2, 0.05), hand(0.8, 0.2)
        r = assign_hands([a, b], "cpu")
        self.assertIs(r["p1"], b)
        self.assertIsNone(r["p2"])

    def test_two_players_split_by_side(self):
        a, b = hand(0.2), hand(0.8)
        r = assign_hands([b, a], "two")
        self.assertIs(r["p1"], a)
        self.assertIs(r["p2"], b)

    def test_two_players_one_side_only(self):
        a = hand(0.3)
        r = assign_hands([a], "two")
        self.assertIs(r["p1"], a)
        self.assertIsNone(r["p2"])

    def test_two_hands_same_side_picks_largest(self):
        small, big = hand(0.1, 0.01), hand(0.3, 0.2)
        self.assertIs(assign_hands([small, big], "two")["p1"], big)

    def test_empty(self):
        self.assertEqual(assign_hands([], "two"), {"p1": None, "p2": None})


class PinchTest(unittest.TestCase):
    def _hand(self, tip_gap):
        lm = [(0.5, 0.9)] * 21
        lm[9] = (0.5, 0.7)                  # middle mcp: hand size 0.2
        lm[8] = (0.5, 0.5)
        lm[4] = (0.5 + tip_gap, 0.5)
        return lm

    def test_pinch_small_ratio(self):
        self.assertLess(pinch_ratio(self._hand(0.02)), 0.32)

    def test_open_large_ratio(self):
        self.assertGreater(pinch_ratio(self._hand(0.2)), 0.5)


if __name__ == "__main__":
    unittest.main()
