"""Round history with optional JSON persistence (no video is ever stored)."""
import json
import os
import time


class RoundHistory:
    def __init__(self, display_size=5):
        self.display_size = display_size
        self._rounds = []

    def add(self, p1, p2, winner, mode):
        self._rounds.append({"p1": p1, "p2": p2, "winner": winner, "mode": mode,
                             "time": time.strftime("%Y-%m-%d %H:%M:%S")})

    def recent(self, n=None):
        """Newest first."""
        n = n or self.display_size
        return [{"p1": r["p1"], "p2": r["p2"], "winner": r["winner"]}
                for r in reversed(self._rounds[-n:])]

    def __len__(self):
        return len(self._rounds)

    def all(self):
        return list(self._rounds)

    def reset(self):
        self._rounds.clear()

    def save(self, path, extra=None):
        rounds = (extra or []) + self._rounds
        if not rounds:
            return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        existing = []
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except (OSError, ValueError):
                existing = []
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing + rounds, f, indent=2)
