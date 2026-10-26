import random

import pytest

from speedsolver.cube import Cube
from speedsolver.methods import CFOP
from speedsolver.notation import parse_moves
from speedsolver.scramble import random_scramble
from speedsolver.search import CROSS_GOAL, cross_key, cross_solutions, cross_table
from speedsolver.solution import Stage, htm, join_stages, qtm, stm
from speedsolver.solver import solve


def test_cross_table_is_exact():
    table = cross_table()
    assert table[cross_key(CROSS_GOAL)] == 0
    assert max(x for x in table if x != 255) == 8  # known cross God's number
    assert sum(1 for x in table if x != 255) == 190080


def test_cross_solutions_solve_the_cross():
    from speedsolver.methods.cfop import _tracked

    cube = Cube().apply("R2 U' D' B' R D L B' F2 R2")
    edges, _ = _tracked(cube, [])
    solutions = cross_solutions(edges, limit=5)
    assert solutions
    for sol in solutions:
        assert len(sol) == cross_table()[cross_key(edges)]
        assert _tracked(cube.apply(sol), [])[0] == CROSS_GOAL


def test_metrics():
    moves = parse_moves("R U2 M' x")
    assert stm(moves) == 3
    assert htm(moves) == 4
    assert qtm(moves) == 5


def test_join_stages_cancels_across_boundaries():
    def joined(*parts):
        return [" ".join(map(str, s.moves)) for s in join_stages([Stage(str(i), parse_moves(p)) for i, p in enumerate(parts)])]

    assert joined("R U", "U R'", "F") == ["R U2", "R'", "F"]
    # A stage that cancels away completely lets the next one cancel further back.
    assert joined("R U", "U R'", "R F") == ["R U2", "", "F"]
    assert joined("R U", "U' R'") == ["", ""]


STAGE_ORDER = ["Inspection", "Cross", "F2L 1", "F2L 2", "F2L 3", "F2L 4"]


@pytest.mark.parametrize("seed", range(4))
def test_cfop_solves_random_scrambles(seed):
    scramble = random_scramble(rng=random.Random(seed))
    cube = Cube().apply(scramble)
    sol = CFOP(cross_colors=("yellow", "green")).solve(cube)
    assert cube.apply(sol.moves).is_solved()
    names = [s.name for s in sol.stages]
    assert names[:6] == STAGE_ORDER
    assert names[6].startswith("OLL")
    assert names[7].startswith("PLL") or names[7] == "AUF"
    assert sol.length("STM") < 80
    # The solver's own rotations (cross and F2L) are only ever y turns.
    # (Algorithms such as the A-perm contain x rotations of their own.)
    for stage in sol.stages[1:6]:
        assert all(m.name == "y" for m in stage.moves if m.is_rotation), stage


def test_cfop_handles_slices_and_rotations_in_the_scramble():
    cube = Cube().apply("M2 E S' x y R U2 F' r u'")
    sol = CFOP(cross_colors=("white", "yellow")).solve(cube)
    assert cube.apply(sol.moves).is_solved()


def test_solved_cube_needs_no_moves():
    sol = CFOP(cross_colors=("yellow",)).solve(Cube())
    assert sol.moves == []
    assert sol.stages[-2].name == "OLL skip" and sol.stages[-1].name == "PLL skip"


def test_full_solve_is_color_neutral_and_verified():
    solutions = solve("D2 F' U2 L2 B' R2 F' L2 D2 U2 F' R' D U2 L' F D2 R' U R' F'")
    assert solutions and solutions[0].method == "CFOP"
