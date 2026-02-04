"""Audio loading and playback wrappers."""

from __future__ import annotations

from pathlib import Path
import pygame


class AudioManager:
    """Loads and plays music/sfx with graceful fallback when assets are absent."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.sound_enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        try:
            pygame.mixer.init()
            self.sound_enabled = True
        except pygame.error:
            self.sound_enabled = False

    def load_assets(self) -> None:
        """Load available audio files from assets folders."""
        if not self.sound_enabled:
            return
        mapping = {
            "collision": self.root / "assets" / "sounds" / "collision.wav",
            "powerup": self.root / "assets" / "sounds" / "powerup.wav",
            "menu": self.root / "assets" / "sounds" / "menu.wav",
            "shoot": self.root / "assets" / "sounds" / "shoot.wav",
        }
        for key, path in mapping.items():
            if path.exists():
                try:
                    self.sounds[key] = pygame.mixer.Sound(str(path))
                except pygame.error:
                    continue

    def set_volumes(self, master: float, music: float, sfx: float) -> None:
        """Apply current volume settings."""
        if not self.sound_enabled:
            return
        pygame.mixer.music.set_volume(master * music)
        for sound in self.sounds.values():
            sound.set_volume(master * sfx)

    def play_music(self) -> None:
        """Play looping background music if file exists."""
        if not self.sound_enabled:
            return
        music_path = self.root / "assets" / "music" / "theme.ogg"
        if not music_path.exists():
            return
        try:
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.play(-1)
        except pygame.error:
            return

    def play(self, key: str) -> None:
        """Play a named sound effect."""
        if not self.sound_enabled:
            return
        sound = self.sounds.get(key)
        if sound:
            sound.play()
