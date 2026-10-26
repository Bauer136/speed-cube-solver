"""CFOP: Cross, F2L (four corner-edge pairs), OLL, PLL.

The solver works like a color-neutral speedcuber:

* Inspection: rotate so the chosen cross color is on the bottom.
* Cross: optimal crosses (exact lookup table), easiest to execute first.
* F2L: pairs are inserted one at a time. For each pair the search returns
  the shortest sequences (and some one move longer) that keep the cross and
  earlier pairs; the easiest to execute are kept, and a beam search tries
  different pair orders.
* Rotations: like a human, the solver may turn the cube with ``y`` before a
  pair so it is inserted with R/U/F/L instead of awkward B moves. A small
  dynamic program picks the orientation for every step.
* OLL / PLL: the case is recognised by lookup, in whatever orientation the
  cube is held after F2L, and solved with a named algorithm, trying every
  pre-AUF so moves cancel into the previous step.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..algs import OLL, OLL_NAMES, PLL
from ..cube import EDGE_SLOTS, CORNER_SLOTS, FACES, SLOTS, Cube, relabel_after_y
from ..ergonomics import execution_time
from ..notation import Move, cancel, invert, parse_moves
from ..search import (
    CORNER_INDEX,
    CROSS_GOAL,
    EDGE_INDEX,
    F2L_SLOTS,
    PAIR_TABLES,
    cross_solutions,
    pair_solutions,
)
from ..solution import DEFAULT_METRIC, METRICS, Solution, Stage, join_stages, scored_moves

# Colors of the faces of the solved cube in the standard WCA orientation.
COLOR_NAMES = {"U": "white", "R": "red", "F": "green", "D": "yellow", "L": "orange", "B": "blue"}
CROSS_COLORS = ("white", "yellow", "green", "blue", "red", "orange")


def _face_with_center(cube: Cube, color: str) -> str:
    """Face currently showing ``color`` in its center (slice moves can move centers)."""
    home = FACES.index(next(f for f, name in COLOR_NAMES.items() if name == color))
    return next(f for i, f in enumerate(FACES) if cube.stickers[9 * i + 4] // 9 == home)

# Rotation that brings each face to the bottom.
CROSS_ROTATION = {"D": "", "U": "x2", "F": "x'", "B": "x", "R": "z", "L": "z'"}

AUFS: list[list[Move]] = [[], parse_moves("U"), parse_moves("U2"), parse_moves("U'")]

Y_TURNS: list[list[Move]] = [[], [Move("y", 1)], [Move("y", 2)], [Move("y", 3)]]

LL_SLOTS = [i for i, (pos, _) in enumerate(SLOTS) if pos[1] == 1 and i != 4]


def _oll_pattern(cube: Cube) -> int:
    """Bitmask of last-layer slots showing the U color."""
    s = cube.stickers
    return sum(1 << k for k, i in enumerate(LL_SLOTS) if s[i] < 9)


def _ll_key(cube: Cube) -> tuple[int, ...]:
    s = cube.stickers
    return tuple(s[i] for i in LL_SLOTS)


@dataclass(frozen=True)
class _LLOption:
    name: str  # "" for a skip
    moves: tuple[Move, ...]  # pre-AUF + algorithm (+ post-AUF for PLL)


def _build_oll_table() -> dict[int, list[_LLOption]]:
    table: dict[int, list[_LLOption]] = {_oll_pattern(Cube()): [_LLOption("", ())]}
    for number, alg in OLL.items():
        nick = OLL_NAMES.get(number)
        name = f"OLL {number}" + (f" ({nick})" if nick else "")
        for auf in AUFS:
            moves = tuple(auf + parse_moves(alg))
            case = Cube().apply(invert(moves))
            table.setdefault(_oll_pattern(case), []).append(_LLOption(name, moves))
    return table


def _build_pll_table() -> dict[tuple[int, ...], list[_LLOption]]:
    table: dict[tuple[int, ...], list[_LLOption]] = {}
    for auf in AUFS:
        case = Cube().apply(invert(auf))
        table.setdefault(_ll_key(case), []).append(_LLOption("", tuple(auf)))
    for name, alg in PLL.items():
        for pre in AUFS:
            for post in AUFS:
                moves = tuple(pre + parse_moves(alg) + post)
                case = Cube().apply(invert(moves))
                table.setdefault(_ll_key(case), []).append(_LLOption(f"PLL {name}", moves))
    return table


OLL_TABLE = _build_oll_table()
PLL_TABLE = _build_pll_table()


def _tracked(cube: Cube, slots: list[str]) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Search indices for the cross edges plus the pairs in ``slots``."""
    pos = {sticker: i for i, sticker in enumerate(cube.stickers)}
    edge_goals = list(CROSS_GOAL) + [F2L_SLOTS[s][1] for s in slots]
    edges = tuple(EDGE_INDEX[pos[EDGE_SLOTS[e]]] for e in edge_goals)
    corners = tuple(CORNER_INDEX[pos[CORNER_SLOTS[F2L_SLOTS[s][0]]]] for s in slots)
    return edges, corners


