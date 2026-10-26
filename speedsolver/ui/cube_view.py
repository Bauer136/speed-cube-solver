"""3D cube drawn with Ursina.

The view never keeps its own idea of the cube: after every animation it
puts all cubies back home and recolors the stickers from the model state.
Ursina's axes are x right, y up, z into the screen, so the model's z
(towards the viewer) is flipped. A positive Ursina ``rotation_x/y/z`` turns
the same way as a clockwise model turn about +x, +y, +z.
"""

from __future__ import annotations

from ursina import Entity, Vec3, color, time

from ..cube import MOVE_GEOMETRY, SLOTS, Cube
from ..notation import Move

STICKER_COLORS = [
    color.hex("#f4f4f4"),  # U white
    color.hex("#c8102e"),  # R red
    color.hex("#009b48"),  # F green
    color.hex("#ffd500"),  # D yellow
    color.hex("#ff5800"),  # L orange
    color.hex("#0046ad"),  # B blue
]
BODY_COLOR = color.hex("#111111")


def to_ursina(v) -> Vec3:
    return Vec3(v[0], v[1], -v[2])


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)


class CubeView(Entity):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.pivot = Entity(parent=self)
        self.cubies: dict[tuple[int, int, int], Entity] = {}
        for pos in sorted({pos for pos, _ in SLOTS}):
            cubie = Entity(parent=self, position=to_ursina(pos))
            Entity(parent=cubie, model="cube", color=BODY_COLOR, scale=0.96)
            self.cubies[pos] = cubie
        self.stickers: list[Entity] = []
        for pos, normal in SLOTS:
            scale = [0.84, 0.84, 0.84]
            scale[[abs(c) for c in normal].index(1)] = 0.02
            sticker = Entity(
                parent=self.cubies[pos], model="cube", position=to_ursina(normal) * 0.49, scale=scale
            )
            self.stickers.append(sticker)
        self._anim: tuple[str, float, list[Entity], Cube] | None = None
        self._elapsed = 0.0
        self._duration = 0.0
        self.show(Cube())

    @property
    def animating(self) -> bool:
        return self._anim is not None

    def show(self, cube: Cube) -> None:
        """Display ``cube`` immediately, cancelling any animation."""
        if self._anim:
            self._reset_layer(self._anim[2])
            self._anim = None
        for sticker, sticker_id in zip(self.stickers, cube.stickers):
            sticker.color = STICKER_COLORS[sticker_id // 9]

    def animate(self, move: Move, result: Cube, duration: float = 0.25) -> None:
        """Turn the layer(s) of ``move``, then show ``result``."""
        self.finish()
        axis, layers, direction = MOVE_GEOMETRY[move.name]
        angle = 90 * direction * {1: 1, 2: 2, 3: -1}[move.turns]
        layer = [c for pos, c in self.cubies.items() if pos[axis] in layers]
        for cubie in layer:
            cubie.parent = self.pivot
        self._anim = ("xyz"[axis], angle, layer, result)
        self._elapsed = 0.0
        self._duration = max(duration, 1e-3)

    def finish(self) -> None:
        """Jump to the end of the current animation."""
        if self._anim:
            self.show(self._anim[3])

    def _reset_layer(self, layer: list[Entity]) -> None:
        self.pivot.rotation = (0, 0, 0)
        for cubie in layer:
            cubie.parent = self
        for pos, cubie in self.cubies.items():
            cubie.position = to_ursina(pos)
            cubie.rotation = (0, 0, 0)

    def update(self) -> None:
        if not self._anim:
            return
        axis, angle, _, _ = self._anim
        self._elapsed += time.dt
        t = min(self._elapsed / self._duration, 1.0)
        setattr(self.pivot, f"rotation_{axis}", angle * _ease(t))
        if t >= 1.0:
            self.finish()
