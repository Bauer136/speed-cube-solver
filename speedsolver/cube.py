"""Sticker-level model of a 3x3 cube.

Each of the 54 sticker slots is described by the position of its cubie and
the outward normal of the sticker. Every move (face turns, slices, wide turns
and rotations) is generated from that geometry by one rule: rotate the
stickers whose cubie lies in the turning layers.

Coordinates: x points right, y up, z towards the viewer (the F face).
Faces are ordered U R F D L B and each face's nine slots are numbered
row-major as the face appears on a standard net.
"""

from __future__ import annotations

from typing import Iterable

from .notation import Move, as_moves

Vec = tuple[int, int, int]

FACES = "URFDLB"
U, R, F, D, L, B = range(6)

# (normal, right, down) for each face as seen on a standard net.
_FACE_FRAMES: dict[str, tuple[Vec, Vec, Vec]] = {
    "U": ((0, 1, 0), (1, 0, 0), (0, 0, 1)),
    "R": ((1, 0, 0), (0, 0, -1), (0, -1, 0)),
    "F": ((0, 0, 1), (1, 0, 0), (0, -1, 0)),
    "D": ((0, -1, 0), (1, 0, 0), (0, 0, -1)),
    "L": ((-1, 0, 0), (0, 0, 1), (0, -1, 0)),
    "B": ((0, 0, -1), (-1, 0, 0), (0, -1, 0)),
}


def _build_slots() -> list[tuple[Vec, Vec]]:
    slots = []
    for face in FACES:
        n, r, d = _FACE_FRAMES[face]
        for row in range(3):
            for col in range(3):
                pos = tuple(n[i] + (col - 1) * r[i] + (row - 1) * d[i] for i in range(3))
                slots.append((pos, n))
    return slots


SLOTS: list[tuple[Vec, Vec]] = _build_slots()
"""``SLOTS[i] = (cubie position, sticker normal)``."""
SLOT_INDEX: dict[tuple[Vec, Vec], int] = {s: i for i, s in enumerate(SLOTS)}
CENTER_SLOTS = tuple(9 * f + 4 for f in range(6))


def slot_at(pos: Vec, normal: Vec) -> int:
    return SLOT_INDEX[(pos, normal)]


def _group_pieces() -> list[tuple[int, ...]]:
    by_pos: dict[Vec, list[int]] = {}
    for i, (pos, _) in enumerate(SLOTS):
        by_pos.setdefault(pos, []).append(i)
    return [tuple(v) for v in by_pos.values()]


PIECES: list[tuple[int, ...]] = _group_pieces()
"""Sticker slots grouped by cubie (6 centers, 12 edges, 8 corners)."""
PIECE_OF_SLOT: list[tuple[int, ...]] = [()] * 54
for _piece in PIECES:
    for _s in _piece:
        PIECE_OF_SLOT[_s] = _piece
EDGE_SLOTS = tuple(sorted(s for p in PIECES if len(p) == 2 for s in p))
CORNER_SLOTS = tuple(sorted(s for p in PIECES if len(p) == 3 for s in p))


def _rotate_cw(v: Vec, axis: int) -> Vec:
    """Rotate ``v`` a quarter turn clockwise as seen looking from +axis."""
    x, y, z = v
    if axis == 0:
        return (x, z, -y)
    if axis == 1:
        return (-z, y, x)
    return (y, -x, z)


# name -> (axis, layers that turn, +1 if clockwise seen from +axis else -1)
MOVE_GEOMETRY: dict[str, tuple[int, tuple[int, ...], int]] = {
    "R": (0, (1,), 1), "L": (0, (-1,), -1), "M": (0, (0,), -1),
    "r": (0, (0, 1), 1), "l": (0, (-1, 0), -1), "x": (0, (-1, 0, 1), 1),
    "U": (1, (1,), 1), "D": (1, (-1,), -1), "E": (1, (0,), -1),
    "u": (1, (0, 1), 1), "d": (1, (-1, 0), -1), "y": (1, (-1, 0, 1), 1),
    "F": (2, (1,), 1), "B": (2, (-1,), -1), "S": (2, (0,), 1),
    "f": (2, (0, 1), 1), "b": (2, (-1, 0), -1), "z": (2, (-1, 0, 1), 1),
}


