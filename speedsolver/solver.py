"""Entry point for solving: runs every method variant and ranks the results."""

from __future__ import annotations

import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import Iterable

from .cube import Cube
from .methods import CFOP
from .notation import Move, as_moves
from .search import cross_table
from .solution import DEFAULT_METRIC, Solution


def default_methods() -> list:
    return [CFOP()]


def _run(method, scramble: Cube, variant: str) -> Solution | None:
    return method.solve(scramble, variant)


def solve_all(
    scramble: str | Iterable[Move],
    methods: list | None = None,
    metric: str = DEFAULT_METRIC,
    parallel: bool = True,
) -> list[Solution]:
    """One solution per method variant (e.g. per cross color), shortest first.

    Every solution is checked against the cube model before it is returned.
    Work runs in separate processes (spawned, so the UI process is never
    forked); set ``parallel=False`` to stay in this process.
    """
    cube = Cube().apply(as_moves(scramble))
    methods = methods if methods is not None else default_methods()
    jobs = [(m, v) for m in methods for v in m.variants()]

    cross_table()  # build/cache once before workers start so they can load it
    if parallel and len(jobs) > 1:
        ctx = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=min(len(jobs), 8), mp_context=ctx) as pool:
            results = list(pool.map(_run, *zip(*[(m, cube, v) for m, v in jobs])))
    else:
        results = [_run(m, cube, v) for m, v in jobs]

    solutions = [s for s in results if s is not None]
    for sol in solutions:
        if not cube.apply(sol.moves).is_solved():
            raise RuntimeError(f"{sol.method} produced a wrong solution: {sol}")
    return sorted(solutions, key=lambda s: s.length(metric))


def best_per_method(solutions: list[Solution], metric: str = DEFAULT_METRIC) -> list[Solution]:
    """The shortest solution of each method, shortest first."""
    best: dict[str, Solution] = {}
    for sol in solutions:
        if sol.method not in best or sol.length(metric) < best[sol.method].length(metric):
            best[sol.method] = sol
    return sorted(best.values(), key=lambda s: s.length(metric))


def solve(
    scramble: str | Iterable[Move],
    methods: list | None = None,
    metric: str = DEFAULT_METRIC,
    parallel: bool = True,
) -> list[Solution]:
    """All methods' best solutions for ``scramble``, shortest first."""
    return best_per_method(solve_all(scramble, methods, metric, parallel), metric)
