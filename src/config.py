"""Central configuration and shared constants."""
from dataclasses import dataclass

ROCK = "ROCK"
PAPER = "PAPER"
SCISSORS = "SCISSORS"
UNKNOWN = "UNKNOWN"
VALID_MOVES = (ROCK, PAPER, SCISSORS)

WIN = "WIN"
LOSE = "LOSE"
DRAW = "DRAW"

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")


@dataclass
class Config:
    # Web server
    host: str = "127.0.0.1"
    port: int = 8000

    # Camera
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    mirror: bool = True              # selfie view (left hand side of screen = left in video)
    max_cameras_to_probe: int = 4
    max_read_failures: int = 30
    jpeg_quality: int = 75

    # Hand tracking
    model_path: str = "data/hand_landmarker.task"
    model_url: str = MODEL_URL
    max_num_hands: int = 2
    min_detection_confidence: float = 0.6
    min_tracking_confidence: float = 0.5
    split_x: float = 0.5             # 2-player: wrist left of this = Player 1

    # Smoothing (One Euro filter). Lower min_cutoff = steadier, higher beta = less lag when moving
    lm_min_cutoff: float = 1.6
    lm_beta: float = 8.0
    ptr_min_cutoff: float = 1.0
    ptr_beta: float = 7.0

    # Gesture classification (tip-to-wrist / pip-to-wrist distance ratio)
    extended_ratio: float = 1.20
    folded_ratio: float = 1.05

    # Stabilisation
    stability_frames: int = 6
    stability_ratio: float = 0.75

    # Round timing (seconds)
    countdown_seconds: int = 3
    result_seconds: float = 2.5
    capture_timeout_cpu: float = 0.0    # 0 = wait forever
    capture_timeout_two: float = 10.0

    # Match / history
    target_score: int = 0               # 0 = free play
    history_size: int = 5
    save_history: bool = True
    history_path: str = "data/game_history.json"