def _build_dest(name: str, turns: int) -> tuple[int, ...]:
    axis, layers, direction = MOVE_GEOMETRY[name]
    quarters = (turns * direction) % 4
    dest = []
    for pos, normal in SLOTS:
        if pos[axis] in layers:
            for _ in range(quarters):
                pos, normal = _rotate_cw(pos, axis), _rotate_cw(normal, axis)
        dest.append(SLOT_INDEX[(pos, normal)])
    return tuple(dest)


MOVE_DEST: dict[Move, tuple[int, ...]] = {
    Move(name, t): _build_dest(name, t) for name in MOVE_GEOMETRY for t in (1, 2, 3)
}
"""``MOVE_DEST[move][i]`` is the slot the sticker in slot ``i`` moves to."""
_MOVE_SRC: dict[Move, tuple[int, ...]] = {}
for _move, _dest in MOVE_DEST.items():
    _src = [0] * 54
    for _i, _d in enumerate(_dest):
        _src[_d] = _i
    _MOVE_SRC[_move] = tuple(_src)


def _home_keys() -> dict[tuple[frozenset[int], int], int]:
    return {
        (frozenset(s // 9 for s in PIECE_OF_SLOT[h]), h // 9): h for h in range(54)
    }


_HOME_BY_KEY = _home_keys()


class Cube:
    """An immutable cube state.

    ``stickers[slot]`` is the id of the sticker in that slot; a sticker id is
    the slot it occupies on a solved cube, so its color is ``id // 9``.
    """

    __slots__ = ("stickers",)

    def __init__(self, stickers: Iterable[int] | None = None) -> None:
        self.stickers: tuple[int, ...] = tuple(range(54)) if stickers is None else tuple(stickers)

    def apply(self, moves: str | Iterable[Move]) -> Cube:
        s = self.stickers
        for move in as_moves(moves):
            src = _MOVE_SRC[move]
            s = tuple(s[i] for i in src)
        return Cube(s)

    def colors(self) -> tuple[int, ...]:
        """Face index (0-5, ``U R F D L B`` of the solved cube) of every slot's color."""
        return tuple(s // 9 for s in self.stickers)

    def is_solved(self) -> bool:
        """True if every face shows one color, whatever the cube's orientation."""
        c = self.colors()
        return all(len(set(c[9 * f:9 * f + 9])) == 1 for f in range(6))

    def normalized(self) -> Cube:
        """The same state relabelled so its centers are home.

        The solver turns only outer faces, so it works in the frame of the
        current centers: a sticker's id becomes the slot it belongs in
        relative to those centers. Turning the result solved with face
        moves solves the original cube.
        """
        c = self.colors()
        face_of_color = {c[9 * f + 4]: f for f in range(6)}
        rel = [face_of_color[x] for x in c]
        return Cube(
            _HOME_BY_KEY[(frozenset(rel[s] for s in PIECE_OF_SLOT[i]), rel[i])] for i in range(54)
        )

    def locate(self, sticker: int) -> int:
        """Slot currently holding ``sticker``."""
        return self.stickers.index(sticker)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Cube) and self.stickers == other.stickers

    def __hash__(self) -> int:
        return hash(self.stickers)

    def __repr__(self) -> str:
        c = self.colors()
        return "Cube(" + " ".join(
            "".join(FACES[x] for x in c[9 * f:9 * f + 9]) for f in range(6)
        ) + ")"


def _build_y_relabel() -> list[dict[Move, Move]]:
    """``table[k][m]``: the move that does ``m`` after the cube is turned by ``y`` k times."""
    solved = Cube()
    table: list[dict[Move, Move]] = []
    for k in range(4):
        turn = [Move("y", k)] if k else []
        after = {solved.apply(turn + [m]): m for m in MOVE_DEST}
        table.append({m: after[solved.apply([m] + turn)] for m in MOVE_DEST})
    return table


Y_RELABEL = _build_y_relabel()


def relabel_after_y(moves: Iterable[Move], k: int) -> list[Move]:
    """Express ``moves`` for a cube held after ``k`` extra ``y`` rotations.

    Doing ``y``*k then the returned moves gives the same state as doing
    ``moves`` then ``y``*k: e.g. ``R`` becomes ``F`` after one ``y``.
    """
    table = Y_RELABEL[k % 4]
    return [table[m] for m in moves]
