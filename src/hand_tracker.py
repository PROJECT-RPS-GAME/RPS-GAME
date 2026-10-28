"""MediaPipe hand tracking for 1-2 hands.

Uses the current MediaPipe Tasks API (HandLandmarker). The small model file is
downloaded once to data/hand_landmarker.task. If the Tasks API is unavailable
the legacy mp.solutions.hands API is used instead.
"""
import os
import time
import urllib.request
from dataclasses import dataclass

import cv2
import numpy as np
import mediapipe as mp

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10),
    (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18),
    (18, 19), (19, 20), (0, 17),
]


@dataclass
class HandResult:
    landmarks: list      # 21 (x, y) normalised points
    label: str           # "Left" / "Right" as reported by MediaPipe
    area: float          # bounding-box area (normalised)
    wrist_x: float       # 0..1 across the (mirrored) image


def ensure_model(cfg):
    path = cfg.model_path
    if os.path.exists(path) and os.path.getsize(path) > 1_000_000:
        return path
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    print(f"Downloading hand model (about 8 MB) to {path} ...")
    tmp = path + ".part"
    try:
        urllib.request.urlretrieve(cfg.model_url, tmp)
        os.replace(tmp, path)
    except Exception as exc:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError(
            f"Could not download the hand model ({exc}).\n"
            f"Download it manually from:\n  {cfg.model_url}\n"
            f"and save it as: {path}") from exc
    return path


class _TasksBackend:
    name = "tasks"

    def __init__(self, cfg):
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
        path = ensure_model(cfg)
        options = vision.HandLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=path),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=cfg.max_num_hands,
            min_hand_detection_confidence=cfg.min_detection_confidence,
            min_hand_presence_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence,
        )
        self._lm = vision.HandLandmarker.create_from_options(options)
        self._ts = 0

    def detect(self, rgb):
        self._ts = max(self._ts + 1, int(time.monotonic() * 1000))
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self._lm.detect_for_video(img, self._ts)
        out = []
        for i, lms in enumerate(res.hand_landmarks or []):
            label = "Unknown"
            if res.handedness and i < len(res.handedness) and res.handedness[i]:
                label = res.handedness[i][0].category_name
            out.append(([(p.x, p.y) for p in lms], label))
        return out

    def close(self):
        self._lm.close()


class _LegacyBackend:
    name = "legacy"

    def __init__(self, cfg):
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=False, max_num_hands=cfg.max_num_hands, model_complexity=0,
            min_detection_confidence=cfg.min_detection_confidence,
            min_tracking_confidence=cfg.min_tracking_confidence)

    def detect(self, rgb):
        res = self._hands.process(rgb)
        out = []
        for i, lm in enumerate(res.multi_hand_landmarks or []):
            label = "Unknown"
            if res.multi_handedness and i < len(res.multi_handedness):
                label = res.multi_handedness[i].classification[0].label
            out.append(([(p.x, p.y) for p in lm.landmark], label))
        return out

    def close(self):
        self._hands.close()


class HandTracker:
    def __init__(self, cfg):
        self.cfg = cfg
        try:
            self._backend = _TasksBackend(cfg)
        except Exception as tasks_err:
            try:
                self._backend = _LegacyBackend(cfg)
            except Exception as legacy_err:
                raise RuntimeError(f"MediaPipe hand tracking failed to start.\n"
                                   f"Tasks API: {tasks_err}\nLegacy API: {legacy_err}") from legacy_err
        self.backend_name = self._backend.name

    def process(self, frame_bgr):
        """Return a list of HandResult (possibly empty)."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        hands = []
        for pts, label in self._backend.detect(rgb):
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            hands.append(HandResult(pts, label, (max(xs) - min(xs)) * (max(ys) - min(ys)), pts[0][0]))
        return hands

    def close(self):
        self._backend.close()
