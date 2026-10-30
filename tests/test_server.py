import json
import threading
import time
import unittest

from main import Hub
from src.config import Config
from src.game_controller import GameController
from src.server import create_app


class VideoStreamTest(unittest.TestCase):
    def test_round_controls_are_in_top_right_actions(self):
        app = create_app(GameController(Config()), threading.Lock(), Hub())
        with app.test_client().get("/") as page:
            self.assertEqual(page.status_code, 200)

            header = page.data.split(b'<header class="game-topbar">', 1)[1].split(b"</header>", 1)[0]
            self.assertIn(b'<div class="top-actions">', header)
            self.assertIn(b'<div id="controls">', header)
            self.assertIn(b'id="btn-next"', header)
            self.assertIn(b'id="btn-rematch"', header)
            self.assertIn(b'data-act="menu"', header)
            footer = page.data.split(b'<div class="game-footer">', 1)[1]
            self.assertNotIn(b'<div id="controls">', footer)

    def test_project_assets_are_served(self):
        app = create_app(GameController(Config()), threading.Lock(), Hub())
        client = app.test_client()
        for path in ("/css/style.css", "/js/script.js", "/assets/icons/rock.png",
                     "/audio/win"):
            with client.get(path) as response:
                self.assertEqual(response.status_code, 200, path)
        self.assertEqual(client.get("/assets/videos/highlight.mp4").status_code, 404)

    def test_video_endpoint_streams_new_frames_without_reconnecting(self):
        hub = Hub()
        app = create_app(GameController(Config()), threading.Lock(), hub)

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
