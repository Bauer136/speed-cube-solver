"""Fast piece-tracking search used by the method solvers.

A piece is tracked by one of its stickers: the slot that sticker sits in
gives both the piece's position and its orientation. Edge stickers and
corner stickers are numbered 0-23 each, and every face move becomes a
lookup table over those numbers. Search states are small tuples of these
indices, which keeps the pure-Python searches quick.
"""

from __future__ import annotations

import os
from collections import deque
from pathlib import Path

from .cube import CORNER_SLOTS, EDGE_SLOTS, MOVE_DEST, slot_at
from .notation import FACE_MOVES, Move

SEARCH_MOVES: list[Move] = [Move(f, t) for f in FACE_MOVES for t in (1, 2, 3)]
MOVE_FACE: list[int] = [FACE_MOVES.index(m.name) for m in SEARCH_MOVES]
OPPOSITE = [3, 4, 5, 0, 1, 2]  # U<->D, R<->L, F<->B

EDGE_INDEX = {slot: i for i, slot in enumerate(EDGE_SLOTS)}
CORNER_INDEX = {slot: i for i, slot in enumerate(CORNER_SLOTS)}
EDGE_MOVE: list[list[int]] = [
    [EDGE_INDEX[MOVE_DEST[m][s]] for s in EDGE_SLOTS] for m in SEARCH_MOVES
]
CORNER_MOVE: list[list[int]] = [
    [CORNER_INDEX[MOVE_DEST[m][s]] for s in CORNER_SLOTS] for m in SEARCH_MOVES
]

ALL_MOVE_IDS = list(range(18))
# F2L keeps the cross, so it never turns D. U and R come first so that among
# equally short solutions the search finds the most finger-friendly ones.
F2L_MOVE_IDS = [i for face in "URFLB" for i in range(18) if SEARCH_MOVES[i].name == face]


def edge_of(pos, normal) -> int:
    return EDGE_INDEX[slot_at(pos, normal)]


def corner_of(pos, normal) -> int:
    return CORNER_INDEX[slot_at(pos, normal)]


def allowed_after(face: int, last: int) -> bool:
    """Skip turning the same face twice and fix the order of commuting opposite faces."""
    return face != last and not (OPPOSITE[face] == last and face < last)


# --- Cross ---------------------------------------------------------------

_DOWN = (0, -1, 0)
CROSS_GOAL: tuple[int, ...] = tuple(
    edge_of(pos, _DOWN) for pos in [(0, -1, 1), (1, -1, 0), (0, -1, -1), (-1, -1, 0)]
)


def cross_key(e: tuple[int, ...] | list[int]) -> int:
    return ((e[0] * 24 + e[1]) * 24 + e[2]) * 24 + e[3]


def _cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "speedsolver"


def _build_cross_table() -> bytearray:
    dist = bytearray([255]) * 24**4
    start = CROSS_GOAL
    dist[cross_key(start)] = 0
    queue = deque([start])
    while queue:
        state = queue.popleft()
        d = dist[cross_key(state)] + 1
        for em in EDGE_MOVE:
            nxt = (em[state[0]], em[state[1]], em[state[2]], em[state[3]])
            k = cross_key(nxt)
            if dist[k] == 255:
                dist[k] = d
                queue.append(nxt)
    return dist


_cross_table: bytearray | None = None


def cross_table() -> bytearray:
    """Exact move count (HTM, all 18 face moves) to solve the D cross, indexed by ``cross_key``."""
    global _cross_table
    if _cross_table is None:
        path = _cache_dir() / "cross-v1.bin"
        try:
            data = bytearray(path.read_bytes())
            if len(data) != 24**4:
                raise ValueError("bad cache size")
            _cross_table = data
        except (OSError, ValueError):
            _cross_table = _build_cross_table()
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(_cross_table)
                tmp.replace(path)
            except OSError:
                pass  # caching is only a speed-up
    return _cross_table


def cross_solutions(edges: tuple[int, ...], extra: int = 0, limit: int = 20) -> list[list[Move]]:
    """Cross solutions of optimal length (plus up to ``extra`` moves), at most ``limit``."""
    table = cross_table()
    best = table[cross_key(edges)]
    found: list[list[Move]] = []
    path: list[int] = []

    def dfs(state: tuple[int, ...], remaining: int, last: int) -> bool:
        if remaining == 0:
            if state == CROSS_GOAL:
                found.append([SEARCH_MOVES[i] for i in path])
                return len(found) >= limit
            return False
        for mi in ALL_MOVE_IDS:
            face = MOVE_FACE[mi]
            if not allowed_after(face, last):
                continue
            em = EDGE_MOVE[mi]
            nxt = (em[state[0]], em[state[1]], em[state[2]], em[state[3]])
            if table[cross_key(nxt)] < remaining:
                path.append(mi)
                if dfs(nxt, remaining - 1, face):
                    return True
                path.pop()
        return False

    for length in range(best, best + extra + 1):
        if dfs(edges, length, -1):
            break
    return found


