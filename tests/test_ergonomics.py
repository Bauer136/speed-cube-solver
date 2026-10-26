import pytest

from speedsolver.cube import Cube, relabel_after_y
from speedsolver.ergonomics import execution_time
from speedsolver.methods.cfop import CFOP, _slot_after_y, _tracked
from speedsolver.notation import Move, format_moves, parse_moves
from speedsolver.search import pair_solutions
from speedsolver.solution import Solution, Stage


def test_easy_moves_are_faster_than_awkward_ones():
    assert execution_time(parse_moves("R U R' U'")) < execution_time(parse_moves("B U B' U'"))
    assert execution_time(parse_moves("R2")) > execution_time(parse_moves("R"))


def test_relabel_after_y_matches_the_cube():
    moves = parse_moves("U R B U2 B' U2 R' M S x z r")
    cube = Cube().apply("R2 U F")
    for k in range(4):
        turn = [Move("y", k)] if k else []
        assert cube.apply(turn + relabel_after_y(moves, k)) == cube.apply(moves + turn)
    assert format_moves(relabel_after_y(parse_moves("R B R'"), 1)) == "F R F'"


@pytest.mark.parametrize("slot, k, expected", [("FR", 0, "FR"), ("FR", 1, "FL"), ("BR", 1, "FR"), ("BL", 2, "FR")])
def test_slot_after_y(slot, k, expected):
    assert _slot_after_y(slot, k) == expected


def test_pair_solutions_are_valid_and_never_end_with_u():
    # These triggers keep the cross but take the FR (and FL) pair apart.
    cube = Cube().apply("R U R' U2 F' U F")
    edges, corners = _tracked(cube, ["FR"])
    sols = pair_solutions(edges, corners, ["FR"], slack=1, limit=15)
    assert sols
    lengths = [len(s) for s in sols]
    assert lengths == sorted(lengths) and lengths[-1] <= lengths[0] + 1
    for seq in sols:
        assert seq[-1].name != "U"
        assert _tracked(cube.apply(seq), ["FR"]) == _tracked(Cube(), ["FR"])


def test_inspection_is_not_scored():
    sol = Solution("X", [Stage("Inspection", parse_moves("x2 y"), free=True), Stage("Cross", parse_moves("R U"))])
    assert sol.length("STM") == 2
    assert sol.length("TIME") == pytest.approx(execution_time(parse_moves("R U")))
    assert sol.moves[:2] == parse_moves("x2 y")  # still played back


def test_cfop_avoids_back_moves_with_rotations():
    # Seen earlier: without ergonomics this scramble's F2L used B moves in three pairs.
    cube = Cube().apply("R2 U' D' B' R D L B' F2 R2 U' B2 U' B D2 U2 R' D2 R' B")
    sol = CFOP().solve(cube, "green")
    assert cube.apply(sol.moves).is_solved()
    f2l_moves = [m for s in sol.stages if s.name.startswith("F2L") for m in s.moves]
    assert sum(1 for m in f2l_moves if m.name == "B") <= 1