def _easiest_time(moves: list[Move]) -> float:
    """Execution time in the best of the four ``y`` orientations."""
    return min(execution_time(relabel_after_y(moves, k)) for k in range(4))


AVERAGE_MOVE_TIME = 0.1  # seconds; turns "moves still needed" into estimated time


def _remaining_estimate(cube: Cube, solved: list[str]) -> float:
    """Rough time still needed for the unsolved pairs (each pair on its own).

    Ranking partial solutions by time spent *plus* this keeps the beam
    search from grabbing cheap early pairs that leave the rest scattered.
    """
    pos = {sticker: i for i, sticker in enumerate(cube.stickers)}
    moves = 0
    for slot, (corner, edge) in F2L_SLOTS.items():
        if slot not in solved:
            c = CORNER_INDEX[pos[CORNER_SLOTS[corner]]]
            e = EDGE_INDEX[pos[EDGE_SLOTS[edge]]]
            moves += PAIR_TABLES[slot][c * 24 + e]
    return moves * AVERAGE_MOVE_TIME


def _rotation_time(before: int, after: int) -> float:
    return execution_time(Y_TURNS[(after - before) % 4])


_Y_FACE = {"F": "L", "R": "F", "B": "R", "L": "B"}  # where a side ends up after one y


def _slot_after_y(slot: str, k: int) -> str:
    """Name of the slot's position once the cube is turned by ``y`` k times."""
    for _ in range(k % 4):
        slot = "".join(_Y_FACE[f] for f in slot)
    return "".join(sorted(slot, key="FBRL".index))


@dataclass
class _Partial:
    stages: list[Stage]  # cross and F2L stages, in the cross frame (no rotations)
    cube: Cube
    solved: list[str]
    cost: float  # estimated time of the stages so far

    @property
    def rank(self) -> float:
        return self.cost + _remaining_estimate(self.cube, self.solved)


def parse_cross_colors(text: str) -> tuple[str, ...]:
    """Read ``"white,yellow"``, ``"w y"`` or ``"all"`` into color names in ``CROSS_COLORS`` order."""
    words = text.replace(",", " ").lower().split()
    if words == ["all"]:
        return CROSS_COLORS
    chosen = set()
    for word in words:
        match = [c for c in CROSS_COLORS if c == word or (len(word) == 1 and c[0] == word)]
        if not match:
            raise ValueError(f"unknown color {word!r}; use {', '.join(CROSS_COLORS)} or all")
        chosen.add(match[0])
    if not chosen:
        raise ValueError("choose at least one cross color")
    return tuple(c for c in CROSS_COLORS if c in chosen)


