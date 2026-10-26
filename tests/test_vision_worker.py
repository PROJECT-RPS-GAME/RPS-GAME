"""Runs the real VisionWorker loop with a fake camera and fake hand tracker."""
import json
import random
import sys
import threading
import types
import unittest

import numpy as np

try:
    import mediapipe  # noqa: F401
except Exception:                                  # not installed here: stub it, the fakes replace it
    sys.modules["mediapipe"] = types.ModuleType("mediapipe")

from src.config import Config
from src.game_engine import GameEngine
from src.hand_tracker import HandResult
from src.vision_worker import HAND_COLORS, VisionWorker, hand_color


class Hub:
    def __init__(self):
        self.seq = 0
        self.payload = None
        self.jpeg = None

    def publish(self, jpeg, payload_json):
        self.seq += 1
        self.jpeg = jpeg
        self.payload = payload_json
from tests.test_gestures import make_hand


class RecordingHub(Hub):
    def __init__(self):
        super().__init__()
        self.log = []

    def publish(self, jpeg, payload_json):
        self.log.append((jpeg, json.loads(payload_json)))
        super().publish(jpeg, payload_json)


class FakeCamera:
    def __init__(self, cfg, frames=90):
        self.left = frames

    def open(self):
        return True

    def read(self):
        if self.left <= 0:
            return None
        self.left -= 1
        return np.zeros((480, 640, 3), np.uint8)

    def release(self):
        pass


class FakeTracker:
    backend_name = "fake"

    def __init__(self, cfg, hands_fn):
        self.hands_fn, self.i = hands_fn, 0

    def process(self, frame):
        self.i += 1
        return self.hands_fn(self.i)

    def close(self):
        pass


def hand_result(lm, area=0.1):
    return HandResult(lm, "Right", area, lm[0][0])


def noisy(lm, rng, s=0.006):
    return [(x + rng.gauss(0, s), y + rng.gauss(0, s)) for x, y in lm]


class WorkerTest(unittest.TestCase):
    def test_tracker_colors_follow_handedness(self):
        self.assertEqual(hand_color(HandResult([], "Left", 0, 0)), HAND_COLORS["Left"])
        self.assertEqual(hand_color(HandResult([], "Right", 0, 0)), HAND_COLORS["Right"])
        self.assertNotEqual(HAND_COLORS["Left"], HAND_COLORS["Right"])

    def run_worker(self, hands_fn, mode="cpu", frames=90):
        cfg = Config(stability_frames=3, stability_ratio=1.0)
        engine, lock, hub = GameEngine(cfg), threading.Lock(), RecordingHub()
        engine.start(mode, None, 0.0)
        clock_t = [0.0]

        def clock():
            clock_t[0] += 1 / 30
            return clock_t[0]

        w = VisionWorker(cfg, engine, lock, hub,
                         tracker_factory=lambda c: FakeTracker(c, hands_fn),
                         camera_factory=lambda c: FakeCamera(c, frames), clock=clock)
        t = threading.Thread(target=w.run, daemon=True)
        t.start()
        for _ in range(500):
            if hub.seq >= frames:
                break
            threading.Event().wait(0.01)
        w.stop()
        t.join(timeout=3)
        return engine, hub

    def test_pointer_is_smoother_than_raw_and_gesture_is_stable(self):
        rng = random.Random(5)
        base = make_hand(1, 1, 1, 1)
        raw_x = []

        def hands(i):
            lm = noisy(base, rng)
            raw_x.append(lm[8][0])
            return [hand_result(lm)]

        engine, hub = self.run_worker(hands)
        frames = [p for _, p in hub.log if p["camera_ok"] and p["pointer"]]
        self.assertGreater(len(frames), 60)
        out = [p["pointer"]["x"] for p in frames][20:]

        def std(v):
            m = sum(v) / len(v)
            return (sum((a - m) ** 2 for a in v) / len(v)) ** 0.5
        self.assertLess(std(out), std(raw_x[20:len(out) + 20]) * 0.5)
        self.assertEqual(engine.live["p1"], "PAPER")
        self.assertTrue(engine.present["p1"])

    def test_two_players_assigned_by_side(self):
        left = make_hand(0, 0, 0, 0)                      # rock, x around 0.5 -> shift left
        right = make_hand(1, 1, 0, 0)                     # scissors -> shift right
        left = [(x - 0.3, y) for x, y in left]
        right = [(x + 0.3, y) for x, y in right]
        engine, _ = self.run_worker(lambda i: [hand_result(left), hand_result(right)], mode="two")
        self.assertEqual((engine.live["p1"], engine.live["p2"]), ("ROCK", "SCISSORS"))

    def test_no_hand_means_no_pointer(self):
        engine, hub = self.run_worker(lambda i: [], frames=30)
        last = [p for _, p in hub.log if p["camera_ok"]][-1]
        self.assertIsNone(last["pointer"])
        self.assertFalse(engine.present["p1"])

    def test_camera_loss_is_reported_not_fatal(self):
        engine, hub = self.run_worker(lambda i: [], frames=5)
        self.assertTrue(any(not p["camera_ok"] for _, p in hub.log))


if __name__ == "__main__":
    unittest.main()
