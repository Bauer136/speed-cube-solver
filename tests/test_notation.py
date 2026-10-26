import pytest

from speedsolver.notation import Move, cancel, format_moves, invert, parse_moves


def test_parse_standard_scramble():
    moves = parse_moves("R U R' U' F2 D L'")
    assert format_moves(moves) == "R U R' U' F2 D L'"
    assert moves[2] == Move("R", 3)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Rw U2'", "r U2"),
        ("RUR'U'", "R U R' U'"),
        ("(R U R') U’", "R U R' U'"),
        ("M2 E S' x y' z2", "M2 E S' x y' z2"),
        ("R4 U3", "U'"),
        ("", ""),
    ],
)
def test_parse_variants(text, expected):
    assert format_moves(parse_moves(text)) == expected


@pytest.mark.parametrize("text", ["R U Q", "R ? U", "Uw3x5'k"])
def test_parse_rejects_garbage(text):
    with pytest.raises(ValueError):
        parse_moves(text)


def test_invert():
    assert format_moves(invert(parse_moves("R U2 F'"))) == "F U2 R'"


def test_cancel():
    assert format_moves(cancel(parse_moves("R U U' R"))) == "R2"
    assert format_moves(cancel(parse_moves("U U U U"))) == ""
    assert format_moves(cancel(parse_moves("R L R"))) == "R L R"