class CFOP:
    name = "CFOP"

    def __init__(
        self,
        cross_colors: tuple[str, ...] | list[str] = CROSS_COLORS,
        cross_alternatives: int = 4,
        beam_width: int = 6,
        pair_candidates: int = 3,
        pair_slack: int = 0,
        metric: str = DEFAULT_METRIC,
    ) -> None:
        unknown = set(cross_colors) - set(CROSS_COLORS)
        if unknown or not cross_colors:
            raise ValueError(f"cross colors must be a non-empty subset of {CROSS_COLORS}, got {cross_colors}")
        self.cross_colors = tuple(c for c in CROSS_COLORS if c in cross_colors)
        self.cross_alternatives = cross_alternatives
        self.beam_width = beam_width
        self.pair_candidates = pair_candidates
        self.pair_slack = pair_slack
        self.metric = METRICS[metric]

    def variants(self) -> list[str]:
        """Independent pieces of work: one per allowed cross color."""
        return list(self.cross_colors)

    def solve(self, scramble: Cube, variant: str | None = None) -> Solution | None:
        """Shortest full solution over the allowed cross colors (or only ``variant``).

        Colors are compared on the whole solution, not just the cross: a
        short cross that leaves a bad F2L loses to a longer one that doesn't.
        """
        best: Solution | None = None
        for color in [variant] if variant else self.variants():
            sol = self._solve_with_cross_on(scramble, _face_with_center(scramble, color))
            if sol and (best is None or self._cost(sol.stages) < self._cost(best.stages)):
                best = sol
        return best

    def _cost(self, stages: list[Stage]) -> float:
        return self.metric(scored_moves(join_stages(stages)))

    def _solve_with_cross_on(self, scramble: Cube, face: str) -> Solution | None:
        color = COLOR_NAMES[FACES[scramble.stickers[9 * FACES.index(face) + 4] // 9]]
        rotation = parse_moves(CROSS_ROTATION[face])
        start = scramble.apply(rotation).normalized()

        edges, _ = _tracked(start, [])
        crosses = [
            _Partial([Stage("Cross", c, color)], start.apply(c), [], _easiest_time(c))
            for c in cross_solutions(edges, limit=30)
        ]
        # Prefer crosses that are easy to do *and* leave the pairs close to solved.
        partials = sorted(crosses, key=lambda p: p.rank)[: self.cross_alternatives]

        for step in range(1, 5):
            expanded = []
            for p in partials:
                for slot in F2L_SLOTS:
                    if slot in p.solved:
                        continue
                    edges, corners = _tracked(p.cube, p.solved + [slot])
                    # Stable sort: among equally easy sequences the shorter comes first.
                    candidates = sorted(pair_solutions(edges, corners, p.solved + [slot], slack=self.pair_slack),
                                        key=_easiest_time)
                    for seq in candidates[: self.pair_candidates]:
                        expanded.append(_Partial(
                            p.stages + [Stage(f"F2L {step}", seq)],
                            p.cube.apply(seq),
                            p.solved + [slot],
                            p.cost + _easiest_time(seq),
                        ))
            expanded.sort(key=lambda p: p.rank)
            # Different orders often reach the same state; keep one of each.
            seen: set[Cube] = set()
            partials = []
            for p in expanded:
                if p.cube not in seen:
                    seen.add(p.cube)
                    partials.append(p)
                if len(partials) == self.beam_width:
                    break

        candidates = [self._present(p, rotation, color) for p in partials]
        if not candidates:
            return None
        best = min(candidates, key=self._cost)
        return Solution(self.name, join_stages(best), variant=f"{color} cross")

    def _present(self, p: _Partial, rotation: list[Move], color: str) -> list[Stage]:
        """Choose how to hold the cube for each step, then add the last layer.

        ``orientation`` k means the cube has been turned ``y`` k times since
        the cross rotation. Turning during inspection is free; later turns
        cost a rotation. Dynamic programming over the four orientations
        finds the cheapest choice for the cross and every F2L pair.
        """
        steps = p.stages
        # best[k] = (time so far, orientation per step) ending in orientation k
        best = {k: (execution_time(relabel_after_y(steps[0].moves, k)), [k]) for k in range(4)}
        for step in steps[1:]:
            best = {
                k: min(
                    (cost + _rotation_time(path[-1], k) + execution_time(relabel_after_y(step.moves, k)), path + [k])
                    for cost, path in best.values()
                )
                for k in range(4)
            }

        options = []
        for _, path in best.values():
            stages = [Stage("Inspection", cancel(rotation + Y_TURNS[path[0]]),
                            f"{color} cross on the bottom", free=True)]
            held = path[0]
            for i, (step, k) in enumerate(zip(steps, path)):
                detail = step.detail
                if i:  # F2L pairs: name the slot where it is when the pair goes in
                    detail = f"{_slot_after_y(p.solved[i - 1], k)} slot"
                stages.append(Stage(step.name, Y_TURNS[(k - held) % 4] + relabel_after_y(step.moves, k), detail))
                held = k
            view = p.cube.apply(Y_TURNS[held]).normalized()
            options.append(self._last_layer(stages, view))
        return min(options, key=self._cost)

    def _last_layer(self, prefix: list[Stage], cube: Cube) -> list[Stage]:
        """``prefix`` plus the cheapest OLL and PLL for ``cube`` (F2L solved, centers home)."""
        best: list[Stage] | None = None
        best_cost = 0.0
        for oll in OLL_TABLE[_oll_pattern(cube)]:
            after_oll = cube.apply(oll.moves)
            oll_stage = Stage(oll.name or "OLL skip", list(oll.moves))
            for pll in PLL_TABLE[_ll_key(after_oll)]:
                pll_name = pll.name or ("AUF" if pll.moves else "PLL skip")
                stages = prefix + [oll_stage, Stage(pll_name, list(pll.moves))]
                cost = self._cost(stages)
                if best is None or cost < best_cost:
                    best, best_cost = stages, cost
        assert best is not None, "last layer case missing from the algorithm tables"
        return best
