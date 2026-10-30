"""Hand-as-mouse helpers: pointer position and pinch (click) measurement."""
import math

THUMB_TIP, INDEX_TIP, MIDDLE_TIP, WRIST, MIDDLE_MCP = 4, 8, 12, 0, 9


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def pointer_position(landmarks):
    """Middle fingertip in normalised image coordinates."""
    return landmarks[MIDDLE_TIP]


def pinch_ratio(landmarks):
    """Thumb-tip to index-tip distance, relative to hand size. Small = pinching."""
    size = _dist(landmarks[WRIST], landmarks[MIDDLE_MCP])
    if size < 1e-6:
        return 9.9
    return _dist(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / size
