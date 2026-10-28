import json
import threading
import time
import unittest

from app import Hub
from src.config import Config
from src.game_engine import GameEngine
from src.server import create_app


class VideoStreamTest(unittest.TestCase):
    def test_video_endpoint_streams_new_frames_without_reconnecting(self):
        hub = Hub()
        app = create_app(GameEngine(Config()), threading.Lock(), hub)

        def publish_frames():
            time.sleep(0.05)
            hub.publish(b"first-frame", json.dumps({"camera_ok": True}))
            time.sleep(0.25)
            hub.publish(b"second-frame", json.dumps({"camera_ok": True}))

        publisher = threading.Thread(target=publish_frames)
        publisher.start()
        response = app.test_client().get("/video", buffered=False)
        chunks = iter(response.response)
        try:
            first = next(chunks)
            second = next(chunks)
        finally:
            response.close()
            publisher.join(timeout=1)

        self.assertIn(b"multipart/x-mixed-replace", response.content_type.encode())
        self.assertIn(b"first-frame", first)
        self.assertIn(b"second-frame", second)


if __name__ == "__main__":
    unittest.main()
