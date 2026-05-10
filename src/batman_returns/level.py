"""Level / tilemap and parallax background.

Mirrors the original "96 maps per stage" idea: each level is a long horizontal
strip of 16x16 tiles. We keep three stages with different palettes/themes:
1. Gotham streets (brick + ground)
2. Snow plaza (Cobblepot's lair approach)
3. Penguin's lair (boss arena)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Final

import pygame

from . import sprites
from .constants import (
    NATIVE_H,
    NATIVE_W,
    PALETTE,
    PARALLAX_FACTORS,
    TILE_SIZE,
)


@dataclass(slots=True)
class Stage:
    name: str
    length_tiles: int           # width of stage in tiles
    ground_tile: str            # sprite key
    sky_top: tuple[int, int, int]
    sky_bot: tuple[int, int, int]
    snow: bool = False
    enemy_density: float = 0.10  # spawn probability per tile column
    boss: bool = False           # last stage spawns Penguin


STAGES: Final = (
    Stage(
        name="GOTHAM STREETS",
        length_tiles=160,
        ground_tile="tile_ground",
        sky_top=(20, 8, 40),
        sky_bot=(80, 30, 100),
        enemy_density=0.10,
    ),
    Stage(
        name="ICE PLAZA",
        length_tiles=180,
        ground_tile="tile_snow",
        sky_top=(30, 30, 90),
        sky_bot=(140, 160, 200),
        snow=True,
        enemy_density=0.13,
    ),
    Stage(
        name="PENGUIN'S LAIR",
        length_tiles=120,
        ground_tile="tile_brick",
        sky_top=(20, 10, 30),
        sky_bot=(70, 40, 90),
        enemy_density=0.16,
        boss=True,
    ),
)


@dataclass(slots=True)
class Level:
    stage: Stage
    cam_x: float = 0.0
    width_px: int = 0
    snowflakes: list[list[float]] = field(default_factory=list)  # [x, y, vx, vy]
    skyline: list[tuple[int, int, int]] = field(default_factory=list)  # x, h, palette_idx

    def __post_init__(self) -> None:
        self.width_px = self.stage.length_tiles * TILE_SIZE
        rng = random.Random(hash(self.stage.name))
        # Procedural skyline silhouettes (mid parallax)
        x = 0
        while x < self.width_px * 1.5:
            h = rng.randint(40, 120)
            w = rng.randint(20, 50)
            shade = rng.randint(0, 2)
            self.skyline.append((x, h, w, shade))  # type: ignore[arg-type]
            x += w + rng.randint(2, 8)
        if self.stage.snow:
            for _ in range(60):
                self.snowflakes.append([
                    rng.uniform(0, NATIVE_W),
                    rng.uniform(0, NATIVE_H),
                    rng.uniform(-0.3, 0.3),
                    rng.uniform(0.3, 1.2),
                ])

    # ------------------------------------------------------------------
    def update(self, target_cam_x: float, dt: float) -> None:
        # Smooth camera lerp
        self.cam_x += (target_cam_x - self.cam_x) * min(1.0, dt * 8)
        self.cam_x = max(0.0, min(self.cam_x, self.width_px - NATIVE_W))
        # Snowflakes
        for f in self.snowflakes:
            f[0] += f[2]
            f[1] += f[3]
            if f[1] > NATIVE_H:
                f[1] = 0
                f[0] = (f[0] + 7) % NATIVE_W
            if f[0] < 0:
                f[0] = NATIVE_W
            elif f[0] > NATIVE_W:
                f[0] = 0

    # ------------------------------------------------------------------
    def draw(self, surf: pygame.Surface) -> None:
        self._draw_sky(surf)
        self._draw_skyline(surf)
        self._draw_ground(surf)
        if self.stage.snow:
            for f in self.snowflakes:
                surf.set_at((int(f[0]), int(f[1])), PALETTE["snow"])

    def _draw_sky(self, surf: pygame.Surface) -> None:
        top = self.stage.sky_top
        bot = self.stage.sky_bot
        for y in range(NATIVE_H):
            t = y / NATIVE_H
            r = int(top[0] * (1 - t) + bot[0] * t)
            g = int(top[1] * (1 - t) + bot[1] * t)
            b = int(top[2] * (1 - t) + bot[2] * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (NATIVE_W, y))

    def _draw_skyline(self, surf: pygame.Surface) -> None:
        offs = self.cam_x * PARALLAX_FACTORS[1]
        shades = [PALETTE["dark"], PALETTE["night"], PALETTE["purple"]]
        ground_y = NATIVE_H - 32
        for x, h, w, shade in self.skyline:  # type: ignore[misc]
            sx = int(x - offs) % (self.width_px + NATIVE_W) - NATIVE_W
            if sx + w < 0 or sx > NATIVE_W:
                continue
            pygame.draw.rect(surf, shades[shade], (sx, ground_y - h, w, h))
            # window dots
            for wy in range(ground_y - h + 6, ground_y - 4, 6):
                for wx in range(sx + 3, sx + w - 3, 5):
                    if (wx + wy) % 11 < 4:
                        surf.set_at((wx, wy), PALETTE["yellow"])

    def _draw_ground(self, surf: pygame.Surface) -> None:
        tile = sprites.get(self.stage.ground_tile)
        ground_y = NATIVE_H - 32
        cam_t = int(self.cam_x) // TILE_SIZE
        offset = int(self.cam_x) % TILE_SIZE
        for col in range(NATIVE_W // TILE_SIZE + 2):
            tx = (cam_t + col) % self.stage.length_tiles
            sx = col * TILE_SIZE - offset
            for row in range(2):
                surf.blit(tile, (sx, ground_y + row * TILE_SIZE))
            # platform variation: occasional brick block floating
            if (tx * 7919) % 23 == 0 and tx > 5:
                surf.blit(sprites.get("tile_brick"), (sx, ground_y - 48))
                surf.blit(sprites.get("tile_brick"), (sx + 16, ground_y - 48))

    # ------------------------------------------------------------------
    def world_to_screen(self, x: float) -> int:
        return int(x - self.cam_x)
