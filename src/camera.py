"""Webcam management with probing, camera switching and disconnect recovery."""
import sys
import time

import cv2


def _open_capture(index):
    # DirectShow opens much faster than the default backend on Windows.
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            return cap
        cap.release()
    return cv2.VideoCapture(index)


class CameraManager:
    def __init__(self, cfg):
        self.cfg = cfg
        self.index = cfg.camera_index
        self._cap = None
        self._failures = 0
        self._last_reopen = 0.0

    def open(self, index=None):
        self.release()
        idx = self.index if index is None else index
        cap = _open_capture(idx)
        if not cap.isOpened():
            cap.release()
            return False
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cfg.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cfg.frame_height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # always the newest frame, less lag
        self._cap, self.index, self._failures = cap, idx, 0
        return True

    @property
    def connected(self):
        return self._cap is not None

    def read(self):
        """Return a BGR frame, or None if unavailable (reconnects about once per second)."""
        if self._cap is None:
            now = time.monotonic()
            if now - self._last_reopen >= 1.0:
                self._last_reopen = now
                self.open()
            return None
        try:
            ok, frame = self._cap.read()
        except cv2.error:
            ok, frame = False, None
        if ok and frame is not None:
            self._failures = 0
            return frame
        self._failures += 1
        if self._failures >= self.cfg.max_read_failures:
            self.release()
        return None

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None
