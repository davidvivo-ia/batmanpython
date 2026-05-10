"""Main game loop and state machine."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame

from . import audio, sprites
from .constants import (
    EXTRA_LIFE_AT,
    FPS,
    GROUND_Y,
    NATIVE_H,
    NATIVE_W,
    PALETTE,
    PLAYER_MAX_HP,
    SCORE_BOSS,
    SCORE_ENEMY,
    SCORE_MIDBOSS,
    SCORE_SMALL,
    STARTING_BATARANGS,
    STARTING_LIVES,
    TILE_SIZE,
    WINDOW_H,
    WINDOW_W,
    EnemyKind,
    Facing,
    GameState,
    PlayerState,
)
from .effects import FloatingTextSystem, HitFreeze, ParticleSystem, ScreenShake
from .entities import (
    Batarang,
    Enemy,
    EnemyProjectile,
    Pickup,
    Player,
    random_pickup,
)
from .hud import draw_hud, draw_text
from .level import STAGES, Level


@dataclass(slots=True)
class World:
    level: Level
    player: Player
    enemies: list[Enemy] = field(default_factory=list)
    batarangs: list[Batarang] = field(default_factory=list)
    enemy_shots: list[EnemyProjectile] = field(default_factory=list)
    pickups: list[Pickup] = field(default_factory=list)
    spawn_index: int = 0          # how many tile-columns have been spawned
    boss_spawned: bool = False
    boss_defeated: bool = False
    rng: random.Random = field(default_factory=lambda: random.Random(1337))
    particles: ParticleSystem = field(default_factory=ParticleSystem)
    shake: ScreenShake = field(default_factory=ScreenShake)
    freeze: HitFreeze = field(default_factory=HitFreeze)
    floats: FloatingTextSystem = field(default_factory=FloatingTextSystem)


def _spawn_for_stage(world: World) -> None:
    """Stream enemies as the camera advances. Mirrors original 'wave by map' design."""
    stage = world.level.stage
    cam_tile = int(world.level.cam_x // TILE_SIZE)
    edge_tile = cam_tile + NATIVE_W // TILE_SIZE + 4
    while world.spawn_index < edge_tile and world.spawn_index < stage.length_tiles:
        tx = world.spawn_index
        world.spawn_index += 1
        if tx < 8:
            continue  # safe zone at start
        if tx > stage.length_tiles - 16 and stage.boss:
            break  # save boss arena
        if world.rng.random() < stage.enemy_density:
            kind = world.rng.choices(
                population=[
                    EnemyKind.BASHER,
                    EnemyKind.JACKBOX,
                    EnemyKind.FIREBREATHER,
                    EnemyKind.KNIFER,
                ],
                weights=[5, 2, 2, 3],
            )[0]
            wx = tx * TILE_SIZE + 8
            world.enemies.append(Enemy.spawn(kind, wx, GROUND_Y - 24))
        # Pickup chance
        if world.rng.random() < 0.04:
            wx = tx * TILE_SIZE + 8
            world.pickups.append(random_pickup(wx, world.rng))

    # Boss spawn at end of last stage
    if stage.boss and not world.boss_spawned and world.player.x > (stage.length_tiles - 18) * TILE_SIZE:
        boss_x = world.player.x + 120
        world.enemies.append(Enemy.spawn(EnemyKind.BOSS_PENGUIN, boss_x, GROUND_Y - 32))
        world.boss_spawned = True
        audio.boss_roar().play()


def _award(world: World, points: int, x: float, y: float) -> None:
    world.player.add_score(points)
    world.floats.emit(f"+{points}", x, y - 8)


def _update_world(world: World, keys: pygame.key.ScancodeWrapper) -> None:
    if world.freeze.tick():
        return
    p = world.player
    was_on_ground = p.on_ground
    p.update(keys, world.level)
    # Landing dust
    if not was_on_ground and p.on_ground:
        world.particles.dust(p.x, p.y + p.H)

    # Camera follows player
    target_cam = p.x - NATIVE_W // 2
    world.level.update(target_cam, 1 / FPS)

    _spawn_for_stage(world)

    # Update enemies
    for e in world.enemies:
        if not e.alive:
            continue
        proj = e.update(p, world.level)
        if proj is not None:
            world.enemy_shots.append(proj)

    # Update projectiles
    for b in world.batarangs:
        b.update(world.level)
    for s in world.enemy_shots:
        s.update(world.level)
    for pk in world.pickups:
        pk.update()

    # ---- Combat resolution ----
    atk = p.attack_hitbox
    if atk is not None:
        dmg = p.attack_damage
        any_hit = False
        for e in world.enemies:
            if e.alive and atk.intersects(e.hitbox):
                any_hit = True
                kb = 4.0 * p.facing
                cx, cy = e.x, e.y + e.H / 2
                world.particles.burst_hit(cx, cy)
                world.shake.kick(2.5)
                killed = e.take_damage(dmg, knockback=kb)
                if killed:
                    pts = p.combo_score_bonus(e.score_value)
                    _award(world, pts, e.x, e.y)
                    world.particles.burst_blood(cx, cy, dir_sign=p.facing)
                    world.shake.kick(5.0)
                    world.freeze.kick(3 if not e.boss else 8)
                    if e.boss:
                        world.boss_defeated = True
        if any_hit:
            p.register_combo_hit()
            if p.combo >= 3:
                world.floats.emit(f"{p.combo}X COMBO!", p.x, p.y - 20, PALETTE["yellow"])

    # Batarang vs enemies
    for b in world.batarangs:
        if not b.alive:
            continue
        for e in world.enemies:
            if e.alive and b.hitbox.intersects(e.hitbox):
                cx, cy = e.x, e.y + e.H / 2
                world.particles.spark(cx, cy, PALETTE["white"])
                killed = e.take_damage(b.damage, knockback=2.0 * (1 if b.vx > 0 else -1))
                if killed:
                    _award(world, e.score_value, e.x, e.y)
                    world.particles.burst_blood(cx, cy, dir_sign=1 if b.vx > 0 else -1)
                    world.shake.kick(4.0)
                    world.freeze.kick(3 if not e.boss else 8)
                    if e.boss:
                        world.boss_defeated = True
                b.alive = False
                break

    # Enemies vs player (contact + projectiles)
    for e in world.enemies:
        if e.alive and e.hitbox.intersects(p.hitbox) and p.iframes <= 0:
            p.take_damage(e.contact_damage)
            world.particles.burst_blood(p.x, p.y + 8, dir_sign=-p.facing)
            world.shake.kick(4.0)
    for s in world.enemy_shots:
        if s.alive and s.hitbox.intersects(p.hitbox):
            world.particles.spark(p.x, p.y + 10, PALETTE["red"])
            if p.iframes <= 0:
                world.shake.kick(3.0)
            p.take_damage(s.damage)
            s.alive = False

    # Pickups
    for pk in world.pickups:
        if pk.alive and pk.hitbox.intersects(p.hitbox):
            world.particles.emit(pk.x, pk.y, count=10, color=PALETTE["green"], speed=2.0, life=18)
            label = {"health": "HEALTH", "batarang": "+3 BAT", "1up": "1UP"}[pk.kind]
            world.floats.emit(label, pk.x, pk.y, PALETTE["green"])
            pk.apply(p)

    # FX update
    world.particles.update()
    world.floats.update()

    # Cleanup
    world.enemies = [e for e in world.enemies if e.alive]
    world.batarangs = [b for b in world.batarangs if b.alive]
    world.enemy_shots = [s for s in world.enemy_shots if s.alive]
    world.pickups = [pk for pk in world.pickups if pk.alive]


def _draw_world(surf: pygame.Surface, world: World) -> None:
    world.level.draw(surf)
    for pk in world.pickups:
        pk.draw(surf, world.level)
    for e in world.enemies:
        e.draw(surf, world.level)
    for s in world.enemy_shots:
        s.draw(surf, world.level)
    for b in world.batarangs:
        b.draw(surf, world.level)
    world.player.draw(surf, world.level)
    world.particles.draw(surf, world.level.cam_x)
    world.floats.draw(surf, world.level.cam_x)
    draw_hud(surf, world.player, world.level.stage.name)


# ----------------------------------------------------------------------
# Title / overlay screens
# ----------------------------------------------------------------------


def _draw_title(surf: pygame.Surface, blink: int) -> None:
    surf.fill(PALETTE["black"])
    # Bat-signal: yellow ellipse with bat shape
    cx, cy = NATIVE_W // 2, NATIVE_H // 2 - 30
    pygame.draw.ellipse(surf, PALETTE["yellow"], (cx - 70, cy - 35, 140, 70))
    pygame.draw.ellipse(surf, PALETTE["dark"], (cx - 60, cy - 28, 120, 56))
    # Stylised bat
    bat_pts = [
        (cx - 50, cy), (cx - 30, cy - 4), (cx - 18, cy - 12), (cx - 10, cy + 4),
        (cx, cy - 8), (cx + 10, cy + 4), (cx + 18, cy - 12), (cx + 30, cy - 4),
        (cx + 50, cy), (cx + 30, cy + 6), (cx + 12, cy + 10), (cx, cy + 6),
        (cx - 12, cy + 10), (cx - 30, cy + 6),
    ]
    pygame.draw.polygon(surf, PALETTE["black"], bat_pts)
    draw_text(surf, "BATMAN RETURNS", NATIVE_W // 2 - 78, NATIVE_H // 2 + 24, PALETTE["yellow"], scale=2)
    draw_text(surf, "PYTHON HOMAGE - 1992 / 2026", NATIVE_W // 2 - 80, NATIVE_H // 2 + 50, PALETTE["lightgray"])
    if blink % 60 < 40:
        draw_text(surf, "PRESS ENTER TO START", NATIVE_W // 2 - 60, NATIVE_H - 40, PALETTE["white"])
    draw_text(surf, "ARROWS:MOVE  Z:PUNCH  X:KICK  C:BATARANG  SPACE:JUMP", 8, NATIVE_H - 16, PALETTE["gray"])


def _draw_game_over(surf: pygame.Surface, world: World, blink: int) -> None:
    overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surf.blit(overlay, (0, 0))
    draw_text(surf, "GAME OVER", NATIVE_W // 2 - 50, NATIVE_H // 2 - 20, PALETTE["red"], scale=2)
    draw_text(surf, f"FINAL SCORE {world.player.score:06d}", NATIVE_W // 2 - 70, NATIVE_H // 2 + 8, PALETTE["white"])
    if blink % 60 < 40:
        draw_text(surf, "ENTER TO RETRY  ESC TO QUIT", NATIVE_W // 2 - 80, NATIVE_H // 2 + 30, PALETTE["yellow"])


def _draw_victory(surf: pygame.Surface, world: World, blink: int) -> None:
    overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 40, 160))
    surf.blit(overlay, (0, 0))
    draw_text(surf, "GOTHAM IS SAFE", NATIVE_W // 2 - 75, NATIVE_H // 2 - 30, PALETTE["yellow"], scale=2)
    draw_text(surf, f"FINAL SCORE {world.player.score:06d}", NATIVE_W // 2 - 70, NATIVE_H // 2 + 4, PALETTE["white"])
    if blink % 60 < 40:
        draw_text(surf, "ENTER TO PLAY AGAIN", NATIVE_W // 2 - 60, NATIVE_H // 2 + 30, PALETTE["yellow"])


def _draw_intro(surf: pygame.Surface, level: Level, blink: int) -> None:
    surf.fill(PALETTE["black"])
    draw_text(surf, "STAGE", NATIVE_W // 2 - 24, NATIVE_H // 2 - 30, PALETTE["lightgray"])
    draw_text(surf, level.stage.name, NATIVE_W // 2 - len(level.stage.name) * 6, NATIVE_H // 2, PALETTE["yellow"], scale=2)
    if blink % 60 < 40:
        draw_text(surf, "GO!", NATIVE_W // 2 - 6, NATIVE_H // 2 + 30, PALETTE["white"])


# ----------------------------------------------------------------------
# Game class (state container + run loop)
# ----------------------------------------------------------------------


@dataclass(slots=True)
class Game:
    screen: pygame.Surface
    canvas: pygame.Surface
    clock: pygame.time.Clock
    state: GameState = GameState.TITLE
    blink: int = 0
    stage_idx: int = 0
    world: World | None = None
    intro_timer: int = 0

    def new_run(self) -> None:
        self.stage_idx = 0
        self.world = self._make_world(carry=None)
        self.state = GameState.LEVEL_INTRO
        self.intro_timer = 90

    def _make_world(self, carry: Player | None) -> World:
        level = Level(STAGES[self.stage_idx])
        if carry is not None:
            player = carry
            player.x = 32
            player.y = GROUND_Y - 24
            player.vx = player.vy = 0
            player.state = PlayerState.IDLE
        else:
            player = Player(
                x=32, y=GROUND_Y - 24,
                hp=PLAYER_MAX_HP, lives=STARTING_LIVES,
                batarangs=STARTING_BATARANGS,
                next_extra_life=EXTRA_LIFE_AT,
            )
        return World(level=level, player=player)

    def advance_stage(self) -> None:
        assert self.world is not None
        if self.stage_idx + 1 >= len(STAGES):
            self.state = GameState.VICTORY
            return
        self.stage_idx += 1
        self.world = self._make_world(carry=self.world.player)
        self.state = GameState.LEVEL_INTRO
        self.intro_timer = 90

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state in {GameState.TITLE, GameState.GAME_OVER, GameState.VICTORY}:
                    return False
                self.state = GameState.TITLE
                return True
            if self.state is GameState.TITLE and event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                self.new_run()
            elif self.state is GameState.PLAYING and self.world is not None:
                p = self.world.player
                match event.key:
                    case pygame.K_SPACE | pygame.K_UP | pygame.K_w:
                        p.try_jump()
                    case pygame.K_z | pygame.K_j:
                        p.try_punch()
                    case pygame.K_x | pygame.K_k:
                        p.try_kick()
                    case pygame.K_c | pygame.K_l:
                        bat = p.try_throw()
                        if bat is not None:
                            self.world.batarangs.append(bat)
                    case pygame.K_DOWN | pygame.K_s:
                        p.try_slide()
            elif self.state in {GameState.GAME_OVER, GameState.VICTORY} and event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                self.new_run()
        return True

    # ------------------------------------------------------------------
    def update(self, keys: pygame.key.ScancodeWrapper) -> None:
        self.blink += 1
        match self.state:
            case GameState.LEVEL_INTRO:
                self.intro_timer -= 1
                if self.intro_timer <= 0:
                    self.state = GameState.PLAYING
            case GameState.PLAYING if self.world is not None:
                _update_world(self.world, keys)
                w = self.world
                # Dead?
                if w.player.state is PlayerState.DEAD and w.player.state_timer <= 0:
                    self.state = GameState.GAME_OVER
                # Stage cleared?
                if w.level.stage.boss:
                    if w.boss_defeated:
                        self.advance_stage()
                else:
                    if w.player.x >= w.level.width_px - NATIVE_W // 2:
                        self.advance_stage()
            case _:
                pass

    def draw(self) -> None:
        c = self.canvas
        match self.state:
            case GameState.TITLE:
                _draw_title(c, self.blink)
            case GameState.LEVEL_INTRO if self.world is not None:
                _draw_intro(c, self.world.level, self.blink)
            case GameState.PLAYING if self.world is not None:
                _draw_world(c, self.world)
            case GameState.GAME_OVER if self.world is not None:
                _draw_world(c, self.world)
                _draw_game_over(c, self.world, self.blink)
            case GameState.VICTORY if self.world is not None:
                _draw_world(c, self.world)
                _draw_victory(c, self.world, self.blink)

        # Apply screen shake during gameplay (post-draw)
        ox, oy = (0, 0)
        if self.state is GameState.PLAYING and self.world is not None:
            ox, oy = self.world.shake.update()
        scaled = pygame.transform.scale(c, (WINDOW_W, WINDOW_H))
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled, (ox * 3, oy * 3))
        pygame.display.flip()

    def run(self) -> None:
        running = True
        while running:
            for ev in pygame.event.get():
                if not self.handle_event(ev):
                    running = False
            keys = pygame.key.get_pressed()
            self.update(keys)
            self.draw()
            self.clock.tick(FPS)


# ----------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------


def create_game() -> Game:
    audio.init()
    pygame.init()
    pygame.display.set_caption("Batman Returns — Python Homage")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    canvas = pygame.Surface((NATIVE_W, NATIVE_H))
    clock = pygame.time.Clock()
    # Warm sprite cache so first frame isn't slow
    for name in sprites.SPRITE_REGISTRY:
        sprites.get(name)
    return Game(screen=screen, canvas=canvas, clock=clock)
