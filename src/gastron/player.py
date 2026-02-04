"""Lightcycle player and projectile entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable
import pygame

from .utils import GRID_SIZE, Direction, Position, add_direction, is_opposite


@dataclass(slots=True)
class PowerState:
    """Active temporary effects for a player."""

    speed_timer: int = 0
    shield_timer: int = 0


class Projectile(pygame.sprite.Sprite):
    """Projectile fired by a player to break opponent trails."""

    def __init__(self, owner_id: int, position: Position, direction: Direction) -> None:
        super().__init__()
        self.owner_id = owner_id
        self.direction = direction
        self.position = position
        self.image = pygame.Surface((GRID_SIZE // 2, GRID_SIZE // 2))
        self.image.fill((255, 200, 120))
        self.rect = self.image.get_rect(center=(position[0] + GRID_SIZE // 2, position[1] + GRID_SIZE // 2))

    def step(self) -> None:
        """Advance projectile by two grid units for punchy feedback."""
        self.position = add_direction(self.position, self.direction, step=GRID_SIZE * 2)
        self.rect.center = (self.position[0] + GRID_SIZE // 2, self.position[1] + GRID_SIZE // 2)


@dataclass(slots=True, eq=False)
class LightCycle(pygame.sprite.Sprite):
    """State and behavior for a Tron lightcycle."""

    player_id: int
    name: str
    color: tuple[int, int, int]
    glow_color: tuple[int, int, int]
    controls: Dict[int, Direction]
    shoot_key: int
    start_pos: Position
    start_dir: Direction

    position: Position = field(init=False)
    direction: Direction = field(init=False)
    pending_direction: Direction | None = field(default=None, init=False)
    trail: list[Position] = field(default_factory=list, init=False)
    trail_set: set[Position] = field(default_factory=set, init=False)
    alive: bool = field(default=True, init=False)
    score: int = field(default=0, init=False)
    ammo: int = field(default=0, init=False)
    power_state: PowerState = field(default_factory=PowerState, init=False)
    image: pygame.Surface = field(init=False)
    rect: pygame.Rect = field(init=False)

    def __post_init__(self) -> None:
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
        self.image.fill(self.color)
        self.rect = self.image.get_rect(topleft=self.start_pos)
        self.reset_round()

    def reset_round(self) -> None:
        """Reset runtime state for a new round."""
        self.position = self.start_pos
        self.direction = self.start_dir
        self.pending_direction = None
        self.trail.clear()
        self.trail_set.clear()
        self.alive = True
        self.ammo = 0
        self.power_state = PowerState()
        self.rect.topleft = self.position

    def queue_turn(self, key: int) -> None:
        """Queue the next direction if the input is legal."""
        if key not in self.controls:
            return
        candidate = self.controls[key]
        if candidate == self.direction or is_opposite(candidate, self.direction):
            return
        self.pending_direction = candidate

    def apply_pending_turn(self) -> None:
        """Apply the queued direction change."""
        if self.pending_direction is None:
            return
        if not is_opposite(self.pending_direction, self.direction):
            self.direction = self.pending_direction
        self.pending_direction = None

    def next_position(self) -> Position:
        """Compute next grid position from current heading."""
        return add_direction(self.position, self.direction)

    def consume_trail_segment(self, max_count: int = 20) -> None:
        """Erase a section of this player's own trail."""
        remove_count = min(max_count, len(self.trail))
        for _ in range(remove_count):
            removed = self.trail.pop(0)
            self.trail_set.discard(removed)

    def tick_effects(self) -> None:
        """Advance effect timers by one simulation step."""
        self.power_state.speed_timer = max(0, self.power_state.speed_timer - 1)
        self.power_state.shield_timer = max(0, self.power_state.shield_timer - 1)

    @property
    def has_shield(self) -> bool:
        return self.power_state.shield_timer > 0

    @property
    def speed_multiplier(self) -> int:
        return 2 if self.power_state.speed_timer > 0 else 1

    def update_sprite(self) -> None:
        """Sync sprite location with logical grid position."""
        self.rect.topleft = self.position


def occupied_cells(players: Iterable[LightCycle]) -> set[Position]:
    """Return all currently occupied cells by players and trails."""
    cells: set[Position] = set()
    for player in players:
        cells.add(player.position)
        cells.update(player.trail_set)
    return cells
