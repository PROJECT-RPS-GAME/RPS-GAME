import unittest

from src.config import Config, ROCK, PAPER, SCISSORS, UNKNOWN
from src.game_controller import GameController


class FixedComputer:
    def __init__(self, move=ROCK):
        self.move, self.calls = move, 0

    def choose(self):
        self.calls += 1
        return self.move


def make(mode="cpu", target=None, move=ROCK, **kw):
    cfg = Config(stability_frames=3, stability_ratio=1.0, countdown_seconds=3,
                 result_seconds=2.0, capture_timeout_two=5.0, **kw)
    comp = FixedComputer(move)
    e = GameController(cfg, comp)
    e.start(mode, None, 0.0)
    if target is not None:
        e.target = target          # bypass the UI-only 0/3/5 choices for short tests
    return e, comp


def feed(e, p1, p2, t, frames=3):
    """Feed `frames` frames at times t+0.1.. ; gesture None = no hand."""
    for i in range(1, frames + 1):
        per = {"p1": (p1 or UNKNOWN, p1 is not None), "p2": (p2 or UNKNOWN, p2 is not None)}
        e.update(per, t + 0.1 * i)
    return t + 0.1 * frames


def to_capture(e, t=0.0):
    e.next_round(t)
    assert e.phase == "COUNTDOWN"
    e.update({}, t + 3.0)
    assert e.phase == "CAPTURE"
    return t + 3.0


class CpuModeTest(unittest.TestCase):
    def test_round_scores_once_and_reveals_late(self):
        e, comp = make()
        t = to_capture(e)
        feed(e, PAPER, None, t, 2)
        self.assertEqual(comp.calls, 0)                      # not chosen before the lock
        self.assertIsNone(e.snapshot(t)["moves"])
        t = feed(e, PAPER, None, t + 0.2, 1)
        self.assertEqual(e.phase, "RESULT")
        snap = e.snapshot(t)
        self.assertEqual(snap["moves"], {"p1": PAPER, "p2": ROCK})
        self.assertEqual(snap["round_winner"], "p1")
        for k in range(20):
            e.update({"p1": (PAPER, True)}, t + 0.05 * k)
        self.assertEqual((e.score["p1"], e.rounds, len(e.history), e.seq), (1, 1, 1, 1))

    def test_countdown_gestures_ignored(self):
        e, _ = make()
        e.next_round(0.0)
        for i in range(1, 30):
            e.update({"p1": (ROCK, True)}, round(0.1 * i, 2))
        self.assertEqual(e.phase, "COUNTDOWN")
        e.update({"p1": (ROCK, True)}, 3.0)
        self.assertEqual(e.phase, "CAPTURE")
        feed(e, SCISSORS, None, 3.0)
        self.assertEqual(e.moves["p1"], SCISSORS)

    def test_unknown_and_no_hand_never_finish(self):
        e, _ = make()
        t = to_capture(e)
        for i in range(30):
            e.update({"p1": (UNKNOWN, True)}, t + 0.1 * i)
            e.update({"p1": (PAPER, False)}, t + 0.1 * i + 0.05)
        self.assertEqual(e.phase, "CAPTURE")
        self.assertEqual(e.rounds, 0)

    def test_draw_and_lose(self):
        e, _ = make(move=PAPER)
        t = to_capture(e)
        feed(e, PAPER, None, t)
        self.assertEqual((e.round_winner, e.score["draws"]), ("draw", 1))
        e.next_round(t + 1)
        t = to_capture(e, t + 1)
        feed(e, ROCK, None, t)
        self.assertEqual((e.round_winner, e.score["p2"]), ("p2", 1))

    def test_target_ends_match_and_rematch_resets(self):
        e, _ = make(target=1, move=SCISSORS)
        t = to_capture(e)
        t = feed(e, ROCK, None, t)
        self.assertEqual(e.phase, "RESULT")
        e.update({}, t + 2.0)
        self.assertEqual(e.phase, "MATCH_OVER")
        self.assertEqual(e.snapshot(t)["match_winner"], "p1")
        e.rematch(t + 3)
        self.assertEqual((e.phase, e.rounds, len(e.history)), ("READY", 0, 0))

    def test_no_timeout_in_cpu_mode(self):
        e, _ = make()
        t = to_capture(e)
        e.update({}, t + 500)
        self.assertEqual(e.phase, "CAPTURE")


