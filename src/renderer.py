"""Drawing helpers for camera frames."""

import cv2

from .hand_tracker import HAND_CONNECTIONS

HAND_COLORS = {"Left": (0, 0, 255), "Right": (0, 0, 0)}
UNKNOWN_HAND_COLOR = (210, 210, 210)


def hand_color(hand):
    """Return a visible BGR tracking color for MediaPipe's handedness label."""
    return HAND_COLORS.get(hand.label, UNKNOWN_HAND_COLOR)


def draw_hand(image, hand, color):
    height, width = image.shape[:2]
    points = [(int(x * width), int(y * height)) for x, y in hand.landmarks]
    for start, end in HAND_CONNECTIONS:
        cv2.line(image, points[start], points[end], (255, 255, 255), 4, cv2.LINE_AA)
        cv2.line(image, points[start], points[end], color, 2, cv2.LINE_AA)
    for point in points:
        cv2.circle(image, point, 5, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(image, point, 3, color, -1, cv2.LINE_AA)


def draw_player_divider(image, split_x):
    x = int(image.shape[1] * split_x)
    for y in range(0, image.shape[0], 24):
        cv2.line(image, (x, y), (x, y + 12), (255, 255, 255), 1)
