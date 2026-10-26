"""The OLL/PLL sets must be correct and cover every last-layer case."""

import itertools

import pytest

from speedsolver.algs import OLL, PLL
from speedsolver.cube import CENTER_SLOTS, PIECES, SLOTS, Cube
from speedsolver.methods.cfop import OLL_TABLE, PLL_TABLE, _ll_key, _oll_pattern
from speedsolver.notation import invert, parse_moves

FIRST_TWO_LAYERS = [i for i, (pos, _) in enumerate(SLOTS) if pos[1] < 1]


def _keeps_f2l(cube: Cube) -> bool:
    return all(cube.stickers[i] == i for i in FIRST_TWO_LAYERS + list(CENTER_SLOTS))


@pytest.mark.parametrize("number", sorted(OLL))
def test_oll_keeps_first_two_layers(number):
    case = Cube().apply(invert(parse_moves(OLL[number])))
    assert _keeps_f2l(case)


@pytest.mark.parametrize("name", sorted(PLL))
def test_pll_keeps_f2l_and_orientation(name):
    case = Cube().apply(invert(parse_moves(PLL[name])))
    assert _keeps_f2l(case)
    assert all(s < 9 for s in case.stickers[:9]), "PLL must not change orientation"


def _clockwise(stickers):
    """Order a corner's stickers U/D first, then clockwise seen from outside."""
    normals = {s: SLOTS[s][1] for s in stickers}
    first = next(s for s in stickers if normals[s][1] != 0)
    a, b = [s for s in stickers if s != first]

    def det(u, v, w):
        return (u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0])
                + u[2] * (v[0] * w[1] - v[1] * w[0]))

    return (first, a, b) if det(normals[first], normals[a], normals[b]) == -1 else (first, b, a)


TOP = [p for p in PIECES if len(p) > 1 and all(SLOTS[s][0][1] == 1 for s in p)]
TOP_CORNERS = [_clockwise(p) for p in TOP if len(p) == 3]
TOP_EDGES = [tuple(sorted(p, key=lambda s: SLOTS[s][1][1] == 0)) for p in TOP if len(p) == 2]


def _parity(perm) -> int:
    return sum(1 for i, j in itertools.combinations(range(len(perm)), 2) if perm[i] > perm[j]) % 2


def _ll_state(cp, co, ep, eo) -> Cube:
    """Solved F2L with the last layer built from piece permutations and orientations."""
    stickers = list(range(54))
    for slot, (src, twist) in enumerate(zip(cp, co)):
        for i, s in enumerate(TOP_CORNERS[src]):
            stickers[TOP_CORNERS[slot][(i + twist) % 3]] = s
    for slot, (src, flip) in enumerate(zip(ep, eo)):
        for i, s in enumerate(TOP_EDGES[src]):
            stickers[TOP_EDGES[slot][(i + flip) % 2]] = s
    return Cube(stickers)


def test_ll_state_builder_matches_real_moves():
    # Sanity check on the builder: every state it makes for the Sune case is reachable.
    sune = Cube().apply("R U R' U R U2 R'")
    assert _oll_pattern(sune) in {_oll_pattern(_ll_state(cp, co, range(4), [0] * 4))
                                  for cp in itertools.permutations(range(4))
                                  for co in itertools.product(range(3), repeat=4) if sum(co) % 3 == 0}


def test_every_orientation_case_has_an_oll():
    identity = list(range(4))
    count = 0
    for co in itertools.product(range(3), repeat=4):
        if sum(co) % 3:
            continue
        for eo in itertools.product(range(2), repeat=4):
            if sum(eo) % 2:
                continue
            assert _oll_pattern(_ll_state(identity, co, identity, eo)) in OLL_TABLE, (co, eo)
            count += 1
    assert count == 216


def test_every_permutation_case_has_a_pll():
    count = 0
    for cp in itertools.permutations(range(4)):
        for ep in itertools.permutations(range(4)):
            if _parity(cp) != _parity(ep):
                continue
            assert _ll_key(_ll_state(cp, [0] * 4, ep, [0] * 4)) in PLL_TABLE, (cp, ep)
            count += 1
    assert count == 288


def test_table_options_solve_their_cases():
    for options in OLL_TABLE.values():
        for opt in options:
            assert all(s < 9 for s in Cube().apply(invert(opt.moves)).apply(opt.moves).stickers[:9])
    for key, options in PLL_TABLE.items():
        for opt in options:
            case = Cube().apply(invert(opt.moves))
            assert _ll_key(case) == key
            assert case.apply(opt.moves) == Cube()
