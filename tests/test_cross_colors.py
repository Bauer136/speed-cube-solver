import pytest

from speedsolver import settings
from speedsolver.cube import Cube
from speedsolver.methods import CFOP, CROSS_COLORS, parse_cross_colors
from speedsolver.solver import best_per_method, solve_all

SCRAMBLE = "R2 U' D' B' R D L B' F2 R2 U' B2 U' B D2 U2 R' D2 R' B"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("white,yellow", ("white", "yellow")),
        ("Y w", ("white", "yellow")),
        ("blue, green blue", ("green", "blue")),
        ("all", CROSS_COLORS),
        ("o", ("orange",)),
    ],
)
def test_parse_cross_colors(text, expected):
    assert parse_cross_colors(text) == expected


@pytest.mark.parametrize("text", ["", "purple", "white,pink", "x"])
def test_parse_cross_colors_rejects_bad_input(text):
    with pytest.raises(ValueError):
        parse_cross_colors(text)


@pytest.mark.parametrize("colors", [(), ("white", "purple")])
def test_cfop_rejects_bad_color_sets(colors):
    with pytest.raises(ValueError):
        CFOP(cross_colors=colors)


def test_picks_the_color_with_the_shortest_full_solution():
    colors = ("white", "yellow", "green")
    solutions = solve_all(SCRAMBLE, methods=[CFOP(cross_colors=colors)], parallel=False)
    assert sorted(s.variant for s in solutions) == sorted(f"{c} cross" for c in colors)
    best = best_per_method(solutions)[0]
    assert best.length() == min(s.length() for s in solutions)
    # CFOP.solve without a variant makes the same choice on its own.
    assert CFOP(cross_colors=colors).solve(Cube().apply(SCRAMBLE)).length() == best.length()


def test_single_color_is_always_used():
    for color in ("white", "orange"):
        sol = CFOP(cross_colors=(color,)).solve(Cube().apply(SCRAMBLE))
        assert sol.variant == f"{color} cross"
        assert sol.stages[0].detail == f"{color} cross on the bottom"


def test_follows_the_center_when_slices_move_it():
    # M2 puts the white center on the bottom, so inspection needs at most a y turn.
    cube = Cube().apply("M2 R U F'")
    sol = CFOP(cross_colors=("white",)).solve(cube)
    assert all(m.name == "y" for m in sol.stages[0].moves)
    assert sol.stages[0].detail == "white cross on the bottom"
    assert cube.apply(sol.moves).is_solved()


def test_settings_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert settings.load_cross_colors() == CROSS_COLORS  # nothing saved yet
    settings.save_cross_colors(("white", "yellow"))
    assert settings.load_cross_colors() == ("white", "yellow")


@pytest.mark.parametrize("content", ["not json", '{"cross_colors": "white"}', '{"cross_colors": ["pink"]}', "[]"])
def test_bad_settings_fall_back_to_all_colors(tmp_path, monkeypatch, content):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = tmp_path / "speedsolver" / "settings.json"
    path.parent.mkdir()
    path.write_text(content)
    assert settings.load_cross_colors() == CROSS_COLORS
    settings.save_cross_colors(("blue",))  # a broken file is replaced, not a crash
    assert settings.load_cross_colors() == ("blue",)
