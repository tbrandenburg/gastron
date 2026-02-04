"""Power-up definitions and spawning logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
import pygame

from .player import LightCycle
from .utils import GRID_SIZE, Position, random_open_cell


class PowerUpType(str, Enum):
    """Supported power-up variants."""

    SPEED = "speed"
    SHIELD = "shield"
    ERASER = "eraser"
    WEAPON = "weapon"


POWERUP_COLORS = {
    PowerUpType.SPEED: (100, 250, 120),
    PowerUpType.SHIELD: (90, 170, 255),
    PowerUpType.ERASER: (255, 210, 90),
    PowerUpType.WEAPON: (255, 120, 120),
}


class PowerUp(pygame.sprite.Sprite):
    """Collectible power-up entity."""

    def __init__(self, kind: PowerUpType, position: Position) -> None:
        super().__init__()
        self.kind = kind
        self.position = position
        self.image = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(self.image, POWERUP_COLORS[kind], self.image.get_rect(), border_radius=2)
        self.rect = self.image.get_rect(topleft=position)


@dataclass(slots=True)
class PowerUpManager:
    """Spawner and effect applier for power-ups."""

    spawn_interval_ticks: int = 170
    max_powerups: int = 3
    ticks_since_spawn: int = 0

    def maybe_spawn(self, group: pygame.sprite.Group, occupied: set[Position]) -> None:
        """Spawn a power-up when the cooldown expires."""
        self.ticks_since_spawn += 1
        if self.ticks_since_spawn < self.spawn_interval_ticks:
            return
        self.ticks_since_spawn = 0
        if len(group.sprites()) >= self.max_powerups:
            return
        kind = random.choice(list(PowerUpType))
        position = random_open_cell(occupied)
        group.add(PowerUp(kind=kind, position=position))

    def apply(self, player: LightCycle, kind: PowerUpType) -> str:
        """Apply the effects of a picked-up power-up."""
        if kind == PowerUpType.SPEED:
            player.power_state.speed_timer = 80
            return "Speed boost activated"
        if kind == PowerUpType.SHIELD:
            player.power_state.shield_timer = 70
            return "Shield online"
        if kind == PowerUpType.ERASER:
            player.consume_trail_segment(35)
            return "Trail section erased"

        player.ammo += 3
        return "Pulse weapon loaded"
