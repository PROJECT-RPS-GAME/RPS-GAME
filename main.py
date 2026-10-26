"""Shinobi Rock Paper Scissors - hand-gesture game (Python + OpenCV + MediaPipe + web UI).

Run:  python app.py            (webcam + hand tracking)
      python app.py --demo     (keyboard only, no camera needed)
"""
import argparse
import threading
import time
import webbrowser

from werkzeug.serving import make_server

from src.config import Config
from src.demo_worker import DemoWorker
from src.game_engine import GameEngine
from src.hub import Hub
from src.server import create_app


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="keyboard demo, no camera")
    ap.add_argument("--camera", type=int, help="camera index (default from src/config.py)")
    ap.add_argument("--port", type=int, help="web server port")
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser")
    args = ap.parse_args()

    cfg = Config()
    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.port:
        cfg.port = args.port

    engine, lock, hub = GameEngine(cfg), threading.Lock(), Hub()
    stop = threading.Event()

    if args.demo:
        worker = DemoWorker(cfg, engine, lock, hub)
        demo_worker = worker
    else:
        from src.vision_worker import VisionWorker      # imports mediapipe, only when needed
        worker = VisionWorker(cfg, engine, lock, hub, on_quit=stop.set)
        demo_worker = None

    app = create_app(engine, lock, hub, on_quit=stop.set, demo_worker=demo_worker)
    server = make_server(cfg.host, cfg.port, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True, name="http").start()
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
