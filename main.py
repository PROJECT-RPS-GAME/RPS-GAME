"""Shinobi Rock Paper Scissors - hand-gesture game entrypoint."""
import argparse
import threading
import time
import webbrowser

from werkzeug.serving import make_server

from src.config import Config
from src.game_controller import GameController
from src.server import create_app


class Hub:
    def __init__(self):
        self.seq = 0
        self.payload = None
        self.jpeg = None
        self._condition = threading.Condition()

    def publish(self, jpeg, payload_json):
        with self._condition:
            self.seq += 1
            self.jpeg = jpeg
            self.payload = payload_json
            self._condition.notify_all()

    def wait_for_update(self, after_seq, timeout=None):
        with self._condition:
            self._condition.wait_for(lambda: self.seq > after_seq, timeout)
            return self.seq, self.jpeg, self.payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, help="camera index (default from src/config.py)")
    ap.add_argument("--port", type=int, help="web server port")
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = ap.parse_args()

    cfg = Config()
    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.port:
        cfg.port = args.port

    engine, lock, hub = GameController(cfg), threading.Lock(), Hub()
    stop = threading.Event()

    app = create_app(engine, lock, hub, on_quit=stop.set)
    server = make_server(cfg.host, cfg.port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True, name="http").start()

    from src.vision_worker import VisionWorker
    worker = VisionWorker(cfg, engine, lock, hub)
    worker.start()

    url = f"http://{cfg.host}:{cfg.port}"
    print(f"Game running at {url}   (Ctrl+C or the Quit button to stop)")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    try:
        while not stop.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        pass
    finally:
        print("Shutting down...")
        worker.stop()
        worker.join(timeout=3)
        server.shutdown()
        if cfg.save_history:
            try:
                with lock:
                    engine.history.save(cfg.history_path)
            except OSError as exc:
                print("warning: could not save history:", exc)


if __name__ == "__main__":
    main()
