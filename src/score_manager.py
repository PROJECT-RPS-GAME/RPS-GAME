"""Match score tracking."""


class ScoreManager:
    def __init__(self):
        self.reset()

    @property
    def rounds(self):
        return self.score["p1"] + self.score["p2"] + self.score["draws"]

    def record(self, winner):
        if winner not in ("p1", "p2", "draw"):
            raise ValueError("winner must be 'p1', 'p2', or 'draw'")
        self.score["draws" if winner == "draw" else winner] += 1

    def reset(self):
        self.score = {"p1": 0, "p2": 0, "draws": 0}
