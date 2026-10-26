"""Rule engine: decides WIN / LOSE / DRAW from the player's point of view."""
from .config import ROCK, PAPER, SCISSORS, VALID_MOVES, WIN, LOSE, DRAW

BEATS = {ROCK: SCISSORS, PAPER: ROCK, SCISSORS: PAPER}


def decide(player, computer):
    if player not in VALID_MOVES or computer not in VALID_MOVES:
        raise ValueError(f"Invalid move(s): {player!r}, {computer!r}")
    if player == computer:
        return DRAW
    return WIN if BEATS[player] == computer else LOSE
