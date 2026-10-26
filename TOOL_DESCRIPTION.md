# SpeedSolverTool: Tool Description

## Purpose

SpeedSolverTool is a Rubik's cube (3x3) speed-solving assistant. The user enters
a scramble, and the tool finds the fastest solution a human speedcuber could
realistically execute. It then plays that solution move by move on a live 3D
cube.

The tool solves the way a speedcuber does. It does **not** aim for a
computer-optimal solve (God's number / Kociemba-style shortest solutions).
Every solution must come from real speed-solving methods: their steps, their
patterns and their named algorithms, so the user can learn from and reproduce it.

## Platform

A **local program** that runs on the user's machine. It is **not a web app**:
no browser UI and no hosted server. The visual runs in a native desktop window.

### Tech stack
- **Language:** Python 3.
- **UI / 3D:** [Ursina](https://www.ursinaengine.org/) (`pip install ursina`), picked
  because it is the easiest option. It opens a native window, draws simple 3D
  shapes (27 cubies) with very little code, has built-in animation for
  rotating face layers, and includes UI widgets (text input, buttons, panels)
  for the scramble field and the clickable move list. So one package covers
  everything.
- **Fallback:** if Ursina's UI widgets become limiting, PySide6 (Qt) with an
  embedded OpenGL view is the heavier but more flexible alternative.
- **Structure:** keep the solver/cube-model logic in plain Python modules with no
  UI imports, so it can be tested on its own (pytest). The UI layer only
  draws and animates the state the model gives it.

## Core Features

### 1. Scramble input
- An on-screen interface where the user enters the current scramble.
- Input as standard WCA move notation (e.g. `R U R' U' F2 D L'`).
- The cube visual updates to show the scrambled state.

### 2. Method-based solver
- Solves the scramble with a variety of established speed-solving methods.
  Candidates include CFOP (Cross → F2L → OLL → PLL), Roux, ZZ and Petrus.
- Within each method, it searches for the fastest sequence: it picks among
  cross/block options, F2L pair orderings, algorithm choices, cancellations
  and similar options.
- Compares results across methods and shows the fastest one.
- Solutions are broken into the method's named stages (e.g. "Cross", "F2L pair 1",
  "OLL 27", "PLL T-perm") so the user can see the reasoning.

### 3. Live cube visual
- A live, animated visual of the cube itself.
- Each move animates as it is made, so the user sees the solve unfold.

### 4. Move history / scrubbing
- The solution is shown as a clickable list of moves (grouped by stage).
- Clicking any earlier or later move jumps the cube to the state at that point.
- Supports stepping forward and back through the solve.

## Guiding Principles
- **Human-executable over computer-optimal**: a slightly longer solution built
  from known patterns beats a shorter one no human would find.
- **Explainable**: every move belongs to a recognizable method stage or algorithm.
- **Visual first**: the cube display and move scrubbing are central to the
  experience, not an extra.

## Settled Decisions
- **First method: CFOP**, color neutral by default. The user can limit the
  allowed cross colors (e.g. white/yellow only) in the window or with
  `--colors`. Among the allowed colors the solver keeps the one whose *whole*
  solution is fastest, not just the shortest cross, and shows every color's
  total. The solver tries each allowed cross color
  (with the inspection rotation shown as its own stage), the optimal crosses
  that are easiest to execute, and a beam search over F2L pair orders. For
  each pair it takes the optimal ⟨U,R,F,L,B⟩ sequences that keep the cross
  and earlier pairs and keeps the easiest to execute. Like a human, it may
  turn the cube with `y` before a pair so the pair goes in with R/U/F/L
  instead of B moves; a dynamic program picks the orientation for every
  step. OLL/PLL are recognised by table lookup in whatever orientation the
  cube is held, trying every pre-AUF so moves cancel into the previous
  stage. Roux, ZZ and Petrus come later, behind the same method interface
  (`variants()` + `solve()`).
- **"Fastest" = estimated execution time** (`speedsolver/ergonomics.py`):
  per-move times where R/U are quickest, L/F/D slower, B slowest, half turns
  take longer and rotations cost a little (free during inspection). STM is
  shown next to it, and `--metric STM|HTM|QTM` ranks by move count instead.
  The weights are a rough first model, not measured data.
- **Algorithm sets (for now): full OLL (57) and full PLL (21).** Tests check
  that every algorithm keeps F2L intact and that the sets cover all 216
  orientation cases and all 288 permutation cases.

## Open Decisions (to be settled as the project develops)
- Refining the execution-time model: calibrate the weights against real
  timings and model regrips and move-to-move flow (e.g. R U R' U' flows,
  F after R needs a regrip), which per-move weights cannot capture.
- Further algorithm sets (COLL, ZBLL, F2L case algorithms, alternatives per case).
- Whether to add other input modes (clicking stickers to paint a physical
  cube's state, camera input) alongside notation.
- Puzzle scope beyond 3x3.
