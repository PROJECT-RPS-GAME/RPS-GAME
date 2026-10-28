"""Computer opponent. MVP: uniformly random choice."""
import random

from .config import VALID_MOVES


class ComputerPlayer:
    def __init__(self, rng=None):
        self._rng = rng or random.Random()

    def choose(self):
        return self._rng.choice(VALID_MOVES)
