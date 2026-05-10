"""Entities: Batman, enemies, projectiles. Modern dataclass-based.

Inspired by the Sega CD source structure (PLAYER.68K, OBJECT.68K, BASHER.68K,
JACKNBOX.68K, FIRETRUC.68K, VILLAN.68K). We don't replicate the bytecode —
just the silhouette of behaviours.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self

import pygame

from . import audio, sprites
from .constants import (
    BATARANG_DAMAGE,
    COMBO_DAMAGE_BONUS,
    COMBO_SCORE_BONUS,
    COMBO_WINDOW,
    DIVEKICK_DAMAGE,
    GRAVITY,
    GROUND_Y,
    HITSTUN_FRAMES,
    IFRAMES,
    JUMP_SPEED,
    KICK_DAMAGE,
    KICK_FRAMES,
    PALETTE,
    PLAYER_MAX_HP,
    PUNCH_DAMAGE,
    PUNCH_FRAMES,
    RUN_SPEED,
    SCORE_BOSS,
    SCORE_ENEMY,
    SCORE_MIDBOSS,
    SLIDE_DAMAGE,
    SLIDE_FRAMES,
    SLIDE_SPEED,
    WALK_SPEED,
    EnemyKind,
    Facing,
    PlayerState,
)

if TYPE_CHECKING:
    from .level import Level


# ----------------------------------------------------------------------
# Base sprite / hitbox helpers
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Hitbox:
    """Rectangular AABB in world space."""
    x: float
    y: float
    w: int
    h: int

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def intersects(self, other: Self | Hitbox) -> bool:
        return self.rect.colliderect(other.rect)


# ----------------------------------------------------------------------
# Player
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Player:
    x: float
    y: float = GROUND_Y - 24
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = True
    facing: Facing = Facing.RIGHT
    state: PlayerState = PlayerState.IDLE
    state_timer: int = 0
    iframes: int = 0
    hp: int = PLAYER_MAX_HP
    lives: int = 3
    batarangs: int = 5
    score: int = 0
    walk_anim: float = 0.0
    next_extra_life: int = 20_000
    combo: int = 0
    combo_timer: int = 0
    last_throw_flash: int = 0  # frames remaining of HUD batarang flash
    charge_frames: int = 0     # how long C is held (for charged shot)

    W: int = 12
    H: int = 24

    @property
    def hitbox(self) -> Hitbox:
        return Hitbox(self.x - self.W / 2, self.y, self.W, self.H)

    @property
    def attack_hitbox(self) -> Hitbox | None:
        if self.state is PlayerState.PUNCH:
            ax = self.x + self.facing * 6
            return Hitbox(ax - 6, self.y + 4, 14, 12)
        if self.state is PlayerState.KICK:
            ax = self.x + self.facing * 8
            return Hitbox(ax - 6, self.y + 12, 18, 10)
        if self.state is PlayerState.SLIDE:
            ax = self.x + self.facing * 6
            return Hitbox(ax - 8, self.y + 14, 22, 10)
        if self.state is PlayerState.DIVEKICK:
            return Hitbox(self.x - 6, self.y + 14, 12, 10)
        return None

    @property
    def attack_damage(self) -> int:
        match self.state:
            case PlayerState.PUNCH:
                base = PUNCH_DAMAGE
            case PlayerState.KICK:
                base = KICK_DAMAGE
            case PlayerState.SLIDE:
                base = SLIDE_DAMAGE
            case PlayerState.DIVEKICK:
                base = DIVEKICK_DAMAGE
            case _:
                return 0
        return int(base * (1 + self.combo * COMBO_DAMAGE_BONUS))

    def register_combo_hit(self) -> None:
        self.combo += 1
        self.combo_timer = COMBO_WINDOW

    def combo_score_bonus(self, base: int) -> int:
        return int(base * (1 + self.combo * COMBO_SCORE_BONUS))

    # ------------------------------------------------------------------
    def update(self, keys: pygame.key.ScancodeWrapper, level: Level) -> None:
        if self.state is PlayerState.DEAD:
            self.vy += GRAVITY
            self.y += self.vy
            # Clamp to ground so the body doesn't fall through the floor while
            # the death animation plays out.
            if self.y >= GROUND_Y - self.H:
                self.y = GROUND_Y - self.H
                self.vy = 0
            if self.state_timer > 0:
                self.state_timer -= 1
            return

        # Combo timer decay
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo = 0

        attacking = self.state in {PlayerState.PUNCH, PlayerState.KICK, PlayerState.THROW}
        sliding = self.state is PlayerState.SLIDE
        dive = self.state is PlayerState.DIVEKICK

        # Horizontal input (no input during ground attacks; slide moves on its own)
        ax = 0.0
        if sliding:
            self.vx = SLIDE_SPEED * self.facing
        elif dive:
            self.vx = 0  # straight down
        elif attacking and self.on_ground:
            # Committed ground attacks: no momentum carryover.
            self.vx = 0
        else:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                ax -= 1
                self.facing = Facing.LEFT
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                ax += 1
                self.facing = Facing.RIGHT
            speed = RUN_SPEED if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else WALK_SPEED
            self.vx = ax * speed

        # Gravity (extra during dive-kick for snappy fall)
        self.vy += GRAVITY * (3.0 if dive else 1.0)
        prev_foot = self.y + self.H
        self.y += self.vy
        self.x += self.vx
        foot = self.y + self.H

        # Platform collision (one-way from above)
        landed_y: float | None = None
        plat_top = level.platform_top_below(self.x, foot, prev_foot)
        if plat_top is not None and self.vy >= 0:
            landed_y = plat_top - self.H

        # Ground collision
        if self.y >= GROUND_Y - self.H:
            landed_y = GROUND_Y - self.H

        if landed_y is not None:
            self.y = landed_y
            self.vy = 0
            if not self.on_ground and self.state is PlayerState.JUMP:
                self.state = PlayerState.IDLE
            # Defer DIVEKICK→IDLE for one frame (handled by state_timer below)
            # so attack_hitbox stays valid on the landing-impact frame.
            self.on_ground = True
        else:
            self.on_ground = False

        # World bounds
        self.x = max(8, min(self.x, level.width_px - 8))

        # State machine timing — DIVEKICK exits when on_ground (after the
        # post-landing attack-hitbox frame has been processed by the world).
        if self.state is PlayerState.DIVEKICK and self.on_ground and self.state_timer == 0:
            self.state_timer = 1  # one extra frame so attack_hitbox lands
        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer == 0 and self.state in {
                PlayerState.PUNCH, PlayerState.KICK, PlayerState.THROW, PlayerState.HURT,
                PlayerState.SLIDE, PlayerState.DIVEKICK,
            }:
                self.state = PlayerState.IDLE
        if self.iframes > 0:
            self.iframes -= 1
        if self.last_throw_flash > 0:
            self.last_throw_flash -= 1

        # Determine animation state if not locked
        if self.state in {PlayerState.IDLE, PlayerState.WALK, PlayerState.JUMP}:
            if not self.on_ground:
                self.state = PlayerState.JUMP
            elif abs(self.vx) > 0.1:
                self.state = PlayerState.WALK
                self.walk_anim += abs(self.vx) * 0.15
            else:
                self.state = PlayerState.IDLE

    # ------------------------------------------------------------------
    def try_jump(self) -> None:
        if self.on_ground and self.state not in {PlayerState.HURT, PlayerState.DEAD}:
            self.vy = JUMP_SPEED
            self.on_ground = False
            self.state = PlayerState.JUMP
            audio.jump().play()

    def try_punch(self) -> None:
        if self.state in {PlayerState.IDLE, PlayerState.WALK} and self.on_ground:
            self.state = PlayerState.PUNCH
            self.state_timer = PUNCH_FRAMES
            audio.punch().play()

    def try_kick(self) -> None:
        if self.state in {PlayerState.IDLE, PlayerState.WALK} and self.on_ground:
            self.state = PlayerState.KICK
            self.state_timer = KICK_FRAMES
            audio.kick().play()
        elif not self.on_ground and self.state not in {
            PlayerState.HURT, PlayerState.DEAD, PlayerState.DIVEKICK,
        }:
            # Air kick → dive-kick
            self.state = PlayerState.DIVEKICK
            self.state_timer = 60
            self.vy = max(self.vy, 2.0)
            audio.kick().play()

    def try_slide(self) -> None:
        if self.on_ground and self.state in {PlayerState.IDLE, PlayerState.WALK}:
            self.state = PlayerState.SLIDE
            self.state_timer = SLIDE_FRAMES
            self.iframes = max(self.iframes, 8)  # brief invuln through projectiles
            audio.kick().play()

    def try_throw(self) -> Batarang | None:
        if self.batarangs <= 0:
            return None
        if self.state not in {PlayerState.IDLE, PlayerState.WALK, PlayerState.JUMP}:
            return None
        self.batarangs -= 1
        self.state = PlayerState.THROW
        self.state_timer = 14
        self.last_throw_flash = 12  # HUD flash so player sees they fired
        audio.batarang().play()
        return Batarang(
            x=self.x + self.facing * 10,
            y=self.y + 8,
            vx=3.2 * self.facing,  # slower than 4.5 so it's actually visible
        )

    def take_damage(self, dmg: int) -> None:
        if self.iframes > 0 or self.state is PlayerState.DEAD:
            return
        self.hp -= dmg
        self.iframes = IFRAMES
        if self.hp <= 0:
            self.lives -= 1
            if self.lives <= 0:
                self.state = PlayerState.DEAD
                self.state_timer = 120
                self.vy = -6
                audio.death().play()
            else:
                self.hp = PLAYER_MAX_HP
                self.state = PlayerState.HURT
                self.state_timer = HITSTUN_FRAMES
                self.vy = -3
                audio.hurt().play()
        else:
            self.state = PlayerState.HURT
            self.state_timer = HITSTUN_FRAMES
            self.vy = -2.5
            audio.hurt().play()

    def add_score(self, pts: int) -> None:
        self.score += pts
        if self.score >= self.next_extra_life:
            self.lives += 1
            self.next_extra_life += 20_000
            audio.pickup().play()

    # ------------------------------------------------------------------
    def draw(self, surf: pygame.Surface, level: Level) -> None:
        sprite_name = self._sprite_name()
        getter = sprites.get_flipped if self.facing is Facing.LEFT else sprites.get
        img = getter(sprite_name)
        # Flicker on i-frames
        if self.iframes and self.iframes % 4 < 2:
            return
        sx = level.world_to_screen(self.x) - img.get_width() // 2
        sy = int(self.y) - 0
        surf.blit(img, (sx, sy))

    def _sprite_name(self) -> str:
        match self.state:
            case PlayerState.IDLE:
                return "batman_idle"
            case PlayerState.WALK:
                return "batman_walk_a" if int(self.walk_anim) % 2 == 0 else "batman_walk_b"
            case PlayerState.JUMP:
                return "batman_jump"
            case PlayerState.PUNCH:
                return "batman_punch"
            case PlayerState.KICK:
                return "batman_kick"
            case PlayerState.THROW:
                return "batman_throw"
            case PlayerState.HURT | PlayerState.DEAD:
                return "batman_hurt"
            case PlayerState.SLIDE:
                return "batman_slide"
            case PlayerState.DIVEKICK:
                return "batman_divekick"


# ----------------------------------------------------------------------
# Projectiles
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Batarang:
    x: float
    y: float
    vx: float
    spin: float = 0.0
    alive: bool = True
    damage: int = BATARANG_DAMAGE
    life: int = 90  # frames
    trail: list[tuple[float, float]] = field(default_factory=list)

    def update(self, level: Level) -> None:
        # Record trail position before updating
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
        self.x += self.vx
        self.spin += 0.5
        self.life -= 1
        if self.life <= 0 or self.x < level.cam_x - 32 or self.x > level.cam_x + 360:
            self.alive = False

    def draw(self, surf: pygame.Surface, level: Level) -> None:
        # Yellow afterimage trail for visibility
        for i, (tx, ty) in enumerate(self.trail):
            sx = level.world_to_screen(tx)
            radius = i + 1
            pygame.draw.circle(surf, PALETTE["yellow"], (sx, int(ty)), radius)
        img = sprites.get("batarang")
        rotated = pygame.transform.rotate(img, self.spin * 30 % 360)
        rect = rotated.get_rect(center=(level.world_to_screen(self.x), int(self.y)))
        surf.blit(rotated, rect)

    @property
    def hitbox(self) -> Hitbox:
        return Hitbox(self.x - 7, self.y - 7, 14, 14)


@dataclass(slots=True)
class EnemyProjectile:
    x: float
    y: float
    vx: float
    vy: float
    sprite: str
    damage: int = 15
    alive: bool = True
    life: int = 120

    def update(self, level: Level) -> None:
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0 or self.x < level.cam_x - 32 or self.x > level.cam_x + 360:
            self.alive = False

    def draw(self, surf: pygame.Surface, level: Level) -> None:
        img = sprites.get(self.sprite)
        if self.vx < 0:
            img = pygame.transform.flip(img, True, False)
        surf.blit(img, (level.world_to_screen(self.x), int(self.y)))

    @property
    def hitbox(self) -> Hitbox:
        return Hitbox(self.x, self.y, 8, 8)


# ----------------------------------------------------------------------
# Enemies
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Enemy:
    kind: EnemyKind
    x: float
    y: float
    hp: int = 50
    max_hp: int = 50
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = True
    facing: Facing = Facing.LEFT
    state_timer: int = 0
    attack_cooldown: int = 0
    score_value: int = SCORE_ENEMY
    alive: bool = True
    iframes: int = 0
    walk_anim: float = 0.0
    activated: bool = True   # jack-in-the-box starts inactive
    contact_damage: int = 12
    W: int = 14
    H: int = 24
    boss: bool = False
    phase: int = 1
    phase_timer: int = 0
    arena_left: float = 0.0
    arena_right: float = 0.0
    dived_this_cycle: bool = False

    @classmethod
    def spawn(cls, kind: EnemyKind, x: float, y: float) -> Enemy:
        match kind:
            case EnemyKind.BASHER:
                return cls(kind, x, y, hp=40, max_hp=40, contact_damage=10)
            case EnemyKind.JACKBOX:
                return cls(
                    kind, x, GROUND_Y - 24, hp=20, max_hp=20,
                    activated=False, contact_damage=18, score_value=200,
                )
            case EnemyKind.FIREBREATHER:
                return cls(kind, x, y, hp=60, max_hp=60, contact_damage=14)
            case EnemyKind.KNIFER:
                return cls(kind, x, y, hp=35, max_hp=35, contact_damage=8)
            case EnemyKind.MIDBOSS_JOKER:
                return cls(
                    kind, x, GROUND_Y - 28, hp=180, max_hp=180,
                    W=20, H=28, contact_damage=15,
                    score_value=SCORE_MIDBOSS, boss=True,
                )
            case EnemyKind.MIDBOSS_CATWOMAN:
                return cls(
                    kind, x, GROUND_Y - 28, hp=200, max_hp=200,
                    W=16, H=28, contact_damage=14,
                    score_value=SCORE_MIDBOSS, boss=True,
                )
            case EnemyKind.BOSS_PENGUIN:
                return cls(
                    kind, x, GROUND_Y - 32, hp=400, max_hp=400, W=24, H=32,
                    contact_damage=20, score_value=SCORE_BOSS, boss=True,
                )
        raise ValueError(kind)

    @property
    def hitbox(self) -> Hitbox:
        return Hitbox(self.x - self.W / 2, self.y, self.W, self.H)

    # ------------------------------------------------------------------
    def update(self, player: Player, level: Level) -> list[EnemyProjectile]:
        if self.iframes:
            self.iframes -= 1
        if self.state_timer > 0:
            self.state_timer -= 1
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        match self.kind:
            case EnemyKind.BASHER:
                proj = self._update_basher(player)
            case EnemyKind.JACKBOX:
                proj = self._update_jack(player)
            case EnemyKind.FIREBREATHER:
                proj = self._update_fire(player)
            case EnemyKind.KNIFER:
                proj = self._update_knifer(player)
            case EnemyKind.MIDBOSS_JOKER:
                return self._update_joker_multi(player, level)
            case EnemyKind.MIDBOSS_CATWOMAN:
                proj = self._update_catwoman(player, level)
            case EnemyKind.BOSS_PENGUIN:
                return self._update_boss_multi(player, level)
            case _:
                proj = None
        return [proj] if proj is not None else []

    def _walk_toward(self, player: Player, speed: float = 1.1) -> None:
        if player.x < self.x:
            self.vx = -speed
            self.facing = Facing.LEFT
        else:
            self.vx = speed
            self.facing = Facing.RIGHT
        self.x += self.vx
        self.walk_anim += abs(self.vx) * 0.15

    def _update_basher(self, player: Player) -> None:
        dx = player.x - self.x
        if abs(dx) > 16:
            self._walk_toward(player, 1.0)
        else:
            self.vx = 0
            if self.attack_cooldown <= 0 and abs(player.y - self.y) < 24:
                self.attack_cooldown = 60
                # Contact damage handled by overlap; just freeze briefly
                self.state_timer = 12
        return None

    def _update_jack(self, player: Player) -> EnemyProjectile | None:
        # Triggers when player walks within 24 pixels horizontally
        if not self.activated:
            if abs(player.x - self.x) < 24:
                self.activated = True
                self.state_timer = 30
                audio.boss_roar().play()
            return None
        # Once activated, idle hostile
        if self.attack_cooldown <= 0 and abs(player.x - self.x) < 80:
            self.attack_cooldown = 110
            return EnemyProjectile(
                x=self.x, y=self.y - 4,
                vx=2.4 * (1 if player.x > self.x else -1),
                vy=-1.5,
                sprite="knife_proj", damage=12,
            )
        return None

    def _update_fire(self, player: Player) -> EnemyProjectile | None:
        dx = player.x - self.x
        if abs(dx) > 60:
            self._walk_toward(player, 0.6)
        else:
            self.vx = 0
            self.facing = Facing.LEFT if dx < 0 else Facing.RIGHT
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 80
                audio.fire().play()
                return EnemyProjectile(
                    x=self.x + self.facing * 10, y=self.y + 8,
                    vx=2.0 * self.facing, vy=0,
                    sprite="fire_proj", damage=15, life=60,
                )
        return None

    def _update_knifer(self, player: Player) -> EnemyProjectile | None:
        dx = player.x - self.x
        # Keep distance
        target = 90
        if abs(dx) < target - 10:
            self.vx = -1.2 if dx > 0 else 1.2
            self.x += self.vx
            self.facing = Facing.LEFT if dx < 0 else Facing.RIGHT
        elif abs(dx) > target + 10:
            self._walk_toward(player, 0.9)
        else:
            self.vx = 0
            self.facing = Facing.LEFT if dx < 0 else Facing.RIGHT
            if self.attack_cooldown <= 0:
                self.attack_cooldown = 90
                return EnemyProjectile(
                    x=self.x, y=self.y + 6,
                    vx=3.2 * self.facing, vy=-0.5,
                    sprite="knife_proj", damage=12, life=120,
                )
        return None

    def _update_joker(self, player: Player, level: Level) -> EnemyProjectile | None:
        # Cackles, hops between two firing positions, throws fan of cards
        self.walk_anim += 0.06
        # Hop pattern
        if self.on_ground and self.attack_cooldown > 30 and self.state_timer == 0:
            # initiate small hop sometimes
            if int(self.attack_cooldown) % 35 == 0:
                self.vy = -4.5
                self.on_ground = False
        # Gravity for boss
        if not self.on_ground:
            self.vy += 0.45
            self.y += self.vy
            if self.y >= GROUND_Y - self.H:
                self.y = GROUND_Y - self.H
                self.vy = 0
                self.on_ground = True
        self.facing = Facing.LEFT if player.x < self.x else Facing.RIGHT
        # Stay near arena center (fixed at spawn time, not the live camera)
        if self.arena_right == 0:
            self.arena_left = self.x - 80
            self.arena_right = self.x + 80
        center = (self.arena_left + self.arena_right) / 2
        self.x += (center - self.x) * 0.005
        self.x = max(self.arena_left, min(self.x, self.arena_right))
        if self.attack_cooldown <= 0:
            self.attack_cooldown = 75
            # Triple-card spread
            return EnemyProjectile(
                x=self.x, y=self.y + 8,
                vx=2.4 * self.facing, vy=-1.8,
                sprite="knife_proj", damage=12, life=120,
            )
        return None

    def _update_catwoman(self, player: Player, level: Level) -> EnemyProjectile | None:
        # Acrobatic: lunges horizontally, claws on contact, occasionally jumps over
        dx = player.x - self.x
        self.facing = Facing.LEFT if dx < 0 else Facing.RIGHT
        # Lunge state pattern
        if self.state_timer == 0 and self.attack_cooldown <= 0:
            # Decide: jump-over or lunge
            if abs(dx) < 40 and self.on_ground:
                self.vy = -7.5
                self.vx = 3.0 * (1 if dx > 0 else -1)
                self.on_ground = False
                self.attack_cooldown = 90
                self.state_timer = 30
            elif abs(dx) < 90 and self.on_ground:
                self.vx = 2.6 * (1 if dx > 0 else -1)
                self.attack_cooldown = 60
                self.state_timer = 18
        # Apply velocity & gravity
        if not self.on_ground:
            self.vy += 0.45
            self.y += self.vy
        self.x += self.vx
        if self.state_timer == 0 and self.on_ground:
            self.vx *= 0.6
        if self.y >= GROUND_Y - self.H:
            self.y = GROUND_Y - self.H
            self.vy = 0
            self.on_ground = True
        # Stay in arena (fixed at spawn time)
        if self.arena_right == 0:
            self.arena_left = self.x - 100
            self.arena_right = self.x + 100
        self.x = max(self.arena_left, min(self.x, self.arena_right))
        return None

    def _update_boss(self, player: Player, level: Level) -> EnemyProjectile | None:
        """Penguin: 3 phases.
        - Phase 1 (>66% HP): paces, lobs single umbrellas (slow arc).
        - Phase 2 (33-66%):  faster pacing, double-shot umbrellas + dive.
        - Phase 3 (<33%):    angry — triple spread + faster cadence.
        """
        # Phase transitions
        ratio = self.hp / self.max_hp
        new_phase = 3 if ratio < 0.33 else 2 if ratio < 0.66 else 1
        if new_phase != self.phase:
            self.phase = new_phase
            self.phase_timer = 30
            audio.boss_roar().play()
            self.attack_cooldown = 30  # brief recovery
        if self.phase_timer > 0:
            self.phase_timer -= 1

        speed_scale = {1: 1.0, 2: 1.5, 3: 2.0}[self.phase]
        self.walk_anim += 0.05 * speed_scale
        self.vx = math.sin(self.walk_anim) * 1.2 * speed_scale
        self.x += self.vx
        self.facing = Facing.LEFT if player.x < self.x else Facing.RIGHT
        # Pin Penguin to a fixed arena recorded at spawn (NOT the live camera)
        if self.arena_right == 0:
            self.arena_left = self.x - 100
            self.arena_right = self.x + 100
        self.x = max(self.arena_left, min(self.x, self.arena_right))

        # Occasional dive in phase 2/3 (jumps into the air for shadow scare).
        # Trigger once mid-cycle; reset flag when cooldown completes.
        if self.attack_cooldown <= 0:
            self.dived_this_cycle = False
        if (
            self.phase >= 2
            and self.on_ground
            and not self.dived_this_cycle
            and self.attack_cooldown <= 14
            and self.attack_cooldown > 0
        ):
            self.vy = -5.5
            self.on_ground = False
            self.dived_this_cycle = True
        if not self.on_ground:
            self.vy += 0.4
            self.y += self.vy
            if self.y >= GROUND_Y - self.H:
                self.y = GROUND_Y - self.H
                self.vy = 0
                self.on_ground = True

        if self.attack_cooldown <= 0:
            cadence = {1: 60, 2: 42, 3: 28}[self.phase]
            self.attack_cooldown = cadence
            sign = 1 if player.x > self.x else -1
            base = EnemyProjectile(
                x=self.x, y=self.y + 6,
                vx=2.6 * sign, vy=-2.0,
                sprite="knife_proj", damage=14, life=140,
            )
            return base
        return None

    def _update_boss_multi(self, player: Player, level: Level) -> list[EnemyProjectile]:
        base = self._update_boss(player, level)
        if base is None:
            return []
        out = [base]
        # Phase 2: add a second shot with different arc
        if self.phase >= 2:
            out.append(EnemyProjectile(
                x=base.x, y=base.y,
                vx=base.vx * 1.2, vy=base.vy + 1.0,
                sprite="knife_proj", damage=14, life=140,
            ))
        # Phase 3: triple spread
        if self.phase >= 3:
            out.append(EnemyProjectile(
                x=base.x, y=base.y,
                vx=base.vx * 0.6, vy=base.vy - 1.5,
                sprite="knife_proj", damage=14, life=140,
            ))
        return out

    def _update_joker_multi(self, player: Player, level: Level) -> list[EnemyProjectile]:
        base = self._update_joker(player, level)
        if base is None:
            return []
        # Joker always throws a fan of three cards
        return [
            base,
            EnemyProjectile(
                x=base.x, y=base.y, vx=base.vx, vy=base.vy + 1.5,
                sprite="knife_proj", damage=12, life=120,
            ),
            EnemyProjectile(
                x=base.x, y=base.y, vx=base.vx, vy=base.vy - 1.0,
                sprite="knife_proj", damage=12, life=120,
            ),
        ]

    # ------------------------------------------------------------------
    def take_damage(self, dmg: int, knockback: float = 0) -> bool:
        """Returns True if killed."""
        if self.iframes > 0 or not self.alive:
            return False
        self.hp -= dmg
        self.iframes = 8
        self.x += knockback
        audio.hit().play()
        if self.hp <= 0:
            self.alive = False
            return True
        return False

    # ------------------------------------------------------------------
    def draw(self, surf: pygame.Surface, level: Level) -> None:
        if not self.alive:
            return
        sprite_name = self._sprite_name()
        if sprite_name is None:
            return
        # Sprites are drawn facing right by convention (matches Player.draw).
        getter = sprites.get_flipped if self.facing is Facing.LEFT else sprites.get
        img = getter(sprite_name)
        if self.iframes and self.iframes % 2 == 0:
            tinted = img.copy()
            tinted.fill((255, 80, 80, 0), special_flags=pygame.BLEND_RGBA_ADD)
            img = tinted
        sx = level.world_to_screen(self.x) - img.get_width() // 2
        sy = int(self.y)
        surf.blit(img, (sx, sy))
        # Boss healthbar
        if self.boss:
            self._draw_boss_hp(surf)

    def _sprite_name(self) -> str | None:
        match self.kind:
            case EnemyKind.BASHER:
                return "clown_a" if int(self.walk_anim) % 2 == 0 else "clown_b"
            case EnemyKind.JACKBOX:
                return "jack_open" if self.activated else "jack_closed"
            case EnemyKind.FIREBREATHER:
                return "firebreather"
            case EnemyKind.KNIFER:
                return "knifer"
            case EnemyKind.MIDBOSS_JOKER:
                return "joker"
            case EnemyKind.MIDBOSS_CATWOMAN:
                return "catwoman"
            case EnemyKind.BOSS_PENGUIN:
                return "penguin"

    def _draw_boss_hp(self, surf: pygame.Surface) -> None:
        from .constants import NATIVE_W
        bar_w = 240
        bar_x = (NATIVE_W - bar_w) // 2
        bar_y = 8
        pygame.draw.rect(surf, PALETTE["dark"], (bar_x - 2, bar_y - 2, bar_w + 4, 8))
        ratio = max(0.0, self.hp / self.max_hp)
        pygame.draw.rect(surf, PALETTE["red"], (bar_x, bar_y, int(bar_w * ratio), 4))
        pygame.draw.rect(surf, PALETTE["white"], (bar_x, bar_y, bar_w, 4), 1)
        # Phase markers at 33%/66%
        for marker in (0.33, 0.66):
            mx = bar_x + int(bar_w * marker)
            pygame.draw.line(surf, PALETTE["yellow"], (mx, bar_y), (mx, bar_y + 4))


# ----------------------------------------------------------------------
# Pickups
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Pickup:
    kind: str  # "batarang" | "health" | "1up"
    x: float
    y: float
    bob: float = 0.0
    alive: bool = True

    @property
    def hitbox(self) -> Hitbox:
        return Hitbox(self.x - 6, self.y - 6, 12, 12)

    def update(self) -> None:
        self.bob += 0.1

    def apply(self, player: Player) -> None:
        match self.kind:
            case "batarang":
                player.batarangs += 3
            case "health":
                player.hp = min(PLAYER_MAX_HP, player.hp + 40)
            case "1up":
                player.lives += 1
        audio.pickup().play()
        self.alive = False

    def draw(self, surf: pygame.Surface, level: Level) -> None:
        if not self.alive:
            return
        sx = level.world_to_screen(self.x)
        sy = int(self.y + math.sin(self.bob) * 2)
        match self.kind:
            case "batarang":
                surf.blit(sprites.get("batarang"), (sx - 5, sy - 4))
            case "health":
                pygame.draw.rect(surf, PALETTE["red"], (sx - 5, sy - 5, 10, 10))
                pygame.draw.rect(surf, PALETTE["white"], (sx - 1, sy - 4, 2, 8))
                pygame.draw.rect(surf, PALETTE["white"], (sx - 4, sy - 1, 8, 2))
            case "1up":
                pygame.draw.rect(surf, PALETTE["green"], (sx - 6, sy - 5, 12, 10))


def random_pickup(x: float, rng: random.Random | None = None) -> Pickup:
    rng = rng or random
    roll = rng.random()
    if roll < 0.55:
        return Pickup("health", x, GROUND_Y - 8)
    if roll < 0.9:
        return Pickup("batarang", x, GROUND_Y - 8)
    return Pickup("1up", x, GROUND_Y - 8)
