import math
import random
import unittest

from src.smoothing import LandmarkSmoother, OneEuroFilter, PointSmoother


def std(v):
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / len(v))


class OneEuroTest(unittest.TestCase):
    def test_reduces_jitter_when_still(self):
        rng = random.Random(1)
        f = OneEuroFilter(1.0, 5.0)
        raw, out = [], []
        for i in range(300):
            x = 0.5 + rng.gauss(0, 0.01)
            raw.append(x); out.append(f(x, i / 30))
        self.assertLess(std(out[30:]), std(raw[30:]) * 0.4)

    def test_follows_fast_motion_with_small_lag(self):
        f = OneEuroFilter(1.0, 20.0)
        y = 0
        for i in range(60):
            y = f(i / 60.0, i / 30)           # moves 2 units/s
        self.assertLess(abs(y - 59 / 60.0), 0.08)

    def test_first_value_passthrough_and_reset(self):
        f = OneEuroFilter()
        self.assertEqual(f(0.3, 0.0), 0.3)
        f(0.9, 0.03)
        f.reset()
        self.assertEqual(f(0.1, 1.0), 0.1)


class LandmarkSmootherTest(unittest.TestCase):
    def hand(self, dx=0.0, dy=0.0):
        return [(0.5 + dx + 0.01 * i, 0.5 + dy) for i in range(21)]

    def test_smooths_noise(self):
        rng = random.Random(2)
        s = LandmarkSmoother()
        raw, out = [], []
        for i in range(200):
            dx = rng.gauss(0, 0.008)
            raw.append(self.hand(dx)[8][0])
            out.append(s.update(self.hand(dx), i / 30)[8][0])
        self.assertLess(std(out[30:]), std(raw[30:]) * 0.5)

    def test_restarts_after_gap_and_on_jump(self):
        s = LandmarkSmoother()
        for i in range(10):
            s.update(self.hand(0.0), i / 30)
        far = self.hand(0.3)                  # a different hand appears: no smearing
        self.assertAlmostEqual(s.update(far, 10 / 30)[0][0], far[0][0], places=6)
        s.update(self.hand(0.3), 11 / 30)
        back = self.hand(0.35)
        self.assertAlmostEqual(s.update(back, 5.0)[0][0], back[0][0], places=6)   # after a long gap


class PointSmootherTest(unittest.TestCase):
    def test_freezes_while_pinching(self):
        p = PointSmoother()
        for i in range(30):
            x, y = p.update(0.5, 0.5, 1.0, i / 30)
        fx, fy = p.update(0.51, 0.5, 0.2, 31 / 30)        # start pinching, tip drifts
        for i in range(32, 45):
            ox, oy = p.update(0.6, 0.6, 0.2, i / 30)
        self.assertEqual((ox, oy), (fx, fy))
        nx, ny = p.update(0.6, 0.6, 1.0, 46 / 30)         # fingers open again: moves
        self.assertGreater(nx, fx)

    def test_pointer_jitter_is_small(self):
        rng = random.Random(3)
        p = PointSmoother()
        raw, out = [], []
        for i in range(300):
            x = 0.5 + rng.gauss(0, 0.01)
            raw.append(x); out.append(p.update(x, 0.5, 1.0, i / 30)[0])
        self.assertLess(std(out[30:]), std(raw[30:]) * 0.35)


if __name__ == "__main__":
    unittest.main()
