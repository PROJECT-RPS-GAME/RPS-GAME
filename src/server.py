"""Serve the web UI and the small API used by the browser."""

import json
import time
from pathlib import Path

from flask import Flask, Response, jsonify, request, send_file, stream_with_context

ROOT = Path(__file__).resolve().parent.parent
WEB_ROOT = ROOT / "web"


def create_app(engine, lock, hub, on_quit=None, demo_worker=None):
    app = Flask(__name__, static_folder=str(WEB_ROOT), static_url_path="")

    @app.get("/")
    def index():
        return send_file(WEB_ROOT / "index.html")

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "mode": getattr(engine, "mode", "cpu")})

    @app.get("/video")
    def video():
        def generate():
            seq = 0
            while True:
                if hasattr(hub, "wait_for_update"):
                    next_seq, jpeg, _ = hub.wait_for_update(seq, timeout=1.0)
                else:
                    next_seq = getattr(hub, "seq", seq)
                    jpeg = getattr(hub, "jpeg", None)
                    if next_seq == seq:
                        time.sleep(0.05)
                        continue
                if next_seq == seq:
                    continue
                seq = next_seq
                if not jpeg:
                    continue
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
                    + jpeg
                    + b"\r\n"
                )

        return Response(
            stream_with_context(generate()),
            mimetype="multipart/x-mixed-replace; boundary=frame",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate",
                     "X-Accel-Buffering": "no"},
        )

    @app.get("/events")
    def events():
        def generate():
            seq = 0
            while True:
                if hasattr(hub, "wait_for_update"):
                    next_seq, _, latest_payload = hub.wait_for_update(seq, timeout=0.25)
                else:
                    next_seq = getattr(hub, "seq", seq)
                    latest_payload = getattr(hub, "payload", None)
                    if next_seq == seq:
                        time.sleep(0.25)
                if next_seq > seq:
                    seq = next_seq
                if latest_payload:
                    payload = json.loads(latest_payload)
                else:
                    with lock:
                        state = engine.snapshot(time.monotonic())
                    payload = {
                        "camera_ok": True,
                        "error": None,
                        "demo": False,
                        "state": state,
                        "pointer": None,
                    }
                yield f"data: {json.dumps(payload)}\n\n"

        return Response(stream_with_context(generate()), mimetype="text/event-stream")

    @app.post("/api/action")
    def api_action():
        payload = request.get_json(silent=True) or {}
        action = payload.get("action")
        now = time.monotonic()

        try:
            with lock:
                if action == "start":
                    mode = payload.get("mode") or "cpu"
                    target = payload.get("target")
                    player_names = payload.get("player_names") or {}
                    engine.start(mode, target, now, player_names)
                    return jsonify({"ok": True, "state": engine.snapshot(now)})
                if action == "next":
                    engine.next_round(now)
                    return jsonify({"ok": True, "state": engine.snapshot(now)})
                if action == "rematch":
                    engine.rematch(now)
                    return jsonify({"ok": True, "state": engine.snapshot(now)})
                if action == "menu":
                    engine.to_menu(now)
                    return jsonify({"ok": True, "state": engine.snapshot(now)})
                return jsonify({"error": "unknown action"}), 400
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/quit")
    def api_quit():
        if on_quit is not None:
            on_quit()
        return jsonify({"ok": True})

    @app.post("/api/demo_input")
    def api_demo_input():
        payload = request.get_json(silent=True) or {}
        player = payload.get("player")
        gesture = payload.get("gesture")
        if player not in {"p1", "p2"} or gesture not in {"ROCK", "PAPER", "SCISSORS"}:
            return jsonify({"error": "invalid demo input"}), 400
        with lock:
            engine.present[player] = True
            engine.live[player] = gesture
            engine.update({"p1": (engine.live.get("p1", "UNKNOWN"), engine.present.get("p1", False)),
                           "p2": (engine.live.get("p2", "UNKNOWN"), engine.present.get("p2", False))}, time.monotonic())
        return jsonify({"ok": True})

    return app
