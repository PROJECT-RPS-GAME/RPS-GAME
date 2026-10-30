"""Game engine for 1-player (vs computer) and 2-player matches.

Phases: MENU -> READY -> COUNTDOWN -> CAPTURE -> RESULT -> (COUNTDOWN | MATCH_OVER)
Any phase can return to MENU. The engine knows nothing about cameras or the web:
it is fed one (gesture, hand_present) pair per player per frame plus a timestamp.
"""
import math

from .computer_player import ComputerPlayer
from .config import Config, UNKNOWN, VALID_MOVES, WIN, LOSE
from .game_rules import decide
from .gesture_stabilizer import GestureStabilizer
from .history import RoundHistory
from .score_manager import ScoreManager

MODES = ("cpu", "two")
TARGETS = (0, 3, 5)
PLAYERS = ("p1", "p2")


class GameController:
    def __init__(self, cfg=None, computer=None):
        self.cfg = cfg or Config()
        self.computer = computer or ComputerPlayer()
        self.stabs = {p: GestureStabilizer(self.cfg.stability_frames, self.cfg.stability_ratio) for p in PLAYERS}
        self.history = RoundHistory(self.cfg.history_size)
        self.phase = "MENU"
        self.phase_since = 0.0
        self.mode = "cpu"
        self.player_names = {"p1": "Player 1", "p2": "Computer"}
        self.target = self.cfg.target_score
        self.score_manager = ScoreManager()
        self.moves = {"p1": None, "p2": None}
        self.round_winner = None
        self.live = {"p1": UNKNOWN, "p2": UNKNOWN}
        self.present = {"p1": False, "p2": False}
        self.message = ""
        self.seq = 0            # increments once per finished round (UI uses it to fire effects)

    # ---- derived ------------------------------------------------------
    @property
    def rounds(self):
        return self.score_manager.rounds

    @property
    def score(self):
        return self.score_manager.score

    @property
    def match_winner(self):
        if self.target > 0:
            if self.score["p1"] >= self.target:
                return "p1"
            if self.score["p2"] >= self.target:
                return "p2"
        return None

    def _timeout(self):
        return self.cfg.capture_timeout_two if self.mode == "two" else self.cfg.capture_timeout_cpu

    # ---- internal helpers -------------------------------------------
    def _set(self, phase, now):
        self.phase = phase
        self.phase_since = now

    def _clear_round(self):
        self.moves = {"p1": None, "p2": None}
        self.round_winner = None
        for s in self.stabs.values():
            s.reset()

    def _reset_match(self):
        self.score_manager.reset()
        self.history.reset()
        self._clear_round()
        self.message = ""

    # ---- actions (called from the UI) -------------------------------
    @staticmethod
    def _player_name(value, player):
        if not isinstance(value, str):
            raise ValueError(f"{player} name must be text")
        name = value.strip()
        if not name:
            raise ValueError(f"{player} name cannot be empty")
        if len(name) > 20:
            raise ValueError(f"{player} name must be 20 characters or fewer")
        if any(ord(char) < 32 or ord(char) == 127 for char in name):
            raise ValueError(f"{player} name cannot contain control characters")
        return name

    def start(self, mode, target, now, player_names=None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        if target is not None and target not in TARGETS:
            raise ValueError(f"target must be one of {TARGETS}")
        defaults = {"p1": "Player 1", "p2": "Computer" if mode == "cpu" else "Player 2"}
        if player_names is not None:
            if not isinstance(player_names, dict):
                raise ValueError("player_names must be an object")
            named_players = ("p1",) if mode == "cpu" else PLAYERS
            for player in named_players:
                if player in player_names:
                    defaults[player] = self._player_name(player_names[player], player)
        if mode == "cpu":
            defaults["p2"] = "Computer"
        self.mode = mode
        self.player_names = defaults
        if target is not None:
            self.target = target
        self._reset_match()
        self._set("READY", now)

    def next_round(self, now):
        if self.phase in ("READY", "RESULT"):
            self._clear_round()
            self.message = ""
            self._set("COUNTDOWN", now)

    def rematch(self, now):
        if self.phase in ("READY", "RESULT", "MATCH_OVER"):
            self._reset_match()
            self._set("READY", now)

    def to_menu(self, now):
        self._reset_match()
        self._set("MENU", now)

    def on_camera_lost(self, now):
        if self.phase in ("COUNTDOWN", "CAPTURE"):
            self._clear_round()
            self.message = "Camera lost - round cancelled."
            self._set("READY", now)

    # ---- per-frame update ---------------------------------------------
    def update(self, per_player, now):
        """per_player: {"p1": (gesture, present), "p2": (gesture, present)}"""
        stable = {}
        for p in PLAYERS:
            g, present = per_player.get(p, (UNKNOWN, False))
            self.present[p] = bool(present)
            self.live[p] = g if present else UNKNOWN
            stable[p] = self.stabs[p].update(self.live[p])
        elapsed = now - self.phase_since

        if self.phase == "COUNTDOWN":
            if elapsed >= self.cfg.countdown_seconds:
                for s in self.stabs.values():
                    s.reset()          # anything shown during the countdown is ignored
                self._set("CAPTURE", now)
        elif self.phase == "CAPTURE":
            self._capture(stable, elapsed, now)
        elif self.phase == "RESULT":
            if self.match_winner and elapsed >= self.cfg.result_seconds:
                self._set("MATCH_OVER", now)

    def _capture(self, stable, elapsed, now):
        humans = ("p1",) if self.mode == "cpu" else PLAYERS
        for p in humans:
            if self.moves[p] is None and stable[p] in VALID_MOVES:
                self.moves[p] = stable[p]          # locked: cannot change this round
        if all(self.moves[p] is not None for p in humans):
            if self.mode == "cpu":
                # computer move is chosen only now, so it can never be seen early
                self.moves["p2"] = self.computer.choose()
            self._finish_round(now)
            return
        tmo = self._timeout()
        if tmo > 0 and elapsed > tmo:
            missing = [p for p in humans if self.moves[p] is None]
            who = " and ".join("Player " + p[1] for p in missing)
            self.message = f"No move from {who} - round cancelled."
            self._clear_round()
            self._set("READY", now)

    def _finish_round(self, now):
        result = decide(self.moves["p1"], self.moves["p2"])
        self.round_winner = "p1" if result == WIN else "p2" if result == LOSE else "draw"
        self.score_manager.record(self.round_winner)
        self.history.add(self.moves["p1"], self.moves["p2"], self.round_winner, self.mode)
        self.seq += 1
        self._set("RESULT", now)

    # ---- state for the UI ---------------------------------------------
    def countdown_label(self, now):
        if self.phase == "COUNTDOWN":
            remaining = self.cfg.countdown_seconds - (now - self.phase_since)
            return str(max(1, math.ceil(remaining)))
        if self.phase == "CAPTURE":
            return "GO!"
        return ""

    def snapshot(self, now):
        revealed = self.phase in ("RESULT", "MATCH_OVER")
        return {
            "phase": self.phase,
            "mode": self.mode,
            "player_names": dict(self.player_names),
            "target": self.target,
            "label": self.countdown_label(now),
            "seq": self.seq,
            "message": self.message,
            "score": dict(self.score),
            "rounds": self.rounds,
            "match_winner": self.match_winner if self.phase in ("RESULT", "MATCH_OVER") else None,
            "round_winner": self.round_winner if revealed else None,
            "moves": dict(self.moves) if revealed else None,
            "locked": {p: self.phase == "CAPTURE" and self.moves[p] is not None for p in PLAYERS},
            "present": dict(self.present),
            "live": dict(self.live) if self.phase == "READY" else None,
            "history": self.history.recent(),
        }
