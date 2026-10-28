"""Keyboard-only demo worker used by the CLI launcher."""

import threading
import time


class DemoWorker(threading.Thread):
    def __init__(self, cfg, engine, lock, hub):
        super().__init__(daemon=True, name="demo")
        self.cfg = cfg
        self.engine = engine
        self.lock = lock
        self.hub = hub
        self._stop_evt = threading.Event()

    def stop(self):
        self._stop_evt.set()

    def run(self):
        while not self._stop_evt.is_set():
            time.sleep(0.1)
