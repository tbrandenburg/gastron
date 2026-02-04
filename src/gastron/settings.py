"""Settings persistence and runtime configuration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import pygame

from .utils import SETTINGS_FILE, ensure_data_dirs, load_json, save_json


class GameMode(str, Enum):
    """Available top-level gameplay modes."""

    SINGLE_PLAYER = "single_player"
    MULTIPLAYER = "multiplayer"
    TOURNAMENT = "tournament"


class AIDifficulty(str, Enum):
    """Difficulty presets for AI behavior."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(slots=True)
class DisplaySettings:
    """Display-related options."""

    fullscreen: bool = False
    show_grid: bool = True
    screen_shake: bool = True
    trail_fade: bool = True


@dataclass(slots=True)
class ControlScheme:
    """Per-player control bindings."""

    up: int
    down: int
    left: int
    right: int
    shoot: int


@dataclass(slots=True)
class GameSettings:
    """Persistent settings for the game."""

    master_volume: float = 0.8
    music_volume: float = 0.6
    sfx_volume: float = 0.8
    ai_difficulty: AIDifficulty = AIDifficulty.MEDIUM
    game_mode: GameMode = GameMode.SINGLE_PLAYER
    tournament_best_of: int = 5
    display: DisplaySettings = field(default_factory=DisplaySettings)
    player1_controls: ControlScheme = field(
        default_factory=lambda: ControlScheme(
            up=pygame.K_UP,
            down=pygame.K_DOWN,
            left=pygame.K_LEFT,
            right=pygame.K_RIGHT,
            shoot=pygame.K_RCTRL,
        )
    )
    player2_controls: ControlScheme = field(
        default_factory=lambda: ControlScheme(
            up=pygame.K_w,
            down=pygame.K_s,
            left=pygame.K_a,
            right=pygame.K_d,
            shoot=pygame.K_LSHIFT,
        )
    )

    @property
    def rounds_to_win(self) -> int:
        """Return wins needed in tournament mode."""
        return max(1, self.tournament_best_of // 2 + 1)


class SettingsManager:
    """Load, save, and mutate game settings."""

    def __init__(self) -> None:
        ensure_data_dirs()
        self.settings = self.load()

    def load(self) -> GameSettings:
        """Load game settings from disk with safe defaults."""
        raw = load_json(SETTINGS_FILE, {})
        settings = GameSettings()

        settings.master_volume = float(raw.get("master_volume", settings.master_volume))
        settings.music_volume = float(raw.get("music_volume", settings.music_volume))
        settings.sfx_volume = float(raw.get("sfx_volume", settings.sfx_volume))

        if raw.get("ai_difficulty") in {e.value for e in AIDifficulty}:
            settings.ai_difficulty = AIDifficulty(raw["ai_difficulty"])
        if raw.get("game_mode") in {e.value for e in GameMode}:
            settings.game_mode = GameMode(raw["game_mode"])

        settings.tournament_best_of = int(raw.get("tournament_best_of", settings.tournament_best_of))

        display = raw.get("display", {})
        settings.display.fullscreen = bool(display.get("fullscreen", settings.display.fullscreen))
        settings.display.show_grid = bool(display.get("show_grid", settings.display.show_grid))
        settings.display.screen_shake = bool(display.get("screen_shake", settings.display.screen_shake))
        settings.display.trail_fade = bool(display.get("trail_fade", settings.display.trail_fade))

        settings.player1_controls = self._load_controls(
            raw.get("player1_controls", {}), settings.player1_controls
        )
        settings.player2_controls = self._load_controls(
            raw.get("player2_controls", {}), settings.player2_controls
        )
        return settings

    @staticmethod
    def _load_controls(payload: dict[str, int], defaults: ControlScheme) -> ControlScheme:
        return ControlScheme(
            up=int(payload.get("up", defaults.up)),
            down=int(payload.get("down", defaults.down)),
            left=int(payload.get("left", defaults.left)),
            right=int(payload.get("right", defaults.right)),
            shoot=int(payload.get("shoot", defaults.shoot)),
        )

    def save(self) -> None:
        """Persist settings to disk."""
        payload = asdict(self.settings)
        payload["ai_difficulty"] = self.settings.ai_difficulty.value
        payload["game_mode"] = self.settings.game_mode.value
        save_json(SETTINGS_FILE, payload)

    def set_mode(self, mode: GameMode) -> None:
        """Update game mode and persist settings."""
        self.settings.game_mode = mode
        self.save()

    def cycle_difficulty(self) -> AIDifficulty:
        """Cycle AI difficulty and persist settings."""
        order = [AIDifficulty.EASY, AIDifficulty.MEDIUM, AIDifficulty.HARD]
        idx = order.index(self.settings.ai_difficulty)
        self.settings.ai_difficulty = order[(idx + 1) % len(order)]
        self.save()
        return self.settings.ai_difficulty

    def adjust_volume(self, field_name: str, delta: float) -> None:
        """Adjust a volume setting and save."""
        value = float(getattr(self.settings, field_name))
        setattr(self.settings, field_name, max(0.0, min(1.0, value + delta)))
        self.save()
