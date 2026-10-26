import pytest

from speedsolver.cube import CENTER_SLOTS, MOVE_DEST, Cube
from speedsolver.notation import invert, parse_moves

SOLVED = Cube()


def test_face_turns_move_the_right_stickers():
    # Each face shows its 9 stickers as letters; see Cube.__repr__.
    assert repr(SOLVED.apply("R")) == "Cube(UUFUUFUUF RRRRRRRRR FFDFFDFFD DDBDDBDDB LLLLLLLLL UBBUBBUBB)"
    assert repr(SOLVED.apply("U")) == "Cube(UUUUUUUUU BBBRRRRRR RRRFFFFFF DDDDDDDDD FFFLLLLLL LLLBBBBBB)"
    assert repr(SOLVED.apply("F")) == "Cube(UUUUUULLL URRURRURR FFFFFFFFF RRRDDDDDD LLDLLDLLD BBBBBBBBB)"


def test_every_move_is_a_permutation_of_order_dividing_four():
    for move, dest in MOVE_DEST.items():
        assert sorted(dest) == list(range(54)), move
        assert SOLVED.apply([move] * 4) == SOLVED, move


def test_known_orders():
    assert SOLVED.apply("R U R' U'" * 6) == SOLVED
    assert SOLVED.apply("R U" * 105) == SOLVED
    assert SOLVED.apply("R U" * 21) != SOLVED


@pytest.mark.parametrize(
    "a, b",
    [
        ("r", "L x"),
        ("M", "R L' x'"),
        ("E", "U D' y'"),
        ("S", "F' B z"),
        ("u", "D y"),
        ("f", "B z"),
        ("x", "R M' L'"),
    ],
)
def test_wide_slice_and_rotation_identities(a, b):
    assert SOLVED.apply(a) == SOLVED.apply(b)


def test_inverse_restores():
    scramble = parse_moves("R2 U' D' B' R D L B' F2 R2 U' B2 U' B D2 U2 R' D2 R' B M x u'")
    assert SOLVED.apply(scramble).apply(invert(scramble)) == SOLVED


def test_is_solved_ignores_orientation():
    assert SOLVED.apply("x y2 z'").is_solved()
    assert not SOLVED.apply("R").is_solved()


def test_normalized_puts_centers_home():
    cube = SOLVED.apply("x2 R U M")
    norm = cube.normalized()
    assert all(norm.stickers[c] == c for c in CENTER_SLOTS)
    # After a rotation the solver works in the new frame: x2 then R U looks
    # exactly like R U done on a solved cube held normally.
    assert SOLVED.apply("x2 R U").normalized() == SOLVED.apply("R U")
    assert SOLVED.apply("y z").normalized() == SOLVED
