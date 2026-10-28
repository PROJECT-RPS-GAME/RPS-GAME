"""Landmark-based Rock/Paper/Scissors classifier.

Independent from game logic: only answers ROCK, PAPER, SCISSORS or UNKNOWN.
Input is a list of 21 (x, y) normalised MediaPipe hand landmarks.

A finger counts as extended when its tip is much farther from the wrist than
its PIP joint (rotation- and scale-invariant). The thumb is ignored because it
is unreliable and not needed to tell the three gestures apart.
"""
import math

from .config import ROCK, PAPER, SCISSORS, UNKNOWN

WRIST = 0
# (pip index, tip index)
FINGERS = {"index": (6, 8), "middle": (10, 12), "ring": (14, 16), "pinky": (18, 20)}

EXT, FOLD, MID = "EXT", "FOLD", "MID"


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def finger_states(landmarks, extended_ratio=1.20, folded_ratio=1.05):
    wrist = landmarks[WRIST]
    states = {}
    for name, (pip, tip) in FINGERS.items():
        d_pip = _dist(wrist, landmarks[pip])
        if d_pip < 1e-6:
            states[name] = MID
            continue
        ratio = _dist(wrist, landmarks[tip]) / d_pip
        if ratio >= extended_ratio:
            states[name] = EXT
        elif ratio <= folded_ratio:
            states[name] = FOLD
        else:
            states[name] = MID
    return states


def classify_gesture(landmarks, extended_ratio=1.20, folded_ratio=1.05):
    if landmarks is None or len(landmarks) < 21:
        return UNKNOWN
    s = finger_states(landmarks, extended_ratio, folded_ratio)
    vals = list(s.values())
    if all(v == EXT for v in vals):
        return PAPER
    if all(v == FOLD for v in vals):
        return ROCK
    if (s["index"] == EXT and s["middle"] == EXT
            and s["ring"] == FOLD and s["pinky"] == FOLD):
        return SCISSORS
    return UNKNOWN
