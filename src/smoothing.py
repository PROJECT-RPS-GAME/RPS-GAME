"""Smoothing for hand landmarks and the on-screen pointer.

Uses the One Euro filter: strong smoothing when the hand is (almost) still, so
there is no jitter, and little smoothing when it moves fast, so there is no lag.
"""
import math


class OneEuroFilter:
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff    # lower = smoother when still
        self.beta = beta                # higher = less lag when moving fast
        self.d_cutoff = d_cutoff
        self.reset()

    def reset(self):
        self._x = None
        self._dx = 0.0
        self._t = None

    @staticmethod
    def _alpha(cutoff, dt):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, x, t):
        if self._x is None:
            self._x, self._t, self._dx = x, t, 0.0
            return x
        dt = max(t - self._t, 1e-3)
        dx = (x - self._x) / dt
        a_d = self._alpha(self.d_cutoff, dt)
        self._dx = a_d * dx + (1.0 - a_d) * self._dx
        cutoff = self.min_cutoff + self.beta * abs(self._dx)
        a = self._alpha(cutoff, dt)
        self._x = a * x + (1.0 - a) * self._x
        self._t = t
        return self._x


class LandmarkSmoother:
    """Smooths the 21 (x, y) landmarks of one hand."""

    def __init__(self, min_cutoff=1.6, beta=8.0, max_gap=0.25, max_jump=0.25):
        self._params = (min_cutoff, beta)
        self.max_gap = max_gap          # seconds without data before restarting
        self.max_jump = max_jump        # wrist jump (normalised) = a different hand
        self._f = None
        self._last_t = None
        self._last_wrist = None

    def reset(self):
        self._f, self._last_t, self._last_wrist = None, None, None

    def update(self, landmarks, t):
        wrist = landmarks[0]
        if self._f is not None:
            gap = t - self._last_t
            jump = math.hypot(wrist[0] - self._last_wrist[0], wrist[1] - self._last_wrist[1])
            if gap > self.max_gap or jump > self.max_jump:
                self._f = None
        if self._f is None:
            mc, b = self._params
            self._f = [(OneEuroFilter(mc, b), OneEuroFilter(mc, b)) for _ in landmarks]
        out = [(fx(x, t), fy(y, t)) for (x, y), (fx, fy) in zip(landmarks, self._f)]
        self._last_t, self._last_wrist = t, out[0]
        return out


class PointSmoother:
    """Smooths the pointer and freezes it while the fingers pinch (so a click does not move it)."""

    def __init__(self, min_cutoff=0.6, beta=5.0, max_gap=0.25, freeze_below=0.55):
        self._fx = OneEuroFilter(min_cutoff, beta)
        self._fy = OneEuroFilter(min_cutoff, beta)
        self.max_gap = max_gap
        self.freeze_below = freeze_below
        self._last_t = None
        self._out = None

    def reset(self):
        self._fx.reset(); self._fy.reset()
        self._last_t, self._out = None, None

    def update(self, x, y, pinch_ratio, t):
        if self._last_t is not None and t - self._last_t > self.max_gap:
            self.reset()
        self._last_t = t
        sx, sy = self._fx(x, t), self._fy(y, t)
        if pinch_ratio < self.freeze_below and self._out is not None:
            return self._out
        self._out = (sx, sy)
        return self._out
