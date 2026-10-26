# SpeedSolverTool

A Rubik's cube (3x3) speed-solving assistant. Enter a scramble and it finds
a short solution built from real speed-solving methods, then plays it move
by move on a live 3D cube. See [TOOL_DESCRIPTION.md](TOOL_DESCRIPTION.md)
for the goals and design decisions.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

## Run

```bash
.venv/bin/python -m speedsolver                 # open the window
.venv/bin/python -m speedsolver --random        # solve a random scramble in the terminal
.venv/bin/python -m speedsolver --solve "R U R' U' F2 D L'"
.venv/bin/python -m speedsolver --random --colors white,yellow   # only these cross colors
```

### What "fastest" means

Solutions are ranked by an estimated execution time
(`speedsolver/ergonomics.py`). R and U turns count as quickest and B turns as
slowest, so the solver prefers a `y` rotation plus R/U/F/L moves over awkward
back-face turns, as a human would. The move count (STM) is shown alongside.
Pass `--metric STM` (or HTM/QTM) to rank by move count instead. The time is a
rough model that ignores recognition pauses, so use it to compare solutions,
not as a prediction of your solve time.

### Cross colors

By default the solver tries a cross on all six colors and keeps whichever
gives the fastest *whole* solution. To train with the colors you actually
use, limit the choice. In the terminal, pass `--colors` (e.g.
`white,yellow`, `w y` or `all`). In the window, click the color swatches
under "Cross colors", or use the **All** / **White/Yellow** presets. After a
solve, the window lists the total for every color tried. The window remembers
your choice in `~/.config/speedsolver/settings.json`.

In the window: type a scramble and press Enter (or **Apply**), then **Solve**.
Click any move in the solution list to jump there. Use the arrow keys to step,
Space to play or pause, and Home/End to jump to the start or end. Drag to look
around the cube and scroll to zoom.

The first solve builds a cross lookup table (about 1 s) and caches it in
`~/.cache/speedsolver/`.

## Tests

```bash
.venv/bin/python -m pytest
```

## Layout

| Path | Contents |
| --- | --- |
| `speedsolver/notation.py` | WCA notation parsing, inverting, cancelling |
| `speedsolver/cube.py` | Sticker-level cube model; all moves generated from 3D geometry |
| `speedsolver/search.py` | Piece-tracking move tables, cross table, F2L pair search |
| `speedsolver/algs.py` | Full OLL (57) and PLL (21) algorithm sets |
| `speedsolver/methods/cfop.py` | CFOP solver |
| `speedsolver/ergonomics.py` | Execution-time estimate used to rank solutions |
| `speedsolver/solution.py` | Stages, solutions, metrics (TIME/STM/HTM/QTM), cross-stage cancellation |
| `speedsolver/solver.py` | Runs all methods/variants (e.g. cross colors) in parallel and ranks them |
| `speedsolver/settings.py` | Remembered user settings (cross colors) |
| `speedsolver/ui/` | Ursina window (the only code that imports Ursina) |
