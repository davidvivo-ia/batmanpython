"""Game constants — mostly mirrored from the original BATMAN.EQU / TECH.DOC."""

from __future__ import annotations

from enum import IntEnum, StrEnum, auto
from typing import Final

# --- Display (TECH.DOC: 32x24 char playfield, 16x16 tiles -> 320x224 effective) ---
TILE_SIZE: Final = 16
PLAYFIELD_TILES_W: Final = 20  # 320 / 16 — wider than original 32 char map (cropped HUD)
PLAYFIELD_TILES_H: Final = 14
NATIVE_W: Final = PLAYFIELD_TILES_W * TILE_SIZE  # 320
NATIVE_H: Final = PLAYFIELD_TILES_H * TILE_SIZE  # 224
SCALE: Final = 3
WINDOW_W: Final = NATIVE_W * SCALE
WINDOW_H: Final = NATIVE_H * SCALE
FPS: Final = 60  # original drove 20fps; we run smooth 60

# --- Physics ---
GRAVITY: Final = 0.55
JUMP_SPEED: Final = -8.5
WALK_SPEED: Final = 2.2
RUN_SPEED: Final = 3.4
GROUND_Y: Final = NATIVE_H - 32  # leave room for HUD
WORLD_W_TILES: Final = 96  # original: 96 maps per stage

# --- Combat ---
PUNCH_DAMAGE: Final = 25
KICK_DAMAGE: Final = 35
BATARANG_DAMAGE: Final = 50
PUNCH_FRAMES: Final = 12
KICK_FRAMES: Final = 16
HITSTUN_FRAMES: Final = 18
IFRAMES: Final = 30
PLAYER_MAX_HP: Final = 100
STARTING_LIVES: Final = 3
STARTING_BATARANGS: Final = 5

# --- Score (from BATMAN.EQU) ---
SCORE_OBSTACLE: Final = 100
SCORE_SMALL: Final = 200
SCORE_ENEMY: Final = 500
SCORE_MIDBOSS: Final = 2000
SCORE_BOSS: Final = 5000
EXTRA_LIFE_AT: Final = 20_000

# --- Palette (NES-ish high-contrast, 16 colors) ---
# (Plain assignment instead of PEP 695 `type` so we stay compatible with 3.11.)
RGB = tuple[int, int, int]
PALETTE: Final[dict[str, RGB]] = {
    "black":      (10, 10, 14),
    "dark":       (24, 22, 38),
    "night":      (48, 40, 80),
    "purple":     (96, 64, 156),
    "magenta":    (180, 60, 140),
    "gray":       (120, 120, 130),
    "lightgray":  (180, 180, 190),
    "white":      (240, 240, 248),
    "skin":       (240, 200, 160),
    "yellow":     (250, 200, 60),
    "orange":     (240, 130, 50),
    "red":        (220, 50, 50),
    "bloodred":   (140, 30, 30),
    "green":      (80, 200, 100),
    "snow":       (220, 230, 240),
    "shadow":     (0, 0, 0),
}


class GameState(StrEnum):
    TITLE = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    LEVEL_INTRO = auto()
    STAGE_CLEAR = auto()      # post-stage summary + bonuses
    HIGH_SCORES = auto()
    PAUSE_CONTROLS = auto()   # sub-screen: full controls reference
    SETTINGS = auto()
    STAGE_SELECT = auto()


class Difficulty(StrEnum):
    EASY = auto()
    NORMAL = auto()
    HARD = auto()


# Multipliers per difficulty applied to enemy HP and contact damage.
DIFFICULTY_SCALARS = {
    "easy":   {"enemy_hp": 0.7, "enemy_dmg": 0.7, "starting_batarangs": 8},
    "normal": {"enemy_hp": 1.0, "enemy_dmg": 1.0, "starting_batarangs": 5},
    "hard":   {"enemy_hp": 1.5, "enemy_dmg": 1.4, "starting_batarangs": 3},
}

# New Game Plus modifies the difficulty scalar on top.
NG_PLUS_HP_MULT = 2.0
NG_PLUS_DMG_MULT = 1.5
NG_PLUS_LIVES_DELTA = -1  # one less starting life


class PlayerState(StrEnum):
    IDLE = auto()
    WALK = auto()
    JUMP = auto()
    PUNCH = auto()
    KICK = auto()
    THROW = auto()
    HURT = auto()
    DEAD = auto()
    SLIDE = auto()
    DIVEKICK = auto()


# Combo system: chained hits within COMBO_WINDOW frames build multiplier.
COMBO_WINDOW: Final = 90  # 1.5s
COMBO_DAMAGE_BONUS: Final = 0.15  # +15% per combo step
COMBO_SCORE_BONUS: Final = 0.25
DIVEKICK_DAMAGE: Final = 50
SLIDE_DAMAGE: Final = 30
SLIDE_SPEED: Final = 5.0
SLIDE_FRAMES: Final = 22


class Facing(IntEnum):
    LEFT = -1
    RIGHT = 1


class EnemyKind(StrEnum):
    BASHER = auto()         # BASHER.68K — clown thug, melee
    JACKBOX = auto()        # JACKNBOX.68K — pop-up surprise
    FIREBREATHER = auto()   # FIRETRUC.68K + MINIFIRE.68K
    KNIFER = auto()         # disc/knife thrower
    SKATER = auto()         # Ice Plaza fast slider
    CYCLE = auto()          # LEVEL_1/CYCLE.68K — motorcycle clown
    TANK = auto()           # LEVEL_2/TANK.68K — slow heavy w/ shells
    CANNON = auto()         # LEVEL_2/CANNON.68K — stationary turret
    WKLITE = auto()         # LEVEL_3/WKLITE.68K — heavy ramming clown
    MIDBOSS_JOKER = auto()  # stage 1 midboss
    MIDBOSS_CATWOMAN = auto()  # stage 2 midboss
    BOSS_PENGUIN = auto()   # VILLAN.68K final boss


# Layer 0 = far parallax (clouds), 1 = mid (skyline), 2 = ground/foreground
PARALLAX_FACTORS: Final = (0.15, 0.45, 1.0)
