"""Core game loop, state machine, rendering, and orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Iterable
import time
import pygame

from .ai import GameSnapshot, TronAI
from .audio import AudioManager
from .menu import Menu, MenuItem
from .particles import ParticleSystem
from .player import LightCycle, Projectile, occupied_cells
from .powerups import PowerUpManager
from .settings import AIDifficulty, GameMode, GameSettings, SettingsManager
from .utils import (
    BG_COLOR,
    CYAN,
    DEFAULT_STEP_INTERVAL_MS,
    FPS,
    GREEN,
    GRID_COLOR,
    GRID_GLOW,
    GRID_SIZE,
    MAGENTA,
    ORANGE,
    RED,
    SCORES_FILE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SHADOW_COLOR,
    TEXT_COLOR,
    YELLOW,
    RoundStats,
    add_direction,
    ensure_data_dirs,
    in_bounds,
    load_json,
    save_json,
)


class GameState(Enum):
    """Finite states for menus and gameplay."""

    MAIN_MENU = auto()
    SETTINGS = auto()
    HIGH_SCORES = auto()
    PLAYING = auto()
    PAUSED = auto()
    ROUND_OVER = auto()
    GAME_OVER = auto()


@dataclass(slots=True)
class MatchInfo:
    """Mutable match-level state."""

    rounds_played: int = 0
    p1_round_wins: int = 0
    p2_round_wins: int = 0
    start_time: float = field(default_factory=time.time)
    round_start_time: float = field(default_factory=time.time)


@dataclass(slots=True)
class ReplayEvent:
    """A single replay frame event."""

    tick: int
    p1: tuple[int, int]
    p2: tuple[int, int]


class TronGame:
    """Production-ready Tron game with menus, AI, effects, and persistence."""

    def __init__(self, root: Path) -> None:
        pygame.init()
        pygame.font.init()
        ensure_data_dirs()

        self.root = root
        self.settings_manager = SettingsManager()
        self.settings: GameSettings = self.settings_manager.settings

        flags = pygame.FULLSCREEN if self.settings.display.fullscreen else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption("Gastron - Neon Tron")
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("consolas", 52, bold=True)
        self.body_font = pygame.font.SysFont("consolas", 27, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 18)

        self.state = GameState.MAIN_MENU
        self.main_menu = Menu(
            title="GASTRON",
            items=[
                MenuItem("Single Player", "start_single"),
                MenuItem("2-Player Versus", "start_multi"),
                MenuItem("Tournament Mode", "start_tourney"),
                MenuItem("Settings", "settings"),
                MenuItem("High Scores", "scores"),
                MenuItem("Exit", "exit"),
            ],
        )
        self.pause_menu = Menu(
            title="PAUSED",
            items=[
                MenuItem("Resume", "resume"),
                MenuItem("Restart Round", "restart"),
                MenuItem("Settings", "settings"),
                MenuItem("Quit to Menu", "quit"),
            ],
        )

        self.players = self._create_players(self.settings)
        self.player_group = pygame.sprite.Group(self.players)
        self.projectiles = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.powerup_manager = PowerUpManager()
        self.particles = ParticleSystem()

        self.ai = TronAI(self.settings.ai_difficulty)
        self.audio = AudioManager(self.root)
        self.audio.load_assets()
        self.audio.set_volumes(
            self.settings.master_volume,
            self.settings.music_volume,
            self.settings.sfx_volume,
        )
        self.audio.play_music()

        self.match = MatchInfo()
        self.winner: LightCycle | None = None
        self.round_stats: RoundStats | None = None
        self.flash_message = ""
        self.flash_timer = 0

        self.tick_accumulator_ms = 0.0
        self.grid_offset = [0.0, 0.0]
        self.screen_shake_frames = 0
        self.screen_shake_magnitude = 0

        self.simulation_tick = 0
        self.replay_log: list[ReplayEvent] = []

    @staticmethod
    def _create_players(settings: GameSettings) -> tuple[LightCycle, LightCycle]:
        mid_y = SCREEN_HEIGHT // 2
        p1_controls = {
            settings.player1_controls.up: (0, -1),
            settings.player1_controls.down: (0, 1),
            settings.player1_controls.left: (-1, 0),
            settings.player1_controls.right: (1, 0),
        }
        p2_controls = {
            settings.player2_controls.up: (0, -1),
            settings.player2_controls.down: (0, 1),
            settings.player2_controls.left: (-1, 0),
            settings.player2_controls.right: (1, 0),
        }
        return (
            LightCycle(
                player_id=1,
                name="Player 1",
                color=CYAN,
                glow_color=CYAN,
                controls=p1_controls,
                shoot_key=settings.player1_controls.shoot,
                start_pos=(SCREEN_WIDTH // 4, mid_y),
                start_dir=(1, 0),
            ),
            LightCycle(
                player_id=2,
                name="Player 2" if settings.game_mode != GameMode.SINGLE_PLAYER else "AI",
                color=MAGENTA,
                glow_color=MAGENTA,
                controls=p2_controls,
                shoot_key=settings.player2_controls.shoot,
                start_pos=(SCREEN_WIDTH * 3 // 4, mid_y),
                start_dir=(-1, 0),
            ),
        )

    def reset_round(self) -> None:
        """Reset round entities but preserve match score state."""
        for player in self.players:
            player.reset_round()
        self.projectiles.empty()
        self.powerups.empty()
        self.replay_log.clear()
        self.tick_accumulator_ms = 0
        self.match.round_start_time = time.time()
        self.winner = None
        self.round_stats = None
        self.state = GameState.PLAYING

    def reset_match(self) -> None:
        """Reset all match scores and restart round."""
        self.match = MatchInfo()
        self.players[0].score = 0
        self.players[1].score = 0
        self.reset_round()

    def run(self) -> None:
        """Main event/render/update loop."""
        running = True
        while running:
            dt_ms = self.clock.tick(FPS)
            running = self._handle_events()
            if not running:
                break

            if self.state == GameState.PLAYING:
                self._update_playing(dt_ms)
            elif self.state == GameState.ROUND_OVER:
                self.particles.update()

            self._render()

        pygame.quit()

    def _handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_ESCAPE:
                if self.state == GameState.PLAYING:
                    self.state = GameState.PAUSED
                elif self.state in {GameState.PAUSED, GameState.SETTINGS, GameState.HIGH_SCORES}:
                    self.state = GameState.MAIN_MENU
                elif self.state == GameState.MAIN_MENU:
                    return False
                continue

            if self.state == GameState.MAIN_MENU:
                self._handle_menu_input(self.main_menu, event.key)
            elif self.state == GameState.PAUSED:
                self._handle_menu_input(self.pause_menu, event.key)
            elif self.state == GameState.PLAYING:
                self._handle_gameplay_input(event.key)
            elif self.state == GameState.ROUND_OVER:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    if self.state == GameState.GAME_OVER:
                        self.state = GameState.MAIN_MENU
                    else:
                        self._advance_after_round()
            elif self.state == GameState.GAME_OVER:
                if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.state = GameState.MAIN_MENU
            elif self.state == GameState.SETTINGS:
                self._handle_settings_input(event.key)
            elif self.state == GameState.HIGH_SCORES and event.key in (pygame.K_BACKSPACE, pygame.K_ESCAPE):
                self.state = GameState.MAIN_MENU
        return True

    def _handle_menu_input(self, menu: Menu, key: int) -> None:
        if key == pygame.K_UP:
            menu.move(-1)
            self.audio.play("menu")
            return
        if key == pygame.K_DOWN:
            menu.move(1)
            self.audio.play("menu")
            return
        if key not in (pygame.K_RETURN, pygame.K_SPACE):
            return

        action = menu.current_action()
        self.audio.play("menu")
        if action == "start_single":
            self.settings_manager.set_mode(GameMode.SINGLE_PLAYER)
            self._refresh_mode()
            self.reset_match()
        elif action == "start_multi":
            self.settings_manager.set_mode(GameMode.MULTIPLAYER)
            self._refresh_mode()
            self.reset_match()
        elif action == "start_tourney":
            self.settings_manager.set_mode(GameMode.TOURNAMENT)
            self._refresh_mode()
            self.reset_match()
        elif action == "settings":
            self.state = GameState.SETTINGS
        elif action == "scores":
            self.state = GameState.HIGH_SCORES
        elif action == "resume":
            self.state = GameState.PLAYING
        elif action == "restart":
            self.reset_round()
        elif action == "quit":
            self.state = GameState.MAIN_MENU
        elif action == "exit":
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    def _handle_settings_input(self, key: int) -> None:
        if key == pygame.K_d:
            self.settings_manager.cycle_difficulty()
        elif key == pygame.K_1:
            self.settings_manager.adjust_volume("master_volume", -0.05)
        elif key == pygame.K_2:
            self.settings_manager.adjust_volume("master_volume", 0.05)
        elif key == pygame.K_3:
            self.settings_manager.adjust_volume("music_volume", -0.05)
        elif key == pygame.K_4:
            self.settings_manager.adjust_volume("music_volume", 0.05)
        elif key == pygame.K_5:
            self.settings_manager.adjust_volume("sfx_volume", -0.05)
        elif key == pygame.K_6:
            self.settings_manager.adjust_volume("sfx_volume", 0.05)
        elif key == pygame.K_g:
            self.settings.display.show_grid = not self.settings.display.show_grid
            self.settings_manager.save()
        elif key == pygame.K_h:
            self.settings.display.screen_shake = not self.settings.display.screen_shake
            self.settings_manager.save()
        elif key == pygame.K_f:
            self.settings.display.trail_fade = not self.settings.display.trail_fade
            self.settings_manager.save()
        elif key in (pygame.K_BACKSPACE, pygame.K_ESCAPE):
            self.state = GameState.MAIN_MENU

        self.settings = self.settings_manager.settings
        self.ai = TronAI(self.settings.ai_difficulty)
        self.audio.set_volumes(
            self.settings.master_volume,
            self.settings.music_volume,
            self.settings.sfx_volume,
        )

    def _refresh_mode(self) -> None:
        self.settings = self.settings_manager.settings
        self.players = self._create_players(self.settings)
        self.player_group = pygame.sprite.Group(self.players)
        self.ai = TronAI(self.settings.ai_difficulty)

    def _handle_gameplay_input(self, key: int) -> None:
        for player in self.players:
            player.queue_turn(key)
            if key == player.shoot_key and player.ammo > 0:
                player.ammo -= 1
                self.projectiles.add(Projectile(player.player_id, player.position, player.direction))
                self.audio.play("shoot")

    def _update_playing(self, dt_ms: float) -> None:
        self.tick_accumulator_ms += dt_ms
        step_ms = DEFAULT_STEP_INTERVAL_MS
        if any(player.power_state.speed_timer > 0 for player in self.players):
            step_ms = int(DEFAULT_STEP_INTERVAL_MS * 0.75)

        while self.tick_accumulator_ms >= step_ms:
            self.tick_accumulator_ms -= step_ms
            self._simulate_step()
            if self.state != GameState.PLAYING:
                break

        self.particles.update()
        if self.flash_timer > 0:
            self.flash_timer -= 1

    def _simulate_step(self) -> None:
        p1, p2 = self.players

        if self.settings.game_mode == GameMode.SINGLE_PLAYER:
            snapshot = GameSnapshot(
                ai_position=p2.position,
                ai_direction=p2.direction,
                opponent_position=p1.position,
                occupied=occupied_cells(self.players),
            )
            p2.pending_direction = self.ai.choose_direction(snapshot)
            if self.ai.should_shoot(snapshot, p2.ammo):
                p2.ammo -= 1
                self.projectiles.add(Projectile(p2.player_id, p2.position, p2.direction))

        for player in self.players:
            player.apply_pending_turn()

        for projectile in list(self.projectiles):
            projectile.step()
            if not in_bounds(projectile.position):
                projectile.kill()
                continue
            victim = p2 if projectile.owner_id == 1 else p1
            if projectile.position in victim.trail_set:
                victim.trail_set.discard(projectile.position)
                victim.trail = [pos for pos in victim.trail if pos != projectile.position]
                projectile.kill()

        occupied = occupied_cells(self.players)
        self.powerup_manager.maybe_spawn(self.powerups, occupied)

        for player in self.players:
            player.tick_effects()

        next_positions: dict[int, tuple[int, int]] = {}
        dead: dict[int, bool] = {1: False, 2: False}

        for player in self.players:
            next_positions[player.player_id] = player.next_position()

        next1 = next_positions[1]
        next2 = next_positions[2]
        if next1 == next2 or (next1 == p2.position and next2 == p1.position):
            dead[1] = True
            dead[2] = True

        for player in self.players:
            nxt = next_positions[player.player_id]
            if not in_bounds(nxt):
                dead[player.player_id] = True
                continue
            if nxt in occupied and not player.has_shield:
                dead[player.player_id] = True

        for player in self.players:
            if dead[player.player_id]:
                continue
            previous = player.position
            player.trail.append(previous)
            player.trail_set.add(previous)
            player.position = next_positions[player.player_id]
            player.update_sprite()
            self.particles.emit_trail_spark(player.position, player.color)

            hit = pygame.sprite.spritecollideany(player, self.powerups)
            if hit and isinstance(hit, pygame.sprite.Sprite):
                self.audio.play("powerup")
                self.flash_message = self.powerup_manager.apply(player, hit.kind)
                self.flash_timer = FPS * 2
                hit.kill()

        self.replay_log.append(ReplayEvent(self.simulation_tick, p1.position, p2.position))
        self.simulation_tick += 1

        if dead[1] or dead[2]:
            self._finish_round(dead[1], dead[2])

    def _finish_round(self, p1_dead: bool, p2_dead: bool) -> None:
        p1, p2 = self.players
        self.state = GameState.ROUND_OVER
        duration = time.time() - self.match.round_start_time

        if p1_dead and p2_dead:
            self.winner = None
            crash = "Double crash"
            self.particles.emit_explosion(p1.position, RED)
            self.particles.emit_explosion(p2.position, RED)
        elif p1_dead:
            self.winner = p2
            p2.score += 1
            self.match.p2_round_wins += 1
            crash = "Player 1 collided"
            self.particles.emit_explosion(p1.position, p1.color)
        else:
            self.winner = p1
            p1.score += 1
            self.match.p1_round_wins += 1
            crash = "Player 2 collided"
            self.particles.emit_explosion(p2.position, p2.color)

        self.audio.play("collision")
        self.match.rounds_played += 1
        self.round_stats = RoundStats(
            winner_name=self.winner.name if self.winner else None,
            winner_color=self.winner.color if self.winner else None,
            crash_type=crash,
            duration_seconds=duration,
            p1_cells=len(p1.trail),
            p2_cells=len(p2.trail),
        )

        if self.settings.display.screen_shake:
            self.screen_shake_frames = 18
            self.screen_shake_magnitude = 6

        if self._is_match_complete():
            self._persist_high_score()
            self._save_replay()
            self.state = GameState.GAME_OVER

    def _is_match_complete(self) -> bool:
        if self.settings.game_mode == GameMode.TOURNAMENT:
            target = self.settings.rounds_to_win
            return self.match.p1_round_wins >= target or self.match.p2_round_wins >= target
        return self.match.rounds_played >= 1

    def _advance_after_round(self) -> None:
        if self.state == GameState.GAME_OVER:
            self.state = GameState.MAIN_MENU
        else:
            self.reset_round()

    def _persist_high_score(self) -> None:
        scores = load_json(SCORES_FILE, [])
        duration = time.time() - self.match.start_time
        label = self.winner.name if self.winner else "Draw"
        entry = {
            "name": label,
            "mode": self.settings.game_mode.value,
            "rounds": self.match.rounds_played,
            "duration_seconds": round(duration, 2),
            "p1_score": self.players[0].score,
            "p2_score": self.players[1].score,
            "timestamp": int(time.time()),
        }
        scores.append(entry)
        scores.sort(key=lambda row: (row["p1_score"], row["p2_score"], -row["duration_seconds"]), reverse=True)
        save_json(SCORES_FILE, scores[:20])

    def _save_replay(self) -> None:
        from .utils import REPLAY_DIR, save_json

        replay_path = REPLAY_DIR / f"match_{int(time.time())}.json"
        payload = {
            "mode": self.settings.game_mode.value,
            "events": [{"tick": ev.tick, "p1": ev.p1, "p2": ev.p2} for ev in self.replay_log],
        }
        save_json(replay_path, payload)

    def _render(self) -> None:
        shake_x = shake_y = 0
        if self.screen_shake_frames > 0:
            self.screen_shake_frames -= 1
            shake_x = int(pygame.time.get_ticks() % self.screen_shake_magnitude) - self.screen_shake_magnitude // 2
            shake_y = int((pygame.time.get_ticks() // 2) % self.screen_shake_magnitude) - self.screen_shake_magnitude // 2

        frame = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        if self.state == GameState.MAIN_MENU:
            self.main_menu.render(frame, self.title_font, self.body_font)
        elif self.state == GameState.PAUSED:
            self._render_playfield(frame)
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 135))
            frame.blit(overlay, (0, 0))
            self.pause_menu.render(frame, self.title_font, self.body_font)
        elif self.state == GameState.SETTINGS:
            self._render_settings(frame)
        elif self.state == GameState.HIGH_SCORES:
            self._render_scores(frame)
        else:
            self._render_playfield(frame)
            if self.state in {GameState.ROUND_OVER, GameState.GAME_OVER}:
                self._render_round_overlay(frame)

        self.screen.fill((0, 0, 0))
        self.screen.blit(frame, (shake_x, shake_y))
        pygame.display.flip()

    def _render_playfield(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        if self.settings.display.show_grid:
            self._draw_parallax_grid(surface)

        glow_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        for player in self.players:
            self._draw_trail(glow_layer, player)
            self._draw_head(glow_layer, player)

        for powerup in self.powerups:
            glow = pygame.Surface((GRID_SIZE * 3, GRID_SIZE * 3), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*GREEN, 60), (GRID_SIZE + 5, GRID_SIZE + 5), GRID_SIZE)
            glow_layer.blit(glow, (powerup.rect.x - GRID_SIZE, powerup.rect.y - GRID_SIZE))

        surface.blit(glow_layer, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        self.powerups.draw(surface)
        self.projectiles.draw(surface)
        self.particles.draw(surface)
        self._render_hud(surface)

    def _draw_parallax_grid(self, surface: pygame.Surface) -> None:
        self.grid_offset[0] = (self.grid_offset[0] + 0.3) % (GRID_SIZE * 2)
        self.grid_offset[1] = (self.grid_offset[1] + 0.15) % (GRID_SIZE * 2)
        ox = int(self.grid_offset[0])
        oy = int(self.grid_offset[1])

        for x in range(-GRID_SIZE * 2, SCREEN_WIDTH + GRID_SIZE * 2, GRID_SIZE * 2):
            strong = ((x // (GRID_SIZE * 2)) % 6) == 0
            color = GRID_GLOW if strong else GRID_COLOR
            alpha = 85 if strong else 45
            pygame.draw.line(surface, (*color, alpha), (x - ox, 0), (x - ox, SCREEN_HEIGHT), 1)
        for y in range(-GRID_SIZE * 2, SCREEN_HEIGHT + GRID_SIZE * 2, GRID_SIZE * 2):
            strong = ((y // (GRID_SIZE * 2)) % 6) == 0
            color = GRID_GLOW if strong else GRID_COLOR
            alpha = 85 if strong else 45
            pygame.draw.line(surface, (*color, alpha), (0, y - oy), (SCREEN_WIDTH, y - oy), 1)

    def _draw_trail(self, surface: pygame.Surface, player: LightCycle) -> None:
        trail = player.trail
        total = max(1, len(trail))
        for idx, cell in enumerate(trail):
            fade_alpha = int(50 + 180 * ((idx + 1) / total)) if self.settings.display.trail_fade else 220
            rect = pygame.Rect(cell[0], cell[1], GRID_SIZE, GRID_SIZE)
            self._draw_glow_rect(surface, player.glow_color, rect, 3, 8, max(25, fade_alpha // 2))
            pygame.draw.rect(surface, (*player.color, fade_alpha), rect, border_radius=2)

    def _draw_head(self, surface: pygame.Surface, player: LightCycle) -> None:
        rect = pygame.Rect(player.position[0], player.position[1], GRID_SIZE, GRID_SIZE)
        color = YELLOW if player.has_shield else player.color
        self._draw_glow_rect(surface, color, rect, 4, 10, 170)
        pygame.draw.rect(surface, (*color, 255), rect, border_radius=3)

    @staticmethod
    def _draw_glow_rect(
        surface: pygame.Surface,
        color: tuple[int, int, int],
        rect: pygame.Rect,
        layers: int,
        spread: int,
        alpha: int,
    ) -> None:
        for i in range(layers, 0, -1):
            inflate = i * spread
            glow_rect = rect.inflate(inflate, inflate)
            glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            pygame.draw.rect(glow, (*color, max(8, alpha // (i + 1))), glow.get_rect(), border_radius=4)
            surface.blit(glow, glow_rect.topleft)

    def _render_hud(self, surface: pygame.Surface) -> None:
        title = self.title_font.render("GASTRON", True, YELLOW)
        title_shadow = self.title_font.render("GASTRON", True, SHADOW_COLOR)
        surface.blit(title_shadow, (24, 19))
        surface.blit(title, (20, 15))

        p1, p2 = self.players
        lines = [
            (f"P1 (Arrows) score: {p1.score} ammo:{p1.ammo}", p1.color),
            (f"P2 (WASD) score: {p2.score} ammo:{p2.ammo}", p2.color),
            (f"Mode: {self.settings.game_mode.value.replace('_', ' ').title()}", ORANGE),
            (f"AI: {self.settings.ai_difficulty.value.title()}", ORANGE),
        ]
        for idx, (line, color) in enumerate(lines):
            text = self.small_font.render(line, True, color)
            surface.blit(text, (20, 82 + idx * 22))

        helper = self.small_font.render("ESC Pause | Space Continue | Shoot: RightCtrl / LeftShift", True, TEXT_COLOR)
        surface.blit(helper, (20, SCREEN_HEIGHT - 28))

        if self.flash_timer > 0 and self.flash_message:
            msg = self.body_font.render(self.flash_message, True, GREEN)
            surface.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 20))

    def _render_round_overlay(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 8, 16, 165))
        surface.blit(overlay, (0, 0))

        if not self.round_stats:
            return

        if self.state == GameState.GAME_OVER:
            headline = "MATCH COMPLETE"
        else:
            headline = self.round_stats.winner_name.upper() + " WINS" if self.round_stats.winner_name else "DOUBLE CRASH"

        line1 = self.title_font.render(headline, True, YELLOW)
        line2 = self.body_font.render(self.round_stats.crash_type, True, TEXT_COLOR)
        line3 = self.small_font.render(
            f"Round time: {self.round_stats.duration_seconds:.1f}s | Trails P1/P2: {self.round_stats.p1_cells}/{self.round_stats.p2_cells}",
            True,
            ORANGE,
        )
        prompt = self.small_font.render("Press Space/Enter", True, TEXT_COLOR)

        surface.blit(line1, (SCREEN_WIDTH // 2 - line1.get_width() // 2, SCREEN_HEIGHT // 2 - 110))
        surface.blit(line2, (SCREEN_WIDTH // 2 - line2.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
        surface.blit(line3, (SCREEN_WIDTH // 2 - line3.get_width() // 2, SCREEN_HEIGHT // 2 - 18))
        surface.blit(prompt, (SCREEN_WIDTH // 2 - prompt.get_width() // 2, SCREEN_HEIGHT // 2 + 42))

    def _render_settings(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        title = self.title_font.render("SETTINGS", True, YELLOW)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 56))

        lines = [
            f"Difficulty [D]: {self.settings.ai_difficulty.value.title()}",
            f"Master Volume [1/2]: {self.settings.master_volume:.2f}",
            f"Music Volume [3/4]: {self.settings.music_volume:.2f}",
            f"SFX Volume [5/6]: {self.settings.sfx_volume:.2f}",
            f"Show Grid [G]: {self.settings.display.show_grid}",
            f"Screen Shake [H]: {self.settings.display.screen_shake}",
            f"Trail Fade [F]: {self.settings.display.trail_fade}",
            "Back: ESC or Backspace",
        ]
        for idx, line in enumerate(lines):
            text = self.body_font.render(line, True, TEXT_COLOR)
            surface.blit(text, (120, 180 + idx * 45))

    def _render_scores(self, surface: pygame.Surface) -> None:
        surface.fill(BG_COLOR)
        title = self.title_font.render("HIGH SCORES", True, YELLOW)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 56))

        scores = load_json(SCORES_FILE, [])
        headers = self.small_font.render("Name | Mode | Rounds | P1 | P2 | Duration(s)", True, ORANGE)
        surface.blit(headers, (120, 140))
        for idx, entry in enumerate(scores[:12]):
            line = f"{entry['name']:<10} {entry['mode']:<11} {entry['rounds']:<6} {entry['p1_score']:<3} {entry['p2_score']:<3} {entry['duration_seconds']:<7}"
            text = self.small_font.render(line, True, TEXT_COLOR)
            surface.blit(text, (120, 175 + idx * 30))

        prompt = self.small_font.render("Backspace / ESC to return", True, TEXT_COLOR)
        surface.blit(prompt, (120, SCREEN_HEIGHT - 40))


def detect_round_collision(
    next_positions: dict[int, tuple[int, int]],
    occupied: Iterable[tuple[int, int]],
    shields: dict[int, bool],
    current_positions: dict[int, tuple[int, int]],
) -> dict[int, bool]:
    """Pure helper used by tests to validate collision behavior."""
    occupied_set = set(occupied)
    dead = {1: False, 2: False}

    n1 = next_positions[1]
    n2 = next_positions[2]
    if n1 == n2 or (n1 == current_positions[2] and n2 == current_positions[1]):
        dead[1] = True
        dead[2] = True

    for pid in (1, 2):
        nxt = next_positions[pid]
        if not in_bounds(nxt):
            dead[pid] = True
        elif nxt in occupied_set and not shields[pid]:
            dead[pid] = True
    return dead
