"""Smooths per-frame gestures: a move is stable only if it dominates a window."""
from collections import Counter, deque

from .config import UNKNOWN


class GestureStabilizer:
    def __init__(self, window=8, min_ratio=0.75):
        self.window = window
        self.min_ratio = min_ratio
        self._buf = deque(maxlen=window)

    def update(self, gesture):
        self._buf.append(gesture)
        if len(self._buf) < self.window:
            return UNKNOWN
        best, count = Counter(self._buf).most_common(1)[0]
        if best != UNKNOWN and count / self.window >= self.min_ratio:
            return best
        return UNKNOWN

    def reset(self):
        self._buf.clear()
