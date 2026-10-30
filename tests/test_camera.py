import unittest
from unittest.mock import patch

import cv2

from src.camera import CameraManager
from src.config import Config


class FakeCapture:
    def __init__(self):
        self.settings = {}
        self.released = False

    def isOpened(self):
        return True

    def set(self, prop, value):
        self.settings[prop] = value
        return True

    def release(self):
        self.released = True


class CameraManagerTest(unittest.TestCase):
    def test_open_requests_smooth_capture_rate_and_latest_frame(self):
        cfg = Config()
        capture = FakeCapture()
        with patch("src.camera._open_capture", return_value=capture):
            camera = CameraManager(cfg)
            self.assertTrue(camera.open())

        self.assertEqual(capture.settings[cv2.CAP_PROP_FRAME_WIDTH], cfg.frame_width)
        self.assertEqual(capture.settings[cv2.CAP_PROP_FRAME_HEIGHT], cfg.frame_height)
        self.assertEqual(capture.settings[cv2.CAP_PROP_FPS], cfg.camera_fps)
        self.assertEqual(capture.settings[cv2.CAP_PROP_BUFFERSIZE], 1)


if __name__ == "__main__":
    unittest.main()
