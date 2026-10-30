"""Background thread: camera -> hand tracking -> gestures -> game engine -> hub."""
import json
import threading
import time

import cv2

from .camera import CameraManager
from .config import UNKNOWN
from .gesture_classifier import classify_gesture
from .hand_tracker import HandTracker
from .players import assign_hands
from .pointer import pinch_ratio, pointer_position
from .renderer import draw_hand, draw_player_divider, hand_color
from .smoothing import LandmarkSmoother, PointSmoother

class VisionWorker(threading.Thread):
    def __init__(self, cfg, engine, lock, hub, tracker_factory=None, camera_factory=None,
                 clock=None):
        super().__init__(daemon=True, name="vision")
        self.cfg, self.engine, self.lock, self.hub = cfg, engine, lock, hub
        self._stop_evt = threading.Event()
        self.tracker = None
        self.camera = None
        self._tracker_factory = tracker_factory or HandTracker
        self._camera_factory = camera_factory or CameraManager
        self._clock = clock or time.monotonic
        self.smoothers = {"p1": LandmarkSmoother(cfg.lm_min_cutoff, cfg.lm_beta),
                          "p2": LandmarkSmoother(cfg.lm_min_cutoff, cfg.lm_beta)}
        self.pointer_smoother = PointSmoother(cfg.ptr_min_cutoff, cfg.ptr_beta)

    def stop(self):
        self._stop_evt.set()

    # -- helpers -----------------------------------------------------
    def _publish(self, jpeg, state, pointer, ok, error, fps):
        self.hub.publish(jpeg, json.dumps({
            "camera_ok": ok, "error": error,
            "fps": round(fps, 1), "state": state, "pointer": pointer}))

    def _idle_state(self):
        with self.lock:
            return self.engine.snapshot(time.monotonic())

    def _fail(self, message):
        """Keep the web page alive and show the problem there."""
        print("ERROR:", message)
        while not self._stop_evt.is_set():
            self._publish(None, self._idle_state(), None, False, message, 0.0)
            time.sleep(0.5)

    # -- main loop -----------------------------------------------------
    def run(self):
        cfg = self.cfg
        try:
            self.tracker = self._tracker_factory(cfg)
        except Exception as exc:
            self._fail(str(exc))
            return
        print(f"Hand tracking ready ({self.tracker.backend_name} backend).")
        self.camera = self._camera_factory(cfg)
        if not self.camera.open():
            print("No webcam found yet - will keep trying (check camera_index in src/config.py).")

        fps, last = 0.0, self._clock()
        try:
            while not self._stop_evt.is_set():
                frame = self.camera.read()
                now = self._clock()
                if frame is None:
                    with self.lock:
                        self.engine.on_camera_lost(now)
                        state = self.engine.snapshot(now)
                    self._publish(None, state, None, False,
                                  "No camera. Connect a webcam, close other apps using it, "
                                  "or change camera_index in src/config.py.", 0.0)
                    time.sleep(0.05)
                    continue
                if cfg.mirror:
                    frame = cv2.flip(frame, 1)
                try:
                    hands = self.tracker.process(frame)
                except Exception as exc:               # never crash on a bad frame
                    print("warning: hand tracking failed:", exc)
                    hands = []

                with self.lock:
                    mode = self.engine.mode
                assigned = assign_hands(hands, mode, cfg.split_x)
                pointer_hand = max(
                    (hand for hand in assigned.values() if hand is not None),
                    key=lambda hand: hand.area,
                    default=None,
                )
                raw_pointer_position = (
                    pointer_position(pointer_hand.landmarks) if pointer_hand is not None else None
                )
                per_player = {}
                for pid in ("p1", "p2"):
                    h = assigned[pid]
                    if h is None:
                        per_player[pid] = (UNKNOWN, False)
                    else:
                        # smoothed landmarks -> steadier gestures, pointer and skeleton drawing
                        h.landmarks = self.smoothers[pid].update(h.landmarks, now)
                        per_player[pid] = (classify_gesture(h.landmarks, cfg.extended_ratio, cfg.folded_ratio), True)

                pointer = None
                if pointer_hand is not None and raw_pointer_position is not None:
                    ratio = pinch_ratio(pointer_hand.landmarks)
                    x, y = raw_pointer_position
                    x, y = self.pointer_smoother.update(x, y, ratio, now)
                    pointer = {"x": round(x, 4), "y": round(y, 4), "ratio": round(ratio, 3)}

                with self.lock:
                    self.engine.update(per_player, now)
                    state = self.engine.snapshot(now)

                for h in hands:
                    draw_hand(frame, h, hand_color(h))
                if mode == "two":
                    draw_player_divider(frame, cfg.split_x)

                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, cfg.jpeg_quality])
                dt = now - last
                last = now
                if dt > 0:
                    fps = 0.9 * fps + 0.1 / dt if fps else 1.0 / dt
                self._publish(buf.tobytes() if ok else None, state, pointer, True, None, fps)
        finally:
            if self.camera:
                self.camera.release()
            if self.tracker:
                self.tracker.close()
