import unittest

from src.config import ROCK, PAPER, SCISSORS, UNKNOWN
from src.gesture_classifier import classify_gesture
from src.gesture_stabilizer import GestureStabilizer

XS = {"index": 0.42, "middle": 0.50, "ring": 0.58, "pinky": 0.66}
BASE = {"index": 5, "middle": 9, "ring": 13, "pinky": 17}


def make_hand(index, middle, ring, pinky, half=False):
    """Synthetic 21-point hand. Wrist at (0.5, 0.9); fingers point up."""
    lm = [(0.5, 0.9)] * 21
    for i in range(1, 5):                      # thumb, out of the way
        lm[i] = (0.35 - 0.01 * i, 0.85 - 0.03 * i)
    ext = {"index": index, "middle": middle, "ring": ring, "pinky": pinky}
    for f, base in BASE.items():
        if ext[f] == "half":
            ys = (0.7, 0.6, 0.57, 0.56)        # ambiguous: ratio between thresholds
        elif ext[f]:
            ys = (0.7, 0.6, 0.5, 0.4)
        else:
            ys = (0.7, 0.62, 0.70, 0.75)
        for k, y in enumerate(ys):
            lm[base + k] = (XS[f], y)
    return lm


class GestureTest(unittest.TestCase):
    def test_rock(self):
        self.assertEqual(classify_gesture(make_hand(0, 0, 0, 0)), ROCK)

    def test_paper(self):
        self.assertEqual(classify_gesture(make_hand(1, 1, 1, 1)), PAPER)

    def test_scissors(self):
        self.assertEqual(classify_gesture(make_hand(1, 1, 0, 0)), SCISSORS)

    def test_unknown_combinations(self):
        self.assertEqual(classify_gesture(make_hand(1, 0, 0, 0)), UNKNOWN)
        self.assertEqual(classify_gesture(make_hand(1, 1, 1, 0)), UNKNOWN)
        self.assertEqual(classify_gesture(make_hand("half", "half", "half", "half")), UNKNOWN)

    def test_missing_landmarks(self):
        self.assertEqual(classify_gesture(None), UNKNOWN)
        self.assertEqual(classify_gesture([(0, 0)] * 5), UNKNOWN)


class StabilizerTest(unittest.TestCase):
    def test_needs_full_window(self):
        s = GestureStabilizer(window=4, min_ratio=0.75)
        out = [s.update(ROCK) for _ in range(3)]
        self.assertTrue(all(o == UNKNOWN for o in out))
        self.assertEqual(s.update(ROCK), ROCK)

    def test_noise_is_tolerated(self):
        s = GestureStabilizer(window=8, min_ratio=0.75)
        seq = [PAPER] * 3 + [UNKNOWN] + [PAPER] * 4
        out = [s.update(g) for g in seq]
        self.assertEqual(out[-1], PAPER)

    def test_unstable_returns_unknown(self):
        s = GestureStabilizer(window=4, min_ratio=0.75)
        for g in (ROCK, PAPER, ROCK, PAPER):
            out = s.update(g)
        self.assertEqual(out, UNKNOWN)

    def test_reset(self):
        s = GestureStabilizer(window=2)
        s.update(ROCK); s.update(ROCK); s.reset()
        self.assertEqual(s.update(ROCK), UNKNOWN)


if __name__ == "__main__":
    unittest.main()
