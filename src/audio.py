"""Audio asset configuration for the browser-based game UI."""

from pathlib import Path

WIN_SOUND_FILE = "win-sound.wav"


def win_sound_path(asset_root):
    return Path(asset_root) / "sounds" / WIN_SOUND_FILE
