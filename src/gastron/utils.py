"""Shared constants and utility helpers for Gastron."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple
import json
import random

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 760
FPS = 60
GRID_SIZE = 10
DEFAULT_STEP_INTERVAL_MS = 60

BG_COLOR = (5, 8, 18)
GRID_COLOR = (22, 39, 70)
GRID_GLOW = (20, 80, 130)
TEXT_COLOR = (220, 238, 255)
SHADOW_COLOR = (15, 24, 45)

CYAN = (30, 242, 255)
MAGENTA = (255, 48, 210)
YELLOW = (255, 233, 68)
ORANGE = (255, 130, 40)
GREEN = (98, 246, 128)
RED = (255, 85, 85)

Direction = Tuple[int, int]
Position = Tuple[int, int]

UP: Direction = (0, -1)
DOWN: Direction = (0, 1)
LEFT: Direction = (-1, 0)
RIGHT: Direction = (1, 0)
DIRECTIONS: tuple[Direction, ...] = (UP, DOWN, LEFT, RIGHT)

DATA_DIR = Path(".gastron")
SETTINGS_FILE = DATA_DIR / "settings.json"
SCORES_FILE = DATA_DIR / "scores.json"
REPLAY_DIR = DATA_DIR / "replays"


def ensure_data_dirs() -> None:
    """Create data directories for save files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a value into a closed interval."""
    return max(minimum, min(maximum, value))


def is_opposite(a: Direction, b: Direction) -> bool:
    """Return whether two directions are opposite vectors."""
    return a[0] == -b[0] and a[1] == -b[1]


def add_direction(position: Position, direction: Direction, step: int = GRID_SIZE) -> Position:
    """Move a grid-aligned position by direction * step."""
    return (position[0] + direction[0] * step, position[1] + direction[1] * step)


def in_bounds(position: Position) -> bool:
    """Check if a grid cell is inside the playfield."""
    x, y = position
    return 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT


def load_json(path: Path, default: Any) -> Any:
    """Load JSON data, returning default when missing or malformed."""
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path: Path, payload: Any) -> None:
    """Save JSON data with deterministic formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def random_open_cell(occupied: Iterable[Position]) -> Position:
    """Return a random free grid cell."""
    occupied_set = set(occupied)
    for _ in range(2000):
        x = random.randrange(0, SCREEN_WIDTH // GRID_SIZE) * GRID_SIZE
        y = random.randrange(0, SCREEN_HEIGHT // GRID_SIZE) * GRID_SIZE
        candidate = (x, y)
        if candidate not in occupied_set:
            return candidate
    return (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)


@dataclass(slots=True)
class RoundStats:
    """Snapshot of a completed round for UI and leaderboard updates."""

    winner_name: str | None
    winner_color: tuple[int, int, int] | None
    crash_type: str
    duration_seconds: float
    p1_cells: int
    p2_cells: int
