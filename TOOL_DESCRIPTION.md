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

## Open Decisions (to be settled as the project develops)
- Which methods to support first (CFOP is the likely starting point).
- How "fastest" is measured: move count (HTM/STM/QTM), estimated execution
  time (finger-trick ergonomics, regrips), or a mix.
- Algorithm sets to include (full OLL/PLL, COLL, ZBLL, etc.).
- Whether to add other input modes (clicking stickers to paint a physical
  cube's state, camera input) alongside notation.
- Puzzle scope beyond 3x3.
