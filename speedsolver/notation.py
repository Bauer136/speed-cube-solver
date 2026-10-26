"""WCA move notation: parsing, formatting, inverting and cancelling moves."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

FACE_MOVES = "URFDLB"
SLICE_MOVES = "MES"
ROTATIONS = "xyz"
WIDE_MOVES = "urfdlb"
ALL_NAMES = FACE_MOVES + SLICE_MOVES + ROTATIONS + WIDE_MOVES

_TOKEN = re.compile(r"([URFDLB]w|[URFDLBMESxyzurfdlb])(\d*)(['’]?)")


@dataclass(frozen=True)
class Move:
    """A single move. ``turns`` is the clockwise quarter-turn count: 1, 2 or 3."""

    name: str
    turns: int = 1

    def __post_init__(self) -> None:
        if self.name not in ALL_NAMES:
            raise ValueError(f"unknown move {self.name!r}")
        if self.turns not in (1, 2, 3):
            raise ValueError(f"turns must be 1, 2 or 3, got {self.turns}")

    @property
    def is_rotation(self) -> bool:
        return self.name in ROTATIONS

    def inverse(self) -> Move:
        return Move(self.name, 4 - self.turns)

    def __str__(self) -> str:
        return self.name + {1: "", 2: "2", 3: "'"}[self.turns]

    def __repr__(self) -> str:
        return f"Move({self})"


def parse_moves(text: str) -> list[Move]:
    """Parse a scramble or algorithm such as ``"R U R' U' F2 Rw x'"``.

    Spaces are optional. ``Rw`` is read as ``r``. Parentheses are ignored so
    algorithms can be pasted with their usual triggers grouping.
    """
    text = text.replace("(", " ").replace(")", " ").strip()
    moves: list[Move] = []
    pos = 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
            continue
        match = _TOKEN.match(text, pos)
        if not match:
            raise ValueError(f"cannot read move at {text[pos:]!r}")
        name, amount, prime = match.groups()
        if name.endswith("w"):
            name = name[0].lower()
        count = int(amount) if amount else 1
        if prime:
            count = -count
        if count % 4:
            moves.append(Move(name, count % 4))
        pos = match.end()
    return moves


def as_moves(moves: str | Iterable[Move]) -> list[Move]:
    return parse_moves(moves) if isinstance(moves, str) else list(moves)


def format_moves(moves: Iterable[Move]) -> str:
    return " ".join(str(m) for m in moves)


def invert(moves: Iterable[Move]) -> list[Move]:
    return [m.inverse() for m in reversed(list(moves))]


def cancel(moves: Iterable[Move]) -> list[Move]:
    """Merge consecutive moves of the same layer (``U U'`` -> nothing, ``R R`` -> ``R2``)."""
    out: list[Move] = []
    for move in moves:
        if out and out[-1].name == move.name:
            turns = (out.pop().turns + move.turns) % 4
            if turns:
                out.append(Move(move.name, turns))
        else:
            out.append(move)
    return out
