"""Menu rendering and navigation helpers."""

from __future__ import annotations

from dataclasses import dataclass
import pygame

from .utils import BG_COLOR, SHADOW_COLOR, TEXT_COLOR, YELLOW


@dataclass(slots=True)
class MenuItem:
    """Single selectable menu row."""

    label: str
    action: str


class Menu:
    """Simple vertical keyboard-driven menu."""

    def __init__(self, title: str, items: list[MenuItem]) -> None:
        self.title = title
        self.items = items
        self.selected_index = 0

    def move(self, delta: int) -> None:
        """Move menu selection by delta."""
        self.selected_index = (self.selected_index + delta) % len(self.items)

    def current_action(self) -> str:
        """Return selected action key."""
        return self.items[self.selected_index].action

    def render(self, surface: pygame.Surface, title_font: pygame.font.Font, body_font: pygame.font.Font) -> None:
        """Draw menu screen contents."""
        surface.fill(BG_COLOR)
        title_shadow = title_font.render(self.title, True, SHADOW_COLOR)
        title = title_font.render(self.title, True, YELLOW)
        surface.blit(title_shadow, (surface.get_width() // 2 - title.get_width() // 2 + 3, 85))
        surface.blit(title, (surface.get_width() // 2 - title.get_width() // 2, 82))

        start_y = 230
        for idx, item in enumerate(self.items):
            selected = idx == self.selected_index
            color = YELLOW if selected else TEXT_COLOR
            prefix = "> " if selected else "  "
            line = body_font.render(f"{prefix}{item.label}", True, color)
            x = surface.get_width() // 2 - line.get_width() // 2
            y = start_y + idx * 42
            surface.blit(line, (x, y))
