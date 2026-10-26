"""Solutions broken into named method stages, plus how they are scored."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from .ergonomics import execution_time
from .notation import Move, format_moves


def stm(moves: Iterable[Move]) -> int:
    """Slice turn metric: every face, slice or wide turn counts 1; rotations are free."""
    return sum(1 for m in moves if not m.is_rotation)


def htm(moves: Iterable[Move]) -> int:
    """Half turn metric: slice turns count 2 (they are two outer turns); rotations free."""
    return sum(2 if m.name in "MES" else 1 for m in moves if not m.is_rotation)


def qtm(moves: Iterable[Move]) -> int:
    """Quarter turn metric: half turns count 2, slices count double; rotations free."""
    return sum(
        (2 if m.turns == 2 else 1) * (2 if m.name in "MES" else 1)
        for m in moves
        if not m.is_rotation
    )


METRICS: dict[str, Callable[[Iterable[Move]], float]] = {
    "TIME": execution_time, "STM": stm, "HTM": htm, "QTM": qtm,
}
DEFAULT_METRIC = "TIME"
"""Solutions are ranked by estimated execution time; move counts are shown alongside."""


def format_score(moves: list[Move]) -> str:
    return f"{stm(moves)} STM, ~{execution_time(moves):.1f} s"


@dataclass
class Stage:
    name: str
    moves: list[Move]
    detail: str = ""  # e.g. the case recognised or the slot inserted
    free: bool = False  # not scored, e.g. rotations during inspection


def scored_moves(stages: Iterable[Stage]) -> list[Move]:
    return [m for s in stages if not s.free for m in s.moves]


@dataclass
class Solution:
    method: str
    stages: list[Stage] = field(default_factory=list)
    variant: str = ""  # e.g. "white cross"

    @property
    def moves(self) -> list[Move]:
        return [m for s in self.stages for m in s.moves]

    @property
    def scored_moves(self) -> list[Move]:
        """The moves that count: everything except inspection."""
        return scored_moves(self.stages)

    def length(self, metric: str = DEFAULT_METRIC) -> float:
        return METRICS[metric](self.scored_moves)

    def score(self) -> str:
        """Human-readable score, e.g. ``"41 STM, ~3.9 s"``."""
        return format_score(self.scored_moves)

    def __str__(self) -> str:
        width = max((len(s.name) for s in self.stages), default=0)
        variant = f" ({self.variant})" if self.variant else ""
        lines = [f"{self.method}{variant}: {self.score()}"]
        lines += [f"  {s.name:<{width}}  {format_moves(s.moves)}" for s in self.stages]
        return "\n".join(lines)


def join_stages(stages: list[Stage]) -> list[Stage]:
    """Cancel moves across stage boundaries (``... U`` + ``U' ...``).

    A merged move stays in the earlier stage. Empty stages (skips) are kept
    so the solution still shows every step of the method.
    """
    out: list[Stage] = []
    for stage in stages:
        moves = list(stage.moves)
        while moves:
            prev = next((s for s in reversed(out) if s.moves), None)
            if prev is None or prev.moves[-1].name != moves[0].name:
                break
            first = moves.pop(0)
            turns = (prev.moves.pop().turns + first.turns) % 4
            if turns:
                prev.moves.append(Move(first.name, turns))
                break
        out.append(Stage(stage.name, moves, stage.detail, stage.free))
    return out
