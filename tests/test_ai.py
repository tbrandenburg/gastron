from __future__ import annotations

from gastron.ai import GameSnapshot, TronAI
from gastron.settings import AIDifficulty


def test_easy_ai_stays_in_safe_space() -> None:
    ai = TronAI(AIDifficulty.EASY)
    snapshot = GameSnapshot(
        ai_position=(100, 100),
        ai_direction=(1, 0),
        opponent_position=(200, 100),
        occupied={(110, 100)},
    )
    move = ai.choose_direction(snapshot)
    assert move != (1, 0)


def test_hard_ai_prefers_space_over_dead_end() -> None:
    ai = TronAI(AIDifficulty.HARD)
    occupied = {(110, 100), (100, 90), (100, 80), (100, 70)}
    snapshot = GameSnapshot(
        ai_position=(100, 100),
        ai_direction=(1, 0),
        opponent_position=(600, 200),
        occupied=occupied,
    )
    move = ai.choose_direction(snapshot)
    assert move in {(0, 1), (-1, 0)}


def test_hard_ai_shoots_when_aligned() -> None:
    ai = TronAI(AIDifficulty.HARD)
    snapshot = GameSnapshot(
        ai_position=(200, 200),
        ai_direction=(1, 0),
        opponent_position=(200, 400),
        occupied=set(),
    )
    assert ai.should_shoot(snapshot, ammo=1)
