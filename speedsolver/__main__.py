"""``python -m speedsolver`` opens the app; ``--solve "<scramble>"`` prints a solution."""

from __future__ import annotations

import argparse
import time

from .methods import CFOP, parse_cross_colors
from .scramble import random_scramble
from .solution import DEFAULT_METRIC, METRICS
from .solver import best_per_method, solve_all


def _colors(text: str) -> tuple[str, ...]:
    try:
        return parse_cross_colors(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def main() -> None:
    parser = argparse.ArgumentParser(prog="speedsolver", description=__doc__)
    parser.add_argument("--solve", metavar="SCRAMBLE", help="solve in the terminal instead of opening the window")
    parser.add_argument("--random", action="store_true", help="solve a random scramble in the terminal")
    parser.add_argument(
        "--metric", choices=sorted(METRICS), default=DEFAULT_METRIC,
        help="what 'fastest' means: TIME (estimated execution time, default) or a move count",
    )
    parser.add_argument(
        "--colors", metavar="COLORS", type=_colors, default="all",
        help="cross colors to choose from, e.g. 'white,yellow' or 'w y' (default: all)",
    )
    args = parser.parse_args()

    if args.solve is None and not args.random:
        from .ui.app import run  # imported here so the solver never needs Ursina

        run()
        return

    scramble = args.solve if args.solve is not None else random_scramble()
    print(f"Scramble: {scramble}")
    start = time.perf_counter()
    solutions = solve_all(scramble, methods=[CFOP(cross_colors=args.colors, metric=args.metric)], metric=args.metric)
    if len(solutions) > 1:
        print("Cross colors, fastest first:")
        for s in solutions:
            print(f"  {s.variant.split()[0]:<7} {s.score()}")
    for sol in best_per_method(solutions, args.metric):
        print(sol)
    print(f"({time.perf_counter() - start:.1f}s)")


if __name__ == "__main__":
    main()
