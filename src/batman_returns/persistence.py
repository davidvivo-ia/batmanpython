"""Settings + high score persistence.

Stored as JSON in the OS-appropriate user-config dir. We avoid an external
``platformdirs`` dep — `appdirs.user_config_dir` is recreated minimally with
``os.path.expanduser`` for portability.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming")
        return Path(base) / "batman-returns-py"
    if sys.platform == "darwin":
        return Path(os.path.expanduser("~/Library/Application Support/batman-returns-py"))
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "batman-returns-py"


def _config_path() -> Path:
    return _config_dir() / "save.json"


# Backwards-compat alias used by existing tests that monkeypatch this directly.
CONFIG_PATH = _config_path()


@dataclass(slots=True)
class SaveData:
    high_scores: list[int] = field(default_factory=list)
    music_volume: float = 0.6
    sfx_volume: float = 0.7
    fullscreen: bool = False
    unlocked: list[str] = field(default_factory=list)
    tutorial_seen: bool = False
    difficulty: str = "normal"             # "easy" | "normal" | "hard"
    highest_cleared_stage: int = -1        # -1 = none cleared, 0 = stage 1, etc
    beat_game: bool = False
    show_fps: bool = False

    def push_score(self, score: int) -> bool:
        """Insert score, keep top 5. Returns True if THIS submission made the table."""
        before = list(self.high_scores)
        self.high_scores.append(score)
        self.high_scores.sort(reverse=True)
        del self.high_scores[5:]
        # Made the table iff the table changed (or if the table is shorter than 5).
        return self.high_scores != before


def load() -> SaveData:
    path = _config_path()
    try:
        raw = json.loads(path.read_text())
        sd = SaveData()
        for k, v in raw.items():
            if hasattr(sd, k):
                setattr(sd, k, v)
        return sd
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return SaveData()


def save(data: SaveData) -> None:
    path = _config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(data), indent=2))
    except OSError:
        pass  # best effort