# --- F2L pairs -------------------------------------------------------------

F2L_SLOTS: dict[str, tuple[int, int]] = {
    # slot name -> (corner tracked by its D sticker, edge tracked by its F/B sticker)
    "FR": (corner_of((1, -1, 1), _DOWN), edge_of((1, 0, 1), (0, 0, 1))),
    "FL": (corner_of((-1, -1, 1), _DOWN), edge_of((-1, 0, 1), (0, 0, 1))),
    "BL": (corner_of((-1, -1, -1), _DOWN), edge_of((-1, 0, -1), (0, 0, -1))),
    "BR": (corner_of((1, -1, -1), _DOWN), edge_of((1, 0, -1), (0, 0, -1))),
}


def _build_pair_table(corner_goal: int, edge_goal: int) -> bytearray:
    dist = bytearray([255]) * (24 * 24)
    dist[corner_goal * 24 + edge_goal] = 0
    queue = deque([(corner_goal, edge_goal)])
    while queue:
        c, e = queue.popleft()
        d = dist[c * 24 + e] + 1
        for mi in F2L_MOVE_IDS:
            nc, ne = CORNER_MOVE[mi][c], EDGE_MOVE[mi][e]
            if dist[nc * 24 + ne] == 255:
                dist[nc * 24 + ne] = d
                queue.append((nc, ne))
    return dist


PAIR_TABLES: dict[str, bytearray] = {name: _build_pair_table(*goal) for name, goal in F2L_SLOTS.items()}
"""Moves (without D) to solve one corner-edge pair, ignoring everything else."""

# Moves the F2L search may make after a move on face ``last`` (-1: none yet),
# with their tables, so the search loop does no filtering of its own. The
# last move of a solution is never U: a final U only moves the last layer.
_F2L_NEXT: dict[int, list[tuple[int, int, list[int], list[int]]]] = {
    last: [(mi, MOVE_FACE[mi], EDGE_MOVE[mi], CORNER_MOVE[mi])
           for mi in F2L_MOVE_IDS if allowed_after(MOVE_FACE[mi], last)]
    for last in range(-1, 6)
}
_F2L_LAST = {last: [m for m in moves if m[1] != 0] for last, moves in _F2L_NEXT.items()}


def pair_solutions(
    edges: tuple[int, ...],
    corners: tuple[int, ...],
    slots: list[str],
    slack: int = 0,
    limit: int = 8,
    max_depth: int = 14,
) -> list[list[Move]]:
    """⟨U,R,F,L,B⟩ sequences that solve the cross and every pair in ``slots``.

    ``edges`` holds the four cross edges followed by each pair's edge,
    ``corners`` each pair's corner, in the order of ``slots``. Pairs that are
    already solved stay solved, so calling this with the solved slots plus
    one new slot inserts that pair.

    Returns up to ``limit`` solutions, shortest first, from the optimal
    length up to ``slack`` moves longer, so the caller can pick the one that
    is easiest to execute. None ends with a U turn (that would be wasted).
    The search tries U and R first, so when ``limit`` cuts it short the
    solutions kept are the finger-friendly ones.
    """
    ctable = cross_table()
    tables = [PAIR_TABLES[s] for s in slots]
    pairs = range(len(slots))
    path: list[int] = []

    def heuristic(es: tuple[int, ...], cs: tuple[int, ...]) -> int:
        return max([ctable[cross_key(es)]] + [tables[k][cs[k] * 24 + es[4 + k]] for k in pairs])

    found: list[list[Move]] = []

    def dfs(es: tuple[int, ...], cs: tuple[int, ...], depth: int, last: int) -> bool:
        """Collect solutions of exactly ``depth`` moves; True once ``limit`` is reached."""
        for mi, face, em, cm in (_F2L_LAST if depth == 1 else _F2L_NEXT)[last]:
            # Hot loop: cheapest pruning test (the cross) first, inlined.
            nes = tuple([em[e] for e in es])
            if ctable[((nes[0] * 24 + nes[1]) * 24 + nes[2]) * 24 + nes[3]] >= depth:
                continue
            ncs = tuple([cm[c] for c in cs])
            if any(tables[k][ncs[k] * 24 + nes[4 + k]] >= depth for k in pairs):
                continue
            path.append(mi)
            if depth == 1:
                found.append([SEARCH_MOVES[i] for i in path])
                done = len(found) >= limit
            else:
                done = dfs(nes, ncs, depth - 1, face)
            path.pop()
            if done:
                return True
        return False

    h0 = heuristic(edges, corners)
    if h0 == 0:
        return [[]]
    first = None
    for depth in range(h0, max_depth + 1):
        if first is not None and depth > first + slack:
            break
        if dfs(edges, corners, depth, -1):
            break
        if found and first is None:
            first = depth
    return found
