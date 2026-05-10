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
from . import music, persistence
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
    midboss_spawned: bool = False
    midboss_defeated: bool = False
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
        world.floats.emit("THE PENGUIN!", world.player.x, world.player.y - 30, PALETTE["red"])

    # Midboss spawn
    if (
        stage.midboss_kind
        and not world.midboss_spawned
        and world.player.x > stage.midboss_at_tile * TILE_SIZE
    ):
        kind = EnemyKind(stage.midboss_kind)
        boss_x = world.player.x + 100
        world.enemies.append(Enemy.spawn(kind, boss_x, GROUND_Y - 28))
        world.midboss_spawned = True
        audio.boss_roar().play()
        label = {"midboss_joker": "THE JOKER!", "midboss_catwoman": "CATWOMAN!"}[stage.midboss_kind]
        world.floats.emit(label, world.player.x, world.player.y - 30, PALETTE["magenta"])


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
        for proj in e.update(p, world.level):
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
                    if e.kind is EnemyKind.BOSS_PENGUIN:
                        world.boss_defeated = True
                    elif e.kind in {EnemyKind.MIDBOSS_JOKER, EnemyKind.MIDBOSS_CATWOMAN}:
                        world.midboss_defeated = True
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
                    if e.kind is EnemyKind.BOSS_PENGUIN:
                        world.boss_defeated = True
                    elif e.kind in {EnemyKind.MIDBOSS_JOKER, EnemyKind.MIDBOSS_CATWOMAN}:
                        world.midboss_defeated = True
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


