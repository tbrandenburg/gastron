#!/usr/bin/env python3
"""Neon Tron lightcycle duel built with pygame."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

import pygame


# --- Display and timing ----------------------------------------------------
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 760
FPS = 60
GRID_SIZE = 10
STEP_INTERVAL_MS = 60  # Movement cadence (roughly 16.6 grid steps/sec)


# --- Palette ---------------------------------------------------------------
BG_COLOR = (5, 8, 18)
GRID_COLOR = (22, 39, 70)
GRID_GLOW = (20, 80, 130)
TEXT_COLOR = (220, 238, 255)
SHADOW_COLOR = (15, 24, 45)

CYAN = (30, 242, 255)
MAGENTA = (255, 48, 210)
YELLOW = (255, 233, 68)
ORANGE = (255, 130, 40)


Direction = Tuple[int, int]
Position = Tuple[int, int]

UP: Direction = (0, -1)
DOWN: Direction = (0, 1)
LEFT: Direction = (-1, 0)
RIGHT: Direction = (1, 0)


class GameState(Enum):
    RUNNING = auto()
    ROUND_OVER = auto()


@dataclass
class Player:
    name: str
    color: Tuple[int, int, int]
    glow_color: Tuple[int, int, int]
    controls: Dict[int, Direction]
    start_pos: Position
    start_dir: Direction

    position: Position = field(init=False)
    direction: Direction = field(init=False)
    pending_direction: Optional[Direction] = field(default=None, init=False)
    trail: List[Position] = field(default_factory=list, init=False)
    trail_set: Set[Position] = field(default_factory=set, init=False)
    alive: bool = field(default=True, init=False)
    score: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.reset_round()

    def reset_round(self) -> None:
        self.position = self.start_pos
        self.direction = self.start_dir
        self.pending_direction = None
        self.trail = []
        self.trail_set = set()
        self.alive = True

    def queue_turn(self, key: int) -> None:
        if key not in self.controls:
            return
        candidate = self.controls[key]
        if candidate == self.direction:
            return
        if candidate[0] == -self.direction[0] and candidate[1] == -self.direction[1]:
            return
        self.pending_direction = candidate

    def apply_pending_turn(self) -> None:
        if self.pending_direction is None:
            return
        candidate = self.pending_direction
        if candidate[0] == -self.direction[0] and candidate[1] == -self.direction[1]:
            self.pending_direction = None
            return
        self.direction = candidate
        self.pending_direction = None

    def next_position(self) -> Position:
        return (
            self.position[0] + self.direction[0] * GRID_SIZE,
            self.position[1] + self.direction[1] * GRID_SIZE,
        )


def draw_glow_rect(
    surface: pygame.Surface,
    color: Tuple[int, int, int],
    rect: pygame.Rect,
    layers: int,
    spread: int,
    alpha: int,
) -> None:
    """Draw stacked translucent rectangles to fake a neon bloom."""
    for i in range(layers, 0, -1):
        inflate = i * spread
        glow_rect = rect.inflate(inflate, inflate)
        glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(glow, (*color, max(8, alpha // (i + 1))), glow.get_rect(), border_radius=4)
        surface.blit(glow, glow_rect.topleft)


def build_grid_surface(size: Tuple[int, int]) -> pygame.Surface:
    """Pre-render a retro glowing perspective-ish grid."""
    width, height = size
    grid = pygame.Surface((width, height), pygame.SRCALPHA)

    for x in range(0, width, GRID_SIZE * 2):
        strong = (x // (GRID_SIZE * 2)) % 6 == 0
        color = GRID_GLOW if strong else GRID_COLOR
        alpha = 95 if strong else 55
        pygame.draw.line(grid, (*color, alpha), (x, 0), (x, height), 1)

    for y in range(0, height, GRID_SIZE * 2):
        strong = (y // (GRID_SIZE * 2)) % 6 == 0
        color = GRID_GLOW if strong else GRID_COLOR
        alpha = 95 if strong else 55
        pygame.draw.line(grid, (*color, alpha), (0, y), (width, y), 1)

    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(vignette, (0, 0, 0, 70), vignette.get_rect(), width=100)
    grid.blit(vignette, (0, 0))
    return grid


def draw_player_trail(glow_layer: pygame.Surface, player: Player) -> None:
    for cell in player.trail:
        rect = pygame.Rect(cell[0], cell[1], GRID_SIZE, GRID_SIZE)
        draw_glow_rect(glow_layer, player.glow_color, rect, layers=3, spread=8, alpha=120)
        pygame.draw.rect(glow_layer, (*player.color, 230), rect, border_radius=2)


def draw_player_head(glow_layer: pygame.Surface, player: Player) -> None:
    rect = pygame.Rect(player.position[0], player.position[1], GRID_SIZE, GRID_SIZE)
    draw_glow_rect(glow_layer, player.glow_color, rect, layers=4, spread=10, alpha=170)
    pygame.draw.rect(glow_layer, (*player.color, 255), rect, border_radius=3)


class TronGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Neon Tron Lightcycle Duel")
        self.clock = pygame.time.Clock()

        self.big_font = pygame.font.SysFont("consolas", 40, bold=True)
        self.ui_font = pygame.font.SysFont("consolas", 24, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 18)

        mid_y = SCREEN_HEIGHT // 2
        self.player1 = Player(
            name="Player 1",
            color=CYAN,
            glow_color=CYAN,
            controls={
                pygame.K_w: UP,
                pygame.K_s: DOWN,
                pygame.K_a: LEFT,
                pygame.K_d: RIGHT,
            },
            start_pos=(SCREEN_WIDTH // 4, mid_y),
            start_dir=RIGHT,
        )
        self.player2 = Player(
            name="Player 2",
            color=MAGENTA,
            glow_color=MAGENTA,
            controls={
                pygame.K_UP: UP,
                pygame.K_DOWN: DOWN,
                pygame.K_LEFT: LEFT,
                pygame.K_RIGHT: RIGHT,
            },
            start_pos=(SCREEN_WIDTH * 3 // 4, mid_y),
            start_dir=LEFT,
        )

        self.state = GameState.RUNNING
        self.winner: Optional[Player] = None
        self.round_message = ""

        self.grid_surface = build_grid_surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.glow_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        self.occupied: Set[Position] = set()
        self.accumulator_ms = 0.0
        self.reset_round()

    def reset_round(self) -> None:
        self.player1.reset_round()
        self.player2.reset_round()

        self.occupied = {self.player1.position, self.player2.position}
        self.state = GameState.RUNNING
        self.winner = None
        self.round_message = ""
        self.accumulator_ms = 0.0

    def run(self) -> None:
        running = True
        while running:
            delta_ms = self.clock.tick(FPS)
            running = self.handle_events()
            if not running:
                break

            if self.state == GameState.RUNNING:
                self.accumulator_ms += delta_ms
                while self.accumulator_ms >= STEP_INTERVAL_MS:
                    self.update_simulation()
                    self.accumulator_ms -= STEP_INTERVAL_MS

            self.render()

        pygame.quit()

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False

                if self.state == GameState.RUNNING:
                    self.player1.queue_turn(event.key)
                    self.player2.queue_turn(event.key)
                elif event.key in (pygame.K_r, pygame.K_SPACE):
                    self.reset_round()
                elif event.key == pygame.K_n:
                    self.player1.score = 0
                    self.player2.score = 0
                    self.reset_round()
        return True

    def update_simulation(self) -> None:
        self.player1.apply_pending_turn()
        self.player2.apply_pending_turn()

        next1 = self.player1.next_position()
        next2 = self.player2.next_position()

        dead1, dead2 = self.detect_collisions(next1, next2)

        if dead1:
            self.player1.alive = False
        if dead2:
            self.player2.alive = False

        if dead1 or dead2:
            self.finish_round(dead1, dead2)
            return

        for player, next_pos in ((self.player1, next1), (self.player2, next2)):
            player.trail.append(player.position)
            player.trail_set.add(player.position)
            self.occupied.add(player.position)
            player.position = next_pos

        self.occupied.add(self.player1.position)
        self.occupied.add(self.player2.position)

    def detect_collisions(self, next1: Position, next2: Position) -> Tuple[bool, bool]:
        dead1 = not self.position_in_bounds(next1)
        dead2 = not self.position_in_bounds(next2)

        if next1 in self.occupied:
            dead1 = True
        if next2 in self.occupied:
            dead2 = True

        # Head-on and pass-through collisions are both fatal in this duel mode.
        if next1 == next2:
            dead1 = True
            dead2 = True
        if next1 == self.player2.position and next2 == self.player1.position:
            dead1 = True
            dead2 = True

        return dead1, dead2

    def finish_round(self, dead1: bool, dead2: bool) -> None:
        self.state = GameState.ROUND_OVER

        if dead1 and dead2:
            self.winner = None
            self.round_message = "DOUBLE CRASH"
            return

        if dead1:
            self.winner = self.player2
        elif dead2:
            self.winner = self.player1
        else:
            self.winner = None

        if self.winner is not None:
            self.winner.score += 1
            self.round_message = f"{self.winner.name.upper()} WINS"
        else:
            self.round_message = "ROUND OVER"

    @staticmethod
    def position_in_bounds(position: Position) -> bool:
        x, y = position
        return 0 <= x < SCREEN_WIDTH and 0 <= y < SCREEN_HEIGHT

    def render(self) -> None:
        self.screen.fill(BG_COLOR)
        self.screen.blit(self.grid_surface, (0, 0))

        self.glow_layer.fill((0, 0, 0, 0))

        draw_player_trail(self.glow_layer, self.player1)
        draw_player_trail(self.glow_layer, self.player2)
        draw_player_head(self.glow_layer, self.player1)
        draw_player_head(self.glow_layer, self.player2)

        self.screen.blit(self.glow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.draw_hud()

        if self.state == GameState.ROUND_OVER:
            self.draw_round_overlay()

        pygame.display.flip()

    def draw_hud(self) -> None:
        title = self.big_font.render("NEON TRON", True, YELLOW)
        title_shadow = self.big_font.render("NEON TRON", True, SHADOW_COLOR)
        self.screen.blit(title_shadow, (23, 21))
        self.screen.blit(title, (20, 18))

        p1_text = self.ui_font.render(f"P1 (WASD): {self.player1.score}", True, CYAN)
        p2_text = self.ui_font.render(f"P2 (Arrows): {self.player2.score}", True, MAGENTA)
        info_text = self.small_font.render("Esc: Quit   R/Space: Restart   N: New Match", True, ORANGE)

        self.screen.blit(p1_text, (20, 68))
        self.screen.blit(p2_text, (20, 96))
        self.screen.blit(info_text, (20, SCREEN_HEIGHT - 34))

    def draw_round_overlay(self) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 8, 16, 170))
        self.screen.blit(overlay, (0, 0))

        msg = self.big_font.render(self.round_message, True, YELLOW)
        msg_shadow = self.big_font.render(self.round_message, True, SHADOW_COLOR)
        msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))

        self.screen.blit(msg_shadow, (msg_rect.x + 3, msg_rect.y + 3))
        self.screen.blit(msg, msg_rect)

        if self.winner is None:
            detail = "No points awarded"
            color = ORANGE
        else:
            detail = f"{self.winner.name} earns a point"
            color = self.winner.color

        detail_surface = self.ui_font.render(detail, True, color)
        detail_rect = detail_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20))
        self.screen.blit(detail_surface, detail_rect)

        prompt = self.small_font.render("Press R or Space to race again", True, TEXT_COLOR)
        prompt_rect = prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 58))
        self.screen.blit(prompt, prompt_rect)


def main() -> None:
    TronGame().run()


if __name__ == "__main__":
    main()
