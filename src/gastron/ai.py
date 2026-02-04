"""AI decision logic for single-player mode."""

from __future__ import annotations

from dataclasses import dataclass
import random

from .settings import AIDifficulty
from .utils import DIRECTIONS, Direction, Position, add_direction, in_bounds, is_opposite


@dataclass(slots=True)
class GameSnapshot:
    """Small, testable snapshot of board state for AI."""

    ai_position: Position
    ai_direction: Direction
    opponent_position: Position
    occupied: set[Position]


class TronAI:
    """Difficulty-scaled AI for steering and aggression."""

    def __init__(self, difficulty: AIDifficulty) -> None:
        self.difficulty = difficulty

    def choose_direction(self, snapshot: GameSnapshot) -> Direction:
        """Choose next direction according to configured difficulty."""
        if self.difficulty == AIDifficulty.EASY:
            return self._easy(snapshot)
        if self.difficulty == AIDifficulty.MEDIUM:
            return self._medium(snapshot)
        return self._hard(snapshot)

    def should_shoot(self, snapshot: GameSnapshot, ammo: int) -> bool:
        """Use weapons aggressively on hard, opportunistically on medium."""
        if ammo <= 0:
            return False
        aligned = (
            snapshot.ai_position[0] == snapshot.opponent_position[0]
            or snapshot.ai_position[1] == snapshot.opponent_position[1]
        )
        if self.difficulty == AIDifficulty.HARD:
            return aligned
        if self.difficulty == AIDifficulty.MEDIUM:
            return aligned and random.random() < 0.4
        return False

    def _easy(self, snapshot: GameSnapshot) -> Direction:
        safe = self._safe_directions(snapshot, look_ahead=1)
        if not safe:
            return snapshot.ai_direction
        if snapshot.ai_direction in safe and random.random() < 0.65:
            return snapshot.ai_direction
        return random.choice(safe)

    def _medium(self, snapshot: GameSnapshot) -> Direction:
        options = self._safe_directions(snapshot, look_ahead=3)
        if not options:
            return snapshot.ai_direction
        scored = sorted(options, key=lambda d: self._space_score(snapshot, d, depth=4), reverse=True)
        return scored[0]

    def _hard(self, snapshot: GameSnapshot) -> Direction:
        options = self._safe_directions(snapshot, look_ahead=4)
        if not options:
            return snapshot.ai_direction
        scored: list[tuple[float, Direction]] = []
        for option in options:
            space = self._space_score(snapshot, option, depth=6)
            next_pos = add_direction(snapshot.ai_position, option)
            aggression = -self._manhattan(next_pos, snapshot.opponent_position) * 0.35
            scored.append((space + aggression, option))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _safe_directions(self, snapshot: GameSnapshot, look_ahead: int) -> list[Direction]:
        safe: list[Direction] = []
        for direction in DIRECTIONS:
            if is_opposite(direction, snapshot.ai_direction):
                continue
            position = snapshot.ai_position
            blocked = False
            for _ in range(look_ahead):
                position = add_direction(position, direction)
                if position in snapshot.occupied or not in_bounds(position):
                    blocked = True
                    break
            if not blocked:
                safe.append(direction)
        return safe

    def _space_score(self, snapshot: GameSnapshot, direction: Direction, depth: int) -> int:
        start = add_direction(snapshot.ai_position, direction)
        if not in_bounds(start) or start in snapshot.occupied:
            return -9999
        frontier = [start]
        visited = {start}
        score = 0
        steps = 0
        while frontier and steps < depth * 40:
            current = frontier.pop(0)
            score += 1
            for candidate in DIRECTIONS:
                nxt = add_direction(current, candidate)
                if nxt in visited or nxt in snapshot.occupied or not in_bounds(nxt):
                    continue
                visited.add(nxt)
                frontier.append(nxt)
            steps += 1
        return score

    @staticmethod
    def _manhattan(a: Position, b: Position) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
