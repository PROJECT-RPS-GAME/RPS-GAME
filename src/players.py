"""Assigns detected hands to players."""


def assign_hands(hands, mode, split=0.5):
    """Return {"p1": hand|None, "p2": hand|None}.

    cpu mode: the largest hand is Player 1.
    two mode: the hand whose wrist is on the left half is Player 1, right half Player 2
    (the camera image is mirrored, so players stand where they appear on screen).
    """
    out = {"p1": None, "p2": None}
    if not hands:
        return out
    if mode == "two":
        left = [h for h in hands if h.wrist_x < split]
        right = [h for h in hands if h.wrist_x >= split]
        if left:
            out["p1"] = max(left, key=lambda h: h.area)
        if right:
            out["p2"] = max(right, key=lambda h: h.area)
    else:
        out["p1"] = max(hands, key=lambda h: h.area)
    return out
