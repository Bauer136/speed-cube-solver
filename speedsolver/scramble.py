"""Random-move scrambles in WCA notation."""

from __future__ import annotations

import random

from .notation import FACE_MOVES, format_moves, Move

_AXIS = {"U": 0, "D": 0, "R": 1, "L": 1, "F": 2, "B": 2}


def random_scramble(length: int = 20, rng: random.Random | None = None) -> str:
    """A scramble with no repeated face and no ``R L R``-style redundancy."""
    rng = rng or random.Random()
    moves: list[Move] = []
    while len(moves) < length:
        face = rng.choice(FACE_MOVES)
        if moves and moves[-1].name == face:
            continue
        if len(moves) >= 2 and _AXIS[moves[-1].name] == _AXIS[face] == _AXIS[moves[-2].name]:
            continue
        moves.append(Move(face, rng.choice((1, 2, 3))))
    return format_moves(moves)