def _draw_pause(surf: pygame.Surface, cursor: int, sfx_vol: float, music_vol: float) -> None:
    overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surf.blit(overlay, (0, 0))
    draw_text(surf, "PAUSED", NATIVE_W // 2 - 30, NATIVE_H // 2 - 60, PALETTE["yellow"], scale=2)
    items = [
        "RESUME",
        "QUIT TO TITLE",
        f"SFX VOL {int(sfx_vol * 100):3d}",
        f"MUSIC VOL {int(music_vol * 100):3d}",
    ]
    for i, label in enumerate(items):
        col = PALETTE["yellow"] if i == cursor else PALETTE["lightgray"]
        prefix = "> " if i == cursor else "  "
        draw_text(surf, prefix + label, NATIVE_W // 2 - 60, NATIVE_H // 2 - 20 + i * 14, col)


def _draw_high_scores(surf: pygame.Surface, scores: list[int]) -> None:
    surf.fill(PALETTE["dark"])
    draw_text(surf, "HIGH SCORES", NATIVE_W // 2 - 60, 30, PALETTE["yellow"], scale=2)
    if not scores:
        draw_text(surf, "NO SCORES YET", NATIVE_W // 2 - 40, 90, PALETTE["lightgray"])
    for i, s in enumerate(scores):
        draw_text(surf, f"{i+1}. {s:08d}", NATIVE_W // 2 - 50, 80 + i * 16, PALETTE["white"])
    draw_text(surf, "ENTER TO RETURN", NATIVE_W // 2 - 50, NATIVE_H - 24, PALETTE["gray"])


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
    save: persistence.SaveData = field(default_factory=persistence.load)
    pause_cursor: int = 0
    score_recorded: bool = False

    def new_run(self) -> None:
        self.stage_idx = 0
        self.world = self._make_world(carry=None)
        self.state = GameState.LEVEL_INTRO
        self.intro_timer = 90
        self.score_recorded = False
        music.set_volume(self.save.music_volume)
        music.play_stage(self.stage_idx)

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
            music.stop()
            return
        self.stage_idx += 1
        self.world = self._make_world(carry=self.world.player)
        self.state = GameState.LEVEL_INTRO
        self.intro_timer = 90
        music.play_stage(self.stage_idx)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            persistence.save(self.save)
            return False
        # Translate joystick into keyboard-equivalents
        if event.type == pygame.JOYBUTTONDOWN:
            event = _pad_to_key(event)
            if event is None:
                return True
        elif event.type == pygame.JOYDEVICEADDED:
            try:
                pygame.joystick.Joystick(event.device_index).init()
            except (pygame.error, AttributeError):
                pass
            return True
        if event.type != pygame.KEYDOWN:
            return True

        match self.state:
            case GameState.TITLE:
                if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self.new_run()
                elif event.key == pygame.K_h:
                    self.state = GameState.HIGH_SCORES
                elif event.key == pygame.K_ESCAPE:
                    persistence.save(self.save)
                    return False
            case GameState.HIGH_SCORES:
                if event.key in {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self.state = GameState.TITLE
            case GameState.PLAYING if self.world is not None:
                p = self.world.player
                match event.key:
                    case pygame.K_ESCAPE | pygame.K_p:
                        self.state = GameState.PAUSED
                        self.pause_cursor = 0
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
            case GameState.PAUSED:
                if event.key in {pygame.K_UP, pygame.K_w}:
                    self.pause_cursor = (self.pause_cursor - 1) % 4
                elif event.key in {pygame.K_DOWN, pygame.K_s}:
                    self.pause_cursor = (self.pause_cursor + 1) % 4
                elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    if self.pause_cursor == 0:
                        self.state = GameState.PLAYING
                    elif self.pause_cursor == 1:  # quit to title
                        self._record_score()
                        music.stop()
                        self.state = GameState.TITLE
                    elif self.pause_cursor == 2:  # toggle SFX volume
                        self.save.sfx_volume = round((self.save.sfx_volume + 0.25) % 1.25, 2)
                        audio.set_sfx_volume(self.save.sfx_volume)
                        persistence.save(self.save)
                    elif self.pause_cursor == 3:  # toggle Music volume
                        self.save.music_volume = round((self.save.music_volume + 0.25) % 1.25, 2)
                        music.set_volume(self.save.music_volume)
                        persistence.save(self.save)
                elif event.key in {pygame.K_ESCAPE, pygame.K_p}:
                    self.state = GameState.PLAYING
            case GameState.GAME_OVER | GameState.VICTORY:
                if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self._record_score()
                    self.new_run()
                elif event.key == pygame.K_ESCAPE:
                    self._record_score()
                    self.state = GameState.TITLE
        return True

    def _record_score(self) -> None:
        if self.score_recorded or self.world is None:
            return
        self.save.push_score(self.world.player.score)
        persistence.save(self.save)
        self.score_recorded = True

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
                    self._record_score()
                    self.state = GameState.GAME_OVER
                    music.stop()
                # Stage cleared?
                if w.level.stage.boss:
                    if w.boss_defeated:
                        self.advance_stage()
                        if self.state is GameState.VICTORY:
                            self._record_score()
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
                if self.save.high_scores:
                    draw_text(c, f"BEST {self.save.high_scores[0]:06d}", 4, 4, PALETTE["yellow"])
                draw_text(c, "H: HIGH SCORES", NATIVE_W - 90, 4, PALETTE["gray"])
            case GameState.HIGH_SCORES:
                _draw_high_scores(c, self.save.high_scores)
            case GameState.LEVEL_INTRO if self.world is not None:
                _draw_intro(c, self.world.level, self.blink)
            case GameState.PLAYING if self.world is not None:
                _draw_world(c, self.world)
            case GameState.PAUSED if self.world is not None:
                _draw_world(c, self.world)
                _draw_pause(c, self.pause_cursor, self.save.sfx_volume, self.save.music_volume)
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
            extra: dict[int, bool] = {}
            _sample_pad_held(extra)
            keys = _AugmentedKeys(pygame.key.get_pressed(), extra)
            self.update(keys)
            self.draw()
            self.clock.tick(FPS)


# ----------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------


_PAD_TO_KEY: dict[int, int] = {
    0: pygame.K_SPACE,   # A → jump
    1: pygame.K_c,       # B → batarang
    2: pygame.K_z,       # X → punch
    3: pygame.K_x,       # Y → kick
    4: pygame.K_DOWN,    # LB → slide
    5: pygame.K_DOWN,    # RB → slide
    7: pygame.K_p,       # Start → pause
    9: pygame.K_p,
    6: pygame.K_ESCAPE,  # Back / Select
}


def _pad_to_key(event: pygame.event.Event) -> pygame.event.Event | None:
    key = _PAD_TO_KEY.get(event.button)
    if key is None:
        return None
    return pygame.event.Event(pygame.KEYDOWN, {"key": key})


def _sample_pad_held(keys_dict: dict[int, bool]) -> None:
    """Treat analog stick / dpad as virtual key holds for movement."""
    for i in range(pygame.joystick.get_count()):
        try:
            j = pygame.joystick.Joystick(i)
            if not j.get_init():
                j.init()
            if j.get_numaxes() >= 2:
                ax = j.get_axis(0)
                ay = j.get_axis(1)
                if ax < -0.4:
                    keys_dict[pygame.K_LEFT] = True
                if ax > 0.4:
                    keys_dict[pygame.K_RIGHT] = True
                if ay < -0.4:
                    keys_dict[pygame.K_UP] = True
                if ay > 0.4:
                    keys_dict[pygame.K_DOWN] = True
            if j.get_numhats() >= 1:
                hx, hy = j.get_hat(0)
                if hx < 0:
                    keys_dict[pygame.K_LEFT] = True
                if hx > 0:
                    keys_dict[pygame.K_RIGHT] = True
                if hy > 0:
                    keys_dict[pygame.K_UP] = True
                if hy < 0:
                    keys_dict[pygame.K_DOWN] = True
        except pygame.error:
            pass


class _AugmentedKeys:
    """Wraps pygame.key.get_pressed() with extra virtual-press flags from gamepad."""
    __slots__ = ("_real", "_extra")

    def __init__(self, real: pygame.key.ScancodeWrapper, extra: dict[int, bool]):
        self._real = real
        self._extra = extra

    def __getitem__(self, key: int) -> bool:
        return bool(self._real[key]) or bool(self._extra.get(key))


def create_game() -> Game:
    audio.init()
    pygame.init()
    pygame.joystick.init()
    pygame.display.set_caption("Batman Returns — Python Homage")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    canvas = pygame.Surface((NATIVE_W, NATIVE_H))
    clock = pygame.time.Clock()
    for i in range(pygame.joystick.get_count()):
        try:
            pygame.joystick.Joystick(i).init()
        except pygame.error:
            pass
    # Warm sprite cache so first frame isn't slow
    for name in sprites.SPRITE_REGISTRY:
        sprites.get(name)
    g = Game(screen=screen, canvas=canvas, clock=clock)
    audio.set_sfx_volume(g.save.sfx_volume)
    return g
