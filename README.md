# Gastron

Gastron is a production-ready Tron lightcycle game built with pygame.

## Features
- Single-player vs AI (easy/medium/hard), 2-player local, and tournament mode (best-of-N)
- Power-ups: speed boost, shield, trail eraser, and pulse weapon pickup
- State-machine architecture with main menu, pause menu, settings, high scores, and game-over screens
- Neon trail rendering with glow + fade, particle explosions, parallax grid, and screen shake
- Persistent settings, high-score JSON storage, and replay snapshots

## Controls
- Player 1: Arrow keys
- Player 2: WASD
- Shoot: Right Ctrl (P1), Left Shift (P2)
- General: ESC pause/back, Enter/Space select/continue

## Run
```bash
python tron.py
```

Or as a package:
```bash
pip install -e .
gastron
```

## Settings Screen Shortcuts
- `D`: cycle AI difficulty
- `1/2`: master volume down/up
- `3/4`: music volume down/up
- `5/6`: SFX volume down/up
- `G`: toggle grid
- `H`: toggle screen shake
- `F`: toggle trail fade

## Audio Assets (optional)
Drop files in:
- `assets/music/theme.ogg`
- `assets/sounds/collision.wav`
- `assets/sounds/powerup.wav`
- `assets/sounds/menu.wav`
- `assets/sounds/shoot.wav`

The game runs without them using graceful fallback.

## Testing
```bash
pytest
```

## Project Layout
- `src/gastron/game.py`: state machine and loop
- `src/gastron/player.py`: lightcycle + projectile entities
- `src/gastron/ai.py`: AI behaviors
- `src/gastron/powerups.py`: power-up system
- `src/gastron/particles.py`: particle effects
- `src/gastron/menu.py`: menu UI components
- `src/gastron/settings.py`: persistence for settings and controls
- `src/gastron/audio.py`: music and SFX management
