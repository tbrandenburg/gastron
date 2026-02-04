from __future__ import annotations

import pygame

from gastron.player import LightCycle


def _player() -> LightCycle:
    pygame.init()
    return LightCycle(
        player_id=1,
        name="P1",
        color=(1, 2, 3),
        glow_color=(4, 5, 6),
        controls={pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)},
        shoot_key=pygame.K_RCTRL,
        start_pos=(100, 100),
        start_dir=(1, 0),
    )


def test_player_prevents_reverse_turn() -> None:
    player = _player()
    player.queue_turn(pygame.K_LEFT)
    assert player.pending_direction is None


def test_player_next_position() -> None:
    player = _player()
    assert player.next_position() == (110, 100)


def test_trail_eraser_removes_segments() -> None:
    player = _player()
    player.trail = [(x, 0) for x in range(0, 100, 10)]
    player.trail_set = set(player.trail)
    player.consume_trail_segment(4)
    assert len(player.trail) == 6
    assert (0, 0) not in player.trail_set
