"""Executable entrypoint for Gastron."""

from __future__ import annotations

from pathlib import Path

from .game import TronGame


def main() -> None:
    """Launch the game."""
    root = Path(__file__).resolve().parents[2]
    TronGame(root=root).run()


if __name__ == "__main__":
    main()
