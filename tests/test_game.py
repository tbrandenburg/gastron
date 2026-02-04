from __future__ import annotations

import tempfile
from pathlib import Path

from gastron.game import detect_round_collision
from gastron.settings import SettingsManager
from gastron.utils import save_json, load_json


def test_collision_head_on_kills_both() -> None:
    dead = detect_round_collision(
        next_positions={1: (100, 100), 2: (100, 100)},
        occupied=set(),
        shields={1: False, 2: False},
        current_positions={1: (90, 100), 2: (110, 100)},
    )
    assert dead == {1: True, 2: True}


def test_collision_shield_ignores_trail() -> None:
    dead = detect_round_collision(
        next_positions={1: (100, 100), 2: (200, 200)},
        occupied={(100, 100)},
        shields={1: True, 2: False},
        current_positions={1: (90, 100), 2: (190, 200)},
    )
    assert dead[1] is False


def test_settings_load_save_round_trip(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        from gastron import utils

        monkeypatch.setattr(utils, "DATA_DIR", Path(tmp))
        monkeypatch.setattr(utils, "SETTINGS_FILE", Path(tmp) / "settings.json")
        monkeypatch.setattr(utils, "REPLAY_DIR", Path(tmp) / "replays")

        mgr = SettingsManager()
        mgr.settings.tournament_best_of = 7
        mgr.save()

        loaded = SettingsManager()
        assert loaded.settings.tournament_best_of == 7


def test_json_helpers() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x.json"
        save_json(p, {"ok": True})
        assert load_json(p, {}) == {"ok": True}


def test_integration_round_transition_to_game_over(monkeypatch) -> None:
    import os
    from pathlib import Path

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    from gastron.game import GameState, TronGame

    game = TronGame(root=Path.cwd())
    game.reset_match()
    p1, p2 = game.players

    p1.position = (0, 0)
    p1.direction = (-1, 0)
    p2.position = (200, 200)
    p2.direction = (1, 0)

    game._simulate_step()
    assert game.state in {GameState.ROUND_OVER, GameState.GAME_OVER}
