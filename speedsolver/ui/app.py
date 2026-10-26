"""The SpeedSolverTool window.

Controls: type a scramble and press Enter (or Apply), then Solve. Click any
move in the solution list to jump there. Arrow keys step, Space plays or
pauses, Home/End jump to the ends. Drag with the mouse to look around the
cube, scroll to zoom.
"""

from __future__ import annotations

import textwrap
import threading

from ursina import (
    Button,
    Entity,
    InputField,
    Text,
    Tooltip,
    Ursina,
    camera,
    clamp,
    color,
    destroy,
    held_keys,
    mouse,
    window,
)

from ..cube import FACES, Cube
from ..methods.cfop import CFOP, COLOR_NAMES, CROSS_COLORS
from ..notation import Move, parse_moves
from ..scramble import random_scramble
from ..settings import load_cross_colors, save_cross_colors
from ..solution import Solution, htm
from ..solver import solve_all
from .cube_view import STICKER_COLORS, CubeView

COLOR_OF_NAME = {name: STICKER_COLORS[FACES.index(face)] for face, name in COLOR_NAMES.items()}
SWATCH_ON, SWATCH_OFF = 0.045, 0.03

BG = color.hex("#1d2026")
PANEL = color.hex("#2a2e37")
BUTTON = color.hex("#3a4050")
ACCENT = color.hex("#4f8ef7")
DONE = color.hex("#2f3440")
ERROR = color.hex("#ff6b6b")

STEP_TIME = 0.22
PLAY_TIME = 0.28
MOVES_PER_ROW = 8
MOVE_W, MOVE_H = 0.052, 0.034