class TwoPlayerTest(unittest.TestCase):
    def test_both_lock_then_result(self):
        e, comp = make("two")
        t = to_capture(e)
        t = feed(e, SCISSORS, None, t)
        self.assertEqual(e.phase, "CAPTURE")                 # waiting for player 2
        self.assertTrue(e.snapshot(t)["locked"]["p1"])
        self.assertFalse(e.snapshot(t)["locked"]["p2"])
        self.assertIsNone(e.snapshot(t)["moves"])            # hidden until both locked
        t = feed(e, SCISSORS, PAPER, t)
        self.assertEqual(e.phase, "RESULT")
        self.assertEqual(comp.calls, 0)
        self.assertEqual((e.round_winner, e.score["p1"], e.score["p2"]), ("p1", 1, 0))

    def test_player_two_can_win(self):
        e, _ = make("two")
        t = to_capture(e)
        feed(e, ROCK, PAPER, t)
        self.assertEqual((e.round_winner, e.score["p2"]), ("p2", 1))

    def test_locked_move_cannot_change(self):
        e, _ = make("two")
        t = to_capture(e)
        t = feed(e, ROCK, None, t)
        feed(e, PAPER, SCISSORS, t)
        self.assertEqual(e.moves["p1"], ROCK)
        self.assertEqual(e.round_winner, "p1")               # rock beats scissors

    def test_timeout_cancels_round(self):
        e, _ = make("two")
        t = to_capture(e)
        t = feed(e, PAPER, None, t)
        e.update({}, t + 6)
        self.assertEqual(e.phase, "READY")
        self.assertIn("Player 2", e.message)
        self.assertEqual(e.rounds, 0)


class MiscTest(unittest.TestCase):
    def test_custom_player_names_are_kept_in_snapshot_and_rematch(self):
        e = GameController(Config())
        e.start("two", 3, 0.0, {"p1": "  Naruto  ", "p2": "Sasuke"})
        snap = e.snapshot(0.0)
        self.assertEqual(snap["player_names"], {"p1": "Naruto", "p2": "Sasuke"})
        e.rematch(1.0)
        self.assertEqual(e.snapshot(1.0)["player_names"], {"p1": "Naruto", "p2": "Sasuke"})

    def test_player_name_validation(self):
        e = GameController(Config())
        for invalid in ("", "   ", "x" * 21, None):
            with self.subTest(name=invalid), self.assertRaises(ValueError):
                e.start("cpu", 3, 0.0, {"p1": invalid})

    def test_validation(self):
        e, _ = make()
        with self.assertRaises(ValueError):
            e.start("three", None, 0)
        with self.assertRaises(ValueError):
            e.start("cpu", 7, 0)

    def test_menu_resets(self):
        e, _ = make()
        t = to_capture(e)
        feed(e, PAPER, None, t)
        e.to_menu(10)
        self.assertEqual((e.phase, e.rounds), ("MENU", 0))

    def test_actions_ignored_in_wrong_phase(self):
        e, _ = make()
        to_capture(e)
        e.next_round(5)
        e.rematch(5)
        self.assertEqual(e.phase, "CAPTURE")

    def test_camera_lost_aborts_round(self):
        e, _ = make()
        to_capture(e)
        e.on_camera_lost(4)
        self.assertEqual(e.phase, "READY")

    def test_snapshot_hides_live_gesture_outside_ready(self):
        e, _ = make()
        e.update({"p1": (ROCK, True)}, 0.1)
        self.assertEqual(e.snapshot(0.1)["live"]["p1"], ROCK)
        to_capture(e)
        self.assertIsNone(e.snapshot(4)["live"])

    def test_history_newest_first(self):
        e, _ = make(move=ROCK)
        t = to_capture(e)
        t = feed(e, PAPER, None, t)
        e.next_round(t)
        t = to_capture(e, t)
        feed(e, SCISSORS, None, t)
        h = e.snapshot(t)["history"]
        self.assertEqual([r["p1"] for r in h], [SCISSORS, PAPER])


if __name__ == "__main__":
    unittest.main()
