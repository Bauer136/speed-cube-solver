"""A rough execution-time model for ranking solutions the way a human would.

Each move has an estimated time in seconds for a fast cuber executing
without pauses: R and U are the quickest finger tricks, L, F and D are a
bit slower, B is awkward, and half turns take longer than quarter turns.
Rotations cost a little (they are free during inspection, which is not
scored). Recognition and look-ahead pauses are not modelled, so the total
is a lower bound on a real solve, useful for comparing solutions rather
than as a prediction.
"""

from __future__ import annotations

from typing import Iterable

from .notation import Move

QUARTER_TURN_TIME = {
    "R": 0.08, "U": 0.08, "L": 0.10, "F": 0.12, "D": 0.12, "B": 0.20,
    "r": 0.09, "u": 0.11, "l": 0.11, "f": 0.14, "d": 0.14, "b": 0.22,
    "M": 0.12, "E": 0.20, "S": 0.20,
    "x": 0.15, "y": 0.15, "z": 0.25,
}
HALF_TURN_FACTOR = 1.4


def move_time(move: Move) -> float:
    base = QUARTER_TURN_TIME[move.name]
    return base * HALF_TURN_FACTOR if move.turns == 2 else base


def execution_time(moves: Iterable[Move]) -> float:
    """Estimated seconds to execute ``moves``."""
    return sum(move_time(m) for m in moves)