class SolverApp(Entity):
    def __init__(self) -> None:
        super().__init__()
        self.rig = Entity(rotation=(28, -35, 0))
        camera.parent = self.rig
        camera.position = (0, 0, -14)
        camera.rotation = (0, 0, 0)
        camera.fov = 40
        # Shift the picture left so the cube sits between the text and the move list.
        camera.lens.setFilmOffset(0.06, 0)
        self.view = CubeView()

        # camera.ui spans y -0.5..0.5 and x +-aspect_ratio/2.
        left = -window.aspect_ratio / 2 + 0.03
        right = window.aspect_ratio / 2 - 0.03
        field_x = left + 0.14
        Text("Scramble", position=(left, 0.462), scale=0.9, color=color.light_gray)
        self.scramble_field = InputField(
            default_value="", character_limit=160, max_lines=1, color=PANEL,
            position=((field_x + right) / 2, 0.45), scale=(right - field_x, 0.045),
        )
        self.scramble_field.text_field.scale *= 0.75  # room for 30+ move scrambles
        for k, (label, action) in enumerate(
            [("Apply", self.apply_scramble), ("Random", self.random), ("Solve", self.start_solve), ("Reset", self.reset)]
        ):
            b = self._button(label, (field_x + 0.06 + k * 0.14, 0.39), action, width=0.12,
                             tint=ACCENT if label == "Solve" else BUTTON)
            if label == "Solve":
                self.solve_button = b
        self.status = Text("", position=(left, 0.33), scale=0.85)

        # Cross color setting: click a swatch to allow or forbid that color.
        Text("Cross colors", position=(left, 0.25), scale=0.8, color=color.light_gray)
        self.swatches: dict[str, Button] = {}
        for k, name in enumerate(CROSS_COLORS):
            b = Button(position=(left + SWATCH_ON / 2 + k * 0.055, 0.19), scale=SWATCH_ON,
                       color=COLOR_OF_NAME[name])
            b.on_click = lambda name=name: self.toggle_cross_color(name)
            b.tooltip = Tooltip(name)
            self.swatches[name] = b
        self._button("All", (left + 0.05, 0.13), lambda: self.set_cross_colors(CROSS_COLORS), width=0.1)
        self._button("White/Yellow", (left + 0.2, 0.13),
                     lambda: self.set_cross_colors(("white", "yellow")), width=0.18)
        self.colors_text = Text("", position=(left, 0.085), scale=0.7, color=color.gray)
        # After a solve: the total for every color tried, best first.
        self.summary = Text("", position=(left, 0.0), scale=0.75, color=color.light_gray)

        panel_x = right - MOVES_PER_ROW * MOVE_W
        Text("Solution", position=(panel_x, 0.33), scale=0.9, color=color.light_gray)
        self.move_panel = Entity(parent=camera.ui, position=(panel_x, 0.29))
        self.panel_height = 0.29 + 0.40  # down to just above the playback controls
        self.move_buttons: list[Button] = []

        # Ursina reads < and > as text markup, so the labels are words.
        controls = [("Start", self.to_start), ("Back", lambda: self.step(-1)), ("Play", self.toggle_play),
                    ("Next", lambda: self.step(1)), ("End", self.to_end)]
        self.play_button = None
        for k, (label, action) in enumerate(controls):
            b = self._button(label, (-0.24 + k * 0.12, -0.44), action, width=0.1)
            if label == "Play":
                self.play_button = b
        Text("drag: look around    scroll: zoom    arrow keys: step    space: play",
             position=(0, -0.485), origin=(0, 0), scale=0.7, color=color.gray)

        self.scramble: list[Move] = []
        self.solution: Solution | None = None
        self.timeline: list[Move] = []
        self.states: list[Cube] = [Cube()]
        self.index = 0
        self.playing = False
        self._dragging = False
        self._result: tuple | None = None
        self._solving = False
        self.cross_colors: tuple[str, ...] = ()
        self.set_cross_colors(load_cross_colors(), save=False)

    def _button(self, text, pos, action, width=0.1, tint=BUTTON) -> Button:
        b = Button(text=text, position=pos, scale=(width, 0.045), color=tint,
                   highlight_color=tint.tint(0.15), text_size=0.75)
        b.on_click = action
        return b

    # --- scramble ---------------------------------------------------------

    def apply_scramble(self) -> bool:
        text = self.scramble_field.text_field.text
        try:
            moves = parse_moves(text)
        except ValueError as exc:
            self._set_status(str(exc), error=True)
            return False
        self.scramble = moves
        self._set_timeline(Cube().apply(moves), [], None)
        self._set_status(f"Scramble applied ({len(moves)} moves)." if moves else "Solved cube.")
        return True

    def random(self) -> None:
        self.scramble_field.text_field.text = random_scramble()
        self.scramble_field.text_field.render()
        self.apply_scramble()

    def reset(self) -> None:
        self.scramble_field.text_field.text = ""
        self.scramble_field.text_field.render()
        self.apply_scramble()

    # --- cross colors ---------------------------------------------------------

    def toggle_cross_color(self, name: str) -> None:
        chosen = set(self.cross_colors)
        if name in chosen:
            if len(chosen) == 1:
                self._set_status("Keep at least one cross color.", error=True)
                return
            chosen.remove(name)
        else:
            chosen.add(name)
        self.set_cross_colors(tuple(c for c in CROSS_COLORS if c in chosen))

    def set_cross_colors(self, colors: tuple[str, ...], save: bool = True) -> None:
        self.cross_colors = colors
        for name, swatch in self.swatches.items():
            on = name in colors
            c = COLOR_OF_NAME[name]
            # Off: smaller and see-through, but still recognisably that color.
            swatch.color = c if on else color.Color(c[0], c[1], c[2], 0.3)
            swatch.highlight_color = swatch.color.tint(0.1)
            swatch.scale = SWATCH_ON if on else SWATCH_OFF
        if len(colors) == len(CROSS_COLORS):
            text = "Picks the fastest of all six"
        elif len(colors) == 1:
            text = f"Always {colors[0]}"
        else:
            text = "Picks the fastest of " + ", ".join(colors)
        self.colors_text.text = "\n".join(textwrap.wrap(text, 32))  # stay clear of the cube
        if save:
            save_cross_colors(colors)

    # --- solving ------------------------------------------------------------

    def start_solve(self) -> None:
        if self._solving or not self.apply_scramble():
            return
        if not self.scramble:
            self._set_status("Nothing to solve: enter a scramble first.")
            return
        self._solving = True
        self.solve_button.text = "..."
        n = len(self.cross_colors)
        self._set_status(f"Solving ({n} cross color{'s' if n > 1 else ''})...")
        scramble = list(self.scramble)
        method = CFOP(cross_colors=self.cross_colors)

        def work() -> None:
            try:
                self._result = ("ok", solve_all(scramble, methods=[method]))
            except Exception as exc:  # shown to the user, not swallowed
                self._result = ("error", exc)

        threading.Thread(target=work, daemon=True).start()

    def _finish_solve(self) -> None:
        kind, value = self._result
        self._result = None
        self._solving = False
        self.solve_button.text = "Solve"
        if kind == "error":
            self._set_status(f"Solver failed: {value}", error=True)
            return
        if not value:
            self._set_status("No solution found.", error=True)
            return
        best = value[0]  # solve_all returns every color's solution, shortest first
        self._set_timeline(Cube().apply(self.scramble), best.moves, best)
        self._set_status(f"{best.method}, {best.variant}: {best.score()}, {htm(best.scored_moves)} HTM")
        if len(value) > 1:
            lines = [f"{s.variant}   {s.score()}" + ("   (chosen)" if s is best else "") for s in value]
            self.summary.text = "Fastest to execute first\n" + "\n".join(lines)

    # --- timeline -----------------------------------------------------------

    def _set_timeline(self, start: Cube, moves: list[Move], solution: Solution | None) -> None:
        self.playing = False
        self.solution = solution
        self.timeline = moves
        self.states = [start]
        for m in moves:
            self.states.append(self.states[-1].apply([m]))
        self.index = 0
        self.view.show(start)
        self._build_move_list()

    def _build_move_list(self) -> None:
        for child in list(self.move_panel.children):
            destroy(child)
        self.move_buttons = []
        self.summary.text = ""
        if not self.solution:
            return
        # Built at full size from the panel's top-left corner, then scaled to fit.
        self.move_panel.scale = 1
        y = 0.0
        k = 0
        for stage in self.solution.stages:
            label = stage.name + (f"  ·  {stage.detail}" if stage.detail else "")
            Text(label, parent=self.move_panel, position=(0, y), scale=0.72, color=color.light_gray)
            y -= 0.028
            if not stage.moves:
                Text("skip", parent=self.move_panel, position=(0.01, y + 0.004), scale=0.65, color=color.gray)
                y -= 0.024
                continue
            for j, move in enumerate(stage.moves):
                if j and j % MOVES_PER_ROW == 0:
                    y -= MOVE_H + 0.004
                b = Button(text=str(move), parent=self.move_panel, scale=(MOVE_W - 0.004, MOVE_H),
                           position=(MOVE_W / 2 + (j % MOVES_PER_ROW) * MOVE_W, y - MOVE_H / 2 + 0.004),
                           color=BUTTON, text_size=0.7)
                b.on_click = lambda target=k + 1: self.jump(target)
                self.move_buttons.append(b)
                k += 1
            y -= MOVE_H + 0.012
        if -y > self.panel_height:
            self.move_panel.scale = self.panel_height / -y
        self._highlight()

    def _highlight(self) -> None:
        for k, b in enumerate(self.move_buttons):
            if k == self.index - 1:
                b.color = ACCENT
            elif k < self.index - 1:
                b.color = DONE
            else:
                b.color = BUTTON
            b.highlight_color = b.color.tint(0.15)

    def step(self, delta: int, duration: float = STEP_TIME) -> None:
        if delta > 0 and self.index < len(self.timeline):
            move = self.timeline[self.index]
            self.index += 1
        elif delta < 0 and self.index > 0:
            move = self.timeline[self.index - 1].inverse()
            self.index -= 1
        else:
            return
        self.view.animate(move, self.states[self.index], duration)
        self._highlight()

    def jump(self, index: int) -> None:
        self.playing = False
        self.index = max(0, min(index, len(self.timeline)))
        self.view.show(self.states[self.index])
        self._highlight()
        self._sync_play_label()

    def to_start(self) -> None:
        self.jump(0)

    def to_end(self) -> None:
        self.jump(len(self.timeline))

    def toggle_play(self) -> None:
        if not self.timeline:
            return
        if not self.playing and self.index == len(self.timeline):
            self.jump(0)
        self.playing = not self.playing
        self._sync_play_label()

    def _sync_play_label(self) -> None:
        if self.play_button:
            self.play_button.text = "Pause" if self.playing else "Play"

    def _set_status(self, text: str, error: bool = False) -> None:
        self.status.text = text
        self.status.color = ERROR if error else color.white

    # --- Ursina hooks ---------------------------------------------------

    def update(self) -> None:
        if self._result is not None:
            self._finish_solve()
        if self.playing and not self.view.animating:
            if self.index < len(self.timeline):
                self.step(1, PLAY_TIME)
            else:
                self.playing = False
                self._sync_play_label()
        if self._dragging:
            if held_keys["left mouse"] or held_keys["right mouse"]:
                self.rig.rotation_y += mouse.velocity[0] * 250
                self.rig.rotation_x = clamp(self.rig.rotation_x - mouse.velocity[1] * 250, -85, 85)
            else:
                self._dragging = False

    def input(self, key: str) -> None:
        if self.scramble_field.active:
            if key == "enter":
                self.apply_scramble()
            return
        if key in ("left mouse down", "right mouse down") and mouse.hovered_entity is None:
            self._dragging = True
        elif key == "scroll up":
            camera.z = min(camera.z + 1, -7)
        elif key == "scroll down":
            camera.z = max(camera.z - 1, -30)
        elif key in ("right arrow", "right arrow hold"):
            self.step(1)
        elif key in ("left arrow", "left arrow hold"):
            self.step(-1)
        elif key == "space":
            self.toggle_play()
        elif key == "home":
            self.to_start()
        elif key == "end":
            self.to_end()


def run() -> None:
    app = Ursina(title="SpeedSolverTool", development_mode=False, size=(1400, 860))
    window.color = BG
    window.fps_counter.enabled = False
    window.exit_button.visible = False
    SolverApp()
    app.run()
