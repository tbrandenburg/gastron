"""Particle effects for trails and explosions."""

from __future__ import annotations

import random
import pygame

from .utils import GRID_SIZE, Position


class Particle(pygame.sprite.Sprite):
    """Lightweight particle sprite with fade-out lifetime."""

    def __init__(
        self,
        position: Position,
        color: tuple[int, int, int],
        velocity: tuple[float, float],
        life: int,
        size: int,
    ) -> None:
        super().__init__()
        self.position = [float(position[0]), float(position[1])]
        self.velocity = [velocity[0], velocity[1]]
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.image = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=position)

    def update(self) -> None:
        """Advance particle simulation one frame."""
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]
        self.velocity[0] *= 0.98
        self.velocity[1] *= 0.98
        self.life -= 1

        alpha = max(0, int(255 * (self.life / max(1, self.max_life))))
        self.image.fill((0, 0, 0, 0))
        pygame.draw.circle(self.image, (*self.color, alpha), (self.size, self.size), self.size)
        self.rect.center = (int(self.position[0]), int(self.position[1]))

        if self.life <= 0:
            self.kill()


class ParticleSystem:
    """Owns particle groups and helper emitters."""

    def __init__(self) -> None:
        self.particles = pygame.sprite.Group()

    def emit_trail_spark(self, position: Position, color: tuple[int, int, int]) -> None:
        """Emit subtle sparks while cycles move."""
        if random.random() > 0.35:
            return
        jitter = (random.randint(-3, 3), random.randint(-3, 3))
        velocity = (random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4))
        self.particles.add(
            Particle(
                position=(position[0] + GRID_SIZE // 2 + jitter[0], position[1] + GRID_SIZE // 2 + jitter[1]),
                color=color,
                velocity=velocity,
                life=random.randint(10, 18),
                size=random.randint(1, 2),
            )
        )

    def emit_explosion(self, position: Position, color: tuple[int, int, int]) -> None:
        """Emit a burst of particles when a crash occurs."""
        origin = (position[0] + GRID_SIZE // 2, position[1] + GRID_SIZE // 2)
        for _ in range(45):
            velocity = (random.uniform(-3.8, 3.8), random.uniform(-3.8, 3.8))
            self.particles.add(
                Particle(
                    position=origin,
                    color=color,
                    velocity=velocity,
                    life=random.randint(18, 42),
                    size=random.randint(1, 3),
                )
            )

    def update(self) -> None:
        """Update all particles."""
        self.particles.update()

    def draw(self, surface: pygame.Surface) -> None:
        """Draw particles on top of the scene."""
        self.particles.draw(surface)
