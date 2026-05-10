"""Lightweight particle + screen-shake effects for juice.

No allocations on the hot path: particles live in a fixed-capacity ring buffer
recycled in place. ``ScreenShake`` returns a per-frame (dx, dy) offset to
apply when blitting the canvas.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Final

import pygame

from .constants import PALETTE


@dataclass(slots=True)
class Particle:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    life: int = 0
    max_life: int = 1
    color: tuple[int, int, int] = (255, 255, 255)
    gravity: float = 0.0
    size: int = 1
    alive: bool = False


_CAPACITY: Final = 256


class ParticleSystem:
    """Fixed-capacity recycled-particle pool."""

    __slots__ = ("_pool", "_cursor")

    def __init__(self) -> None:
        self._pool: list[Particle] = [Particle() for _ in range(_CAPACITY)]
        self._cursor = 0

    def _next(self) -> Particle:
        # Find a dead slot starting from cursor; if none, overwrite cursor.
        for _ in range(_CAPACITY):
            p = self._pool[self._cursor]
            self._cursor = (self._cursor + 1) % _CAPACITY
            if not p.alive:
                return p
        return self._pool[self._cursor]

    def emit(
        self,
        x: float,
        y: float,
        *,
        count: int = 6,
        speed: float = 2.0,
        life: int = 18,
        color: tuple[int, int, int] = PALETTE["yellow"],
        gravity: float = 0.15,
        size: int = 1,
        spread: float = math.tau,
        angle: float = 0.0,
    ) -> None:
        for _ in range(count):
            p = self._next()
            theta = angle + (random.random() - 0.5) * spread
            v = speed * (0.5 + random.random())
            p.x = x
            p.y = y
            p.vx = math.cos(theta) * v
            p.vy = math.sin(theta) * v
            p.life = life + random.randint(-3, 3)
            p.max_life = max(1, p.life)
            p.color = color
            p.gravity = gravity
            p.size = size
            p.alive = True

    def burst_hit(self, x: float, y: float) -> None:
        self.emit(x, y, count=8, speed=2.6, life=12, color=PALETTE["yellow"])
        self.emit(x, y, count=4, speed=1.8, life=14, color=PALETTE["white"])

    def burst_blood(self, x: float, y: float, dir_sign: int = 1) -> None:
        self.emit(
            x, y,
            count=10, speed=2.2, life=18,
            color=PALETTE["red"], gravity=0.3,
            spread=math.pi * 0.8, angle=0 if dir_sign >= 0 else math.pi,
        )

    def dust(self, x: float, y: float) -> None:
        self.emit(
            x, y,
            count=5, speed=1.0, life=14,
            color=PALETTE["gray"], gravity=-0.05,
            spread=math.pi * 0.6, angle=-math.pi / 2,
            size=2,
        )

    def spark(self, x: float, y: float, color: tuple[int, int, int]) -> None:
        self.emit(x, y, count=4, speed=2.4, life=10, color=color)

    def update(self) -> None:
        for p in self._pool:
            if not p.alive:
                continue
            p.x += p.vx
            p.y += p.vy
            p.vy += p.gravity
            p.life -= 1
            if p.life <= 0:
                p.alive = False

    def draw(self, surf: pygame.Surface, cam_x: float) -> None:
        for p in self._pool:
            if not p.alive:
                continue
            sx = int(p.x - cam_x)
            sy = int(p.y)
            if -8 <= sx <= surf.get_width() + 8:
                # fade by life
                t = p.life / p.max_life
                col = (
                    int(p.color[0] * t + 30 * (1 - t)),
                    int(p.color[1] * t + 30 * (1 - t)),
                    int(p.color[2] * t + 30 * (1 - t)),
                )
                if p.size <= 1:
                    surf.set_at((sx, sy), col)
                else:
                    pygame.draw.rect(surf, col, (sx, sy, p.size, p.size))


@dataclass(slots=True)
class ScreenShake:
    intensity: float = 0.0
    decay: float = 0.85

    def kick(self, amount: float) -> None:
        self.intensity = max(self.intensity, amount)

    def update(self) -> tuple[int, int]:
        if self.intensity < 0.2:
            self.intensity = 0
            return (0, 0)
        dx = int((random.random() - 0.5) * self.intensity * 2)
        dy = int((random.random() - 0.5) * self.intensity * 2)
        self.intensity *= self.decay
        return (dx, dy)


@dataclass(slots=True)
class HitFreeze:
    """Brief frame-freeze on big impacts (game-feel)."""
    frames: int = 0

    def kick(self, n: int) -> None:
        self.frames = max(self.frames, n)

    def tick(self) -> bool:
        """Returns True if game logic should be skipped this frame."""
        if self.frames > 0:
            self.frames -= 1
            return True
        return False


@dataclass(slots=True)
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    life: int = 30
    vy: float = -1.0
    alive: bool = True


@dataclass(slots=True)
class FloatingTextSystem:
    items: list[FloatingText] = field(default_factory=list)

    def emit(self, text: str, x: float, y: float, color: tuple[int, int, int] = PALETTE["yellow"]) -> None:
        self.items.append(FloatingText(text=text, x=x, y=y, color=color))

    def update(self) -> None:
        for f in self.items:
            f.y += f.vy
            f.vy *= 0.92
            f.life -= 1
            if f.life <= 0:
                f.alive = False
        self.items = [f for f in self.items if f.alive]

    def draw(self, surf: pygame.Surface, cam_x: float) -> None:
        from .hud import draw_text
        for f in self.items:
            sx = int(f.x - cam_x) - len(f.text) * 3
            draw_text(surf, f.text, sx, int(f.y), f.color, scale=1)
