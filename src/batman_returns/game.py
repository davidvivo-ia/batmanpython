"""Main game loop and state machine."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame

from . import audio, i18n, music, persistence, sprites
from .achievements import AchievementTracker
from .constants import (
    DIFFICULTY_SCALARS,
    EXTRA_LIFE_AT,
    FPS,
    GROUND_Y,
    NATIVE_H,
    NATIVE_W,
    PALETTE,
    PLAYER_MAX_HP,
    STARTING_LIVES,
    TILE_SIZE,
    WINDOW_H,
    WINDOW_W,
    EnemyKind,
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
from .hud import (
    draw_goal_arrow,
    draw_hud,
    draw_progress_bar,
    draw_text,
    draw_warning_banner,
)
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
    achievements: AchievementTracker = field(default_factory=AchievementTracker)
    warning_text: str = ""
    warning_timer: int = 0
    frame: int = 0
    difficulty: str = "normal"
    first_kill_done: bool = False
    # Stats for stage-clear summary
    kills: int = 0
    damage_taken: int = 0
    pickups_collected: int = 0
    time_frames: int = 0
    combo_max: int = 0
    batarangs_used: int = 0


def _spawn_for_stage(world: World) -> None:
    """Stream enemies as the camera advances. Mirrors original 'wave by map' design."""
    stage = world.level.stage
    cam_tile = int(world.level.cam_x // TILE_SIZE)
    edge_tile = cam_tile + NATIVE_W // TILE_SIZE + 4
    scalars = DIFFICULTY_SCALARS[world.difficulty]
    hp_scale = scalars["enemy_hp"]
    dmg_scale = scalars["enemy_dmg"]
    while world.spawn_index < edge_tile and world.spawn_index < stage.length_tiles:
        tx = world.spawn_index
        world.spawn_index += 1
        if tx < 8:
            continue  # safe zone at start
        if tx > stage.length_tiles - 16 and stage.boss:
            break  # save boss arena
        if world.rng.random() < stage.enemy_density:
            # Stage-specific roster:
            # - Streets/Rooftops/Docks get motorcycles
            # - Sewers/Asylum get heavy WKLITE clowns + cannons
            # - Ice gets skaters
            stage_name = stage.name
            if stage.snow:
                population = [
                    EnemyKind.BASHER, EnemyKind.JACKBOX, EnemyKind.FIREBREATHER,
                    EnemyKind.KNIFER, EnemyKind.SKATER,
                ]
                weights = [4, 1, 2, 2, 3]
            elif "ROOFTOPS" in stage_name or "STREETS" in stage_name or "DOCKS" in stage_name:
                population = [
                    EnemyKind.BASHER, EnemyKind.JACKBOX, EnemyKind.FIREBREATHER,
                    EnemyKind.KNIFER, EnemyKind.CYCLE, EnemyKind.CANNON,
                ]
                weights = [4, 1, 2, 2, 3, 1]
            elif "SEWERS" in stage_name or "ASYLUM" in stage_name:
                population = [
                    EnemyKind.BASHER, EnemyKind.JACKBOX, EnemyKind.FIREBREATHER,
                    EnemyKind.KNIFER, EnemyKind.WKLITE, EnemyKind.CANNON,
                ]
                weights = [3, 2, 2, 2, 2, 1]
            else:
                population = [
                    EnemyKind.BASHER, EnemyKind.JACKBOX, EnemyKind.FIREBREATHER,
                    EnemyKind.KNIFER,
                ]
                weights = [5, 2, 2, 3]
            kind = world.rng.choices(population=population, weights=weights)[0]
            wx = tx * TILE_SIZE + 8
            # CYCLE spawns at a y-position that lets it streak across.
            spawn_y = GROUND_Y - 16 if kind == EnemyKind.CYCLE else GROUND_Y - 24
            world.enemies.append(Enemy.spawn(kind, wx, spawn_y, hp_scale, dmg_scale))
        # Pickup chance
        if world.rng.random() < 0.04:
            wx = tx * TILE_SIZE + 8
            world.pickups.append(random_pickup(wx, world.rng))

    # Boss spawn at end of last stage
    if stage.boss and not world.boss_spawned and world.player.x > (stage.length_tiles - 18) * TILE_SIZE:
        boss_x = world.player.x + 120
        world.enemies.append(Enemy.spawn(
            EnemyKind.BOSS_PENGUIN, boss_x, GROUND_Y - 32, hp_scale, dmg_scale,
        ))
        world.boss_spawned = True
        if pygame.mixer.get_init():
            audio.boss_roar().play()
        world.floats.emit("THE PENGUIN!", world.player.x, world.player.y - 30, PALETTE["red"])
        world.warning_text = "WARNING - PENGUIN APPROACHES"
        world.warning_timer = 90

    # Midboss spawn — pin to a fixed world position (not relative to player)
    # so a player who runs through the trigger zone doesn't shove the midboss
    # off-stage; also pause mook spawning during the midboss fight.
    if (
        stage.midboss_kind
        and not world.midboss_spawned
        and world.player.x > stage.midboss_at_tile * TILE_SIZE
    ):
        kind = EnemyKind(stage.midboss_kind)
        boss_world_x = (stage.midboss_at_tile + 8) * TILE_SIZE
        boss_world_x = min(boss_world_x, stage.length_tiles * TILE_SIZE - 32)
        world.enemies.append(Enemy.spawn(kind, boss_world_x, GROUND_Y - 28, hp_scale, dmg_scale))
        world.midboss_spawned = True
        # Skip the spawn cursor past the midboss arena so we don't dump mooks
        # on top of the boss fight.
        world.spawn_index = max(world.spawn_index, stage.midboss_at_tile + 16)
        if pygame.mixer.get_init():
            audio.boss_roar().play()
        label = {"midboss_joker": "THE JOKER!", "midboss_catwoman": "CATWOMAN!"}[stage.midboss_kind]
        world.floats.emit(label, world.player.x, world.player.y - 30, PALETTE["magenta"])
        warn = {
            "midboss_joker": "WARNING - JOKER AHEAD",
            "midboss_catwoman": "WARNING - CATWOMAN AHEAD",
        }[stage.midboss_kind]
        world.warning_text = warn
        world.warning_timer = 90


def _award(world: World, points: int, x: float, y: float) -> None:
    world.player.add_score(points)
    world.floats.emit(f"+{points}", x, y - 8)


def _update_world(world: World, keys: pygame.key.ScancodeWrapper) -> None:
    if world.freeze.tick():
        return
    p = world.player
    hp_before = p.hp
    was_on_ground = p.on_ground
    was_divekick = p.state is PlayerState.DIVEKICK
    # Charged batarang: hold C, on release if held >=45 frames fire piercing.
    held = bool(keys[pygame.K_c] or keys[pygame.K_l])
    if held:
        p.charge_frames = min(p.charge_frames + 1, 90)
        if p.charge_frames == 45:
            world.particles.emit(p.x, p.y + 8, count=4, speed=0.6, life=20,
                                 color=PALETTE["yellow"])
    elif p.charge_frames >= 45:
        bat = p.try_throw(charged=True)
        if bat is not None:
            world.batarangs.append(bat)
            world.particles.emit(bat.x, bat.y, count=14, speed=2.6, life=14,
                                 color=PALETTE["yellow"])
            world.shake.kick(2.5)
            world.floats.emit("CHARGED!", p.x, p.y - 16, PALETTE["yellow"])
        p.charge_frames = 0
    else:
        p.charge_frames = 0
    p.update(keys, world.level)
    # Landing dust
    if not was_on_ground and p.on_ground:
        world.particles.dust(p.x, p.y + p.H)

    # Camera follows player
    target_cam = p.x - NATIVE_W // 2
    world.level.update(target_cam, 1 / FPS)

    _spawn_for_stage(world)

    # Update enemies. Cap projectile pool defensively (Penguin phase 3 with
    # extreme cadence shouldn't be able to OOM the screen).
    MAX_ENEMY_SHOTS = 64
    for e in world.enemies:
        if not e.alive:
            continue
        for proj in e.update(p, world.level):
            if len(world.enemy_shots) < MAX_ENEMY_SHOTS:
                world.enemy_shots.append(proj)

    # Update projectiles
    for b in world.batarangs:
        b.owner_x_ref = p.x
        b.update(world.level)
        # Re-catch on the return leg if it overlaps the player.
        if b.returning and b.alive and b.hitbox.intersects(p.hitbox):
            b.alive = False
            p.batarangs += 1
            world.particles.emit(p.x, p.y + 6, count=6, speed=1.4, life=12,
                                 color=PALETTE["yellow"])
            world.floats.emit("RECATCH", p.x, p.y - 12, PALETTE["yellow"])
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
            if e.alive and not e.is_dying and atk.intersects(e.hitbox):
                any_hit = True
                kb = 4.0 * p.facing
                cx, cy = e.x, e.y + e.H / 2
                world.particles.burst_hit(cx, cy)
                world.shake.kick(2.5)
                killed = e.take_damage(dmg, knockback=kb)
                if killed:
                    world.kills += 1
                    pts = p.combo_score_bonus(e.score_value)
                    _award(world, pts, e.x, e.y)
                    world.particles.burst_blood(cx, cy, dir_sign=p.facing)
                    world.shake.kick(5.0)
                    if not world.first_kill_done:
                        world.first_kill_done = True
                        world.freeze.kick(10)  # extra hit-stop on the first kill
                        world.floats.emit("FIRST BLOOD!", e.x, e.y - 16, PALETTE["yellow"])
                    else:
                        world.freeze.kick(3 if not e.boss else 8)
                    world.achievements.on_kill(was_batarang=False, was_divekick=was_divekick)
                    if e.kind is EnemyKind.BOSS_PENGUIN:
                        world.boss_defeated = True
                        world.achievements.on_boss_killed("boss_penguin")
                    elif e.kind is EnemyKind.MIDBOSS_JOKER:
                        world.midboss_defeated = True
                        world.achievements.on_boss_killed("boss_joker")
                    elif e.kind is EnemyKind.MIDBOSS_CATWOMAN:
                        world.midboss_defeated = True
                        world.achievements.on_boss_killed("boss_catwoman")
        if any_hit:
            p.register_combo_hit()
            world.achievements.on_combo(p.combo)
            combo_name = {2: "DOUBLE", 3: "TRIPLE", 5: "MEGA COMBO!", 7: "INSANE!", 10: "UNSTOPPABLE!"}.get(p.combo)
            if combo_name:
                world.floats.emit(combo_name, p.x, p.y - 20, PALETTE["yellow"])
            elif p.combo >= 4:
                world.floats.emit(f"{p.combo}X COMBO!", p.x, p.y - 20, PALETTE["yellow"])

    # Batarang vs enemies
    for b in world.batarangs:
        if not b.alive:
            continue
        for e in world.enemies:
            if not (e.alive and not e.is_dying and b.hitbox.intersects(e.hitbox)):
                continue
            if id(e) in b.hit_set:
                continue  # already hit this enemy on a piercing shot
            b.hit_set.add(id(e))
            cx, cy = e.x, e.y + e.H / 2
            world.particles.spark(cx, cy, PALETTE["white"])
            killed = e.take_damage(b.damage, knockback=2.0 * (1 if b.vx > 0 else -1))
            if killed:
                world.kills += 1
                _award(world, e.score_value, e.x, e.y)
                world.particles.burst_blood(cx, cy, dir_sign=1 if b.vx > 0 else -1)
                world.shake.kick(4.0)
                world.freeze.kick(3 if not e.boss else 8)
                world.achievements.on_kill(was_batarang=True, was_divekick=False)
                if e.kind is EnemyKind.BOSS_PENGUIN:
                    world.boss_defeated = True
                    world.achievements.on_boss_killed("boss_penguin")
                elif e.kind is EnemyKind.MIDBOSS_JOKER:
                    world.midboss_defeated = True
                    world.achievements.on_boss_killed("boss_joker")
                elif e.kind is EnemyKind.MIDBOSS_CATWOMAN:
                    world.midboss_defeated = True
                    world.achievements.on_boss_killed("boss_catwoman")
            if not b.piercing:
                b.alive = False
                break

    # Enemies vs player (contact + projectiles).
    # Only one damage event per frame; iframes are still respected by take_damage.
    if p.iframes <= 0:
        for e in world.enemies:
            if e.alive and not e.is_dying and e.hitbox.intersects(p.hitbox):
                p.take_damage(e.contact_damage)
                world.particles.burst_blood(p.x, p.y + 8, dir_sign=-p.facing)
                world.shake.kick(4.0)
                break
    for s in world.enemy_shots:
        if s.alive and s.hitbox.intersects(p.hitbox):
            if p.iframes <= 0:
                world.particles.spark(p.x, p.y + 10, PALETTE["red"])
                world.shake.kick(3.0)
                p.take_damage(s.damage)
            s.alive = False

    # Pickups
    for pk in world.pickups:
        if pk.alive and pk.hitbox.intersects(p.hitbox):
            world.particles.emit(pk.x, pk.y, count=10, color=PALETTE["green"], speed=2.0, life=18)
            label = {
                "health": "HEALTH",
                "batarang": "+3 BAT",
                "1up": "1UP",
                "smoke": "SMOKE BOMB!",
                "invuln": "INVINCIBLE!",
                "dmg2x": "2X DAMAGE!",
                "infbat": "INFINITE BAT!",
            }[pk.kind]
            world.floats.emit(label, pk.x, pk.y, PALETTE["green"])
            pk.apply(p)
            if pk.kind == "smoke":
                # AOE: damage all non-boss enemies on screen.
                for e in world.enemies:
                    if not e.alive or e.boss or e.is_dying:
                        continue
                    if abs(e.x - p.x) < 160 and abs(e.y - p.y) < 80:
                        e.iframes = 0
                        if e.take_damage(999):
                            _award(world, e.score_value, e.x, e.y)
                # Big visual smoke
                for _ in range(40):
                    world.particles.emit(
                        p.x, p.y + 8, count=1, speed=3.5, life=30,
                        color=PALETTE["lightgray"], gravity=-0.05,
                    )
                world.shake.kick(6.0)

    # Track damage taken for "no damage" achievement + stage stats
    if p.hp < hp_before:
        world.achievements.on_damage(hp_before - p.hp)
        world.damage_taken += hp_before - p.hp
    world.combo_max = max(world.combo_max, p.combo)
    world.time_frames += 1
    world.achievements.on_score(p.score)

    # FX update
    world.particles.update()
    world.floats.update()
    world.achievements.update()
    if world.warning_timer > 0:
        world.warning_timer -= 1
    world.frame += 1

    # Cleanup
    world.enemies = [e for e in world.enemies if e.alive]
    world.batarangs = [b for b in world.batarangs if b.alive]
    world.enemy_shots = [s for s in world.enemy_shots if s.alive]
    world.pickups = [pk for pk in world.pickups if pk.alive]


def _world_objective(world: World) -> str:
    stage = world.level.stage
    if stage.boss:
        return "DEFEAT THE PENGUIN" if not world.boss_defeated else "VICTORY!"
    if stage.midboss_kind and not world.midboss_defeated:
        return {
            "midboss_joker": "DEFEAT THE JOKER",
            "midboss_catwoman": "DEFEAT CATWOMAN",
        }[stage.midboss_kind]
    if stage.hazard_kind == "pit":
        return "WATCH YOUR STEP — REACH THE FLAG >>"
    if stage.hazard_kind == "water":
        return "MIND THE WATER — REACH THE FLAG >>"
    return "REACH THE FLAG >>"


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
    # Foreground parallax (drawn after entities so lamps/icicles occlude)
    world.level.draw_foreground(surf)

    # Progress bar at top-centre
    stage = world.level.stage
    progress = world.level.cam_x / max(1, world.level.width_px - 320)
    midboss_marker = (stage.midboss_at_tile * 16) / world.level.width_px if stage.midboss_kind else None
    draw_progress_bar(surf, progress, midboss_marker, midboss_alive=not world.midboss_defeated)

    objective = _world_objective(world)
    draw_hud(surf, world.player, stage.name, objective=objective)
    _draw_toasts(surf, world)

    # Goal arrow on right edge during the last screen of non-boss stages
    if not stage.boss and world.player.x > world.level.width_px - 320 * 1.5:
        draw_goal_arrow(surf, world.frame)

    # Boss / midboss warning banner
    if world.warning_timer > 0:
        draw_warning_banner(surf, world.warning_text, world.warning_timer)


def _draw_tutorial(surf: pygame.Surface, text: str, frame: int) -> None:
    if not text:
        return
    # Bottom-of-screen prompt with subtle blink
    alpha = 200 if (frame // 6) % 2 == 0 else 160
    box_w = len(text) * 6 + 24
    box_x = NATIVE_W // 2 - box_w // 2
    box_y = NATIVE_H - 56
    overlay = pygame.Surface((box_w, 18), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, alpha))
    surf.blit(overlay, (box_x, box_y))
    pygame.draw.rect(surf, PALETTE["yellow"], (box_x, box_y, box_w, 18), 1)
    draw_text(surf, text, box_x + 12, box_y + 6, PALETTE["white"])


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


def _draw_toasts(surf: pygame.Surface, world: World) -> None:
    """Stack achievement toasts in the upper-right corner."""
    y = 20
    for t in list(world.achievements.toasts)[:3]:
        # Fade in/out by life
        bar_w = len(t.text) * 6 + 24
        bar_x = NATIVE_W - bar_w - 4
        pygame.draw.rect(surf, PALETTE["dark"], (bar_x, y, bar_w, 14))
        pygame.draw.rect(surf, PALETTE["yellow"], (bar_x, y, bar_w, 14), 1)
        draw_text(surf, "* " + t.text, bar_x + 4, y + 4, PALETTE["yellow"])
        y += 18


def _draw_pause(surf: pygame.Surface, cursor: int, sfx_vol: float, music_vol: float) -> None:
    overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    surf.blit(overlay, (0, 0))
    draw_text(surf, "PAUSED", NATIVE_W // 2 - 30, NATIVE_H // 2 - 70, PALETTE["yellow"], scale=2)
    items = [
        "RESUME",
        "CONTROLS",
        "QUIT TO TITLE",
        f"SFX VOL {int(sfx_vol * 100):3d}",
        f"MUSIC VOL {int(music_vol * 100):3d}",
    ]
    for i, label in enumerate(items):
        col = PALETTE["yellow"] if i == cursor else PALETTE["lightgray"]
        prefix = "> " if i == cursor else "  "
        draw_text(surf, prefix + label, NATIVE_W // 2 - 60, NATIVE_H // 2 - 30 + i * 14, col)


def _draw_title_menu(surf: pygame.Surface, items: list[str], cursor: int) -> None:
    y = NATIVE_H - 40 - len(items) * 12
    for i, label in enumerate(items):
        col = PALETTE["yellow"] if i == cursor else PALETTE["lightgray"]
        prefix = "> " if i == cursor else "  "
        x = NATIVE_W // 2 - 50
        draw_text(surf, prefix + label, x, y + i * 12, col)


def _draw_controls_screen(surf: pygame.Surface) -> None:
    """Full controls reference, reachable from pause menu."""
    overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surf.blit(overlay, (0, 0))
    draw_text(surf, "CONTROLS", NATIVE_W // 2 - 36, 16, PALETTE["yellow"], scale=2)

    rows = [
        ("ARROWS / WASD", "MOVE"),
        ("SHIFT", "RUN"),
        ("SPACE / UP", "JUMP"),
        ("Z / J", "PUNCH"),
        ("X / K", "KICK (AIR = DIVE)"),
        ("C / L", "BATARANG (HOLD = CHARGE)"),
        ("DOWN / S", "SLIDE"),
        ("P / ESC", "PAUSE"),
        ("PAD A", "JUMP"),
        ("PAD X", "PUNCH"),
        ("PAD Y", "KICK"),
        ("PAD B", "BATARANG"),
        ("PAD LB/RB", "SLIDE"),
    ]
    y = 56
    for k, v in rows:
        draw_text(surf, k, 36, y, PALETTE["yellow"])
        draw_text(surf, v, 168, y, PALETTE["lightgray"])
        y += 12
    draw_text(surf, "ESC TO RETURN", NATIVE_W // 2 - 40, NATIVE_H - 16, PALETTE["gray"])


def _draw_settings(surf: pygame.Surface, save: persistence.SaveData, cursor: int) -> None:
    overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surf.blit(overlay, (0, 0))
    draw_text(surf, i18n.t("settings"), NATIVE_W // 2 - 36, 16, PALETTE["yellow"], scale=2)
    lang_label = "ENG" if save.language == "en" else "ESP"
    items = [
        f"{i18n.t('difficulty'):12s} {save.difficulty.upper()}",
        f"{i18n.t('sfx_volume'):12s} {int(save.sfx_volume * 100):3d}",
        f"{i18n.t('music_volume'):12s} {int(save.music_volume * 100):3d}",
        f"{i18n.t('show_fps'):12s} {'ON' if save.show_fps else 'OFF'}",
        f"{i18n.t('language'):12s} {lang_label}",
        i18n.t("reset_high_scores"),
        i18n.t("back"),
    ]
    for i, label in enumerate(items):
        col = PALETTE["yellow"] if i == cursor else PALETTE["lightgray"]
        prefix = "> " if i == cursor else "  "
        draw_text(surf, prefix + label, 40, 50 + i * 14, col)
    draw_text(surf, "UP/DOWN MOVE  ENTER CHANGE  ESC BACK", 16, NATIVE_H - 16, PALETTE["gray"])


def _draw_stage_select(surf: pygame.Surface, save: persistence.SaveData, cursor: int) -> None:
    overlay = pygame.Surface((NATIVE_W, NATIVE_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 220))
    surf.blit(overlay, (0, 0))
    draw_text(surf, "STAGE SELECT", NATIVE_W // 2 - 50, 16, PALETTE["yellow"], scale=2)
    # Hide the secret Batcave (index 7) until the player has unlocked it.
    last_visible = 7 if save.batcave_unlocked else 6
    names = [f"{i+1}. {STAGES[i].name}" for i in range(last_visible + 1)]
    max_unlocked = save.highest_cleared_stage + 1
    if save.beat_game:
        max_unlocked = last_visible
    for i, name in enumerate(names):
        unlocked = i <= max_unlocked
        col = PALETTE["yellow"] if i == cursor else (PALETTE["lightgray"] if unlocked else PALETTE["gray"])
        prefix = "> " if i == cursor else "  "
        suffix = "" if unlocked else "  [LOCKED]"
        draw_text(surf, prefix + name + suffix, 50, 50 + i * 14, col)
    if save.beat_game and save.batcave_unlocked:
        draw_text(surf, "* BATCAVE UNLOCKED", NATIVE_W // 2 - 60, NATIVE_H - 30, PALETTE["yellow"])
    draw_text(surf, "ENTER START  ESC BACK", NATIVE_W // 2 - 60, NATIVE_H - 16, PALETTE["gray"])


def _draw_stage_clear(
    surf: pygame.Surface,
    stage_idx: int,
    kills: int, time_frames: int, no_damage: bool, combo_max: int,
    total_bonus: int, anim_frame: int,
) -> None:
    """Show the stage-clear summary with progressively-revealed lines."""
    surf.fill(PALETTE["dark"])
    name = STAGES[stage_idx].name
    draw_text(surf, "STAGE CLEAR!", NATIVE_W // 2 - 60, 16, PALETTE["yellow"], scale=2)
    draw_text(surf, name, NATIVE_W // 2 - len(name) * 3, 38, PALETTE["white"])
    secs = time_frames // 60
    minutes = secs // 60
    secs %= 60
    rows = [
        (f"KILLS  x{kills:3d}", kills * 500),
        (f"TIME   {minutes:1d}:{secs:02d}", max(0, 5000 - time_frames * 2)),
        (f"MAX COMBO  x{combo_max:2d}", max(0, (combo_max - 2) * 300)),
    ]
    if no_damage:
        rows.append(("NO-DAMAGE BONUS", 5000))
    y = 70
    for i, (label, value) in enumerate(rows):
        if anim_frame > i * 12:
            col = PALETTE["yellow"] if anim_frame > (i + 1) * 12 else PALETTE["lightgray"]
            draw_text(surf, label, 40, y, col)
            draw_text(surf, f"+{value}", NATIVE_W - 80, y, col)
        y += 14
    if anim_frame > len(rows) * 12:
        pygame.draw.line(surf, PALETTE["white"], (40, y + 2), (NATIVE_W - 40, y + 2))
        draw_text(surf, "TOTAL", 40, y + 8, PALETTE["yellow"], scale=2)
        draw_text(surf, f"+{total_bonus}", NATIVE_W - 100, y + 8, PALETTE["yellow"], scale=2)
    if anim_frame > 80 and (anim_frame // 30) % 2 == 0:
        draw_text(surf, "PRESS ENTER TO CONTINUE", NATIVE_W // 2 - 80, NATIVE_H - 20, PALETTE["white"])


def _draw_high_scores(surf: pygame.Surface, scores: list[int]) -> None:
    surf.fill(PALETTE["dark"])
    draw_text(surf, "HIGH SCORES", NATIVE_W // 2 - 60, 30, PALETTE["yellow"], scale=2)
    if not scores:
        draw_text(surf, "NO SCORES YET", NATIVE_W // 2 - 40, 90, PALETTE["lightgray"])
    for i, s in enumerate(scores):
        draw_text(surf, f"{i+1}. {s:08d}", NATIVE_W // 2 - 50, 80 + i * 16, PALETTE["white"])
    draw_text(surf, "ENTER TO RETURN", NATIVE_W // 2 - 50, NATIVE_H - 24, PALETTE["gray"])


def _stage_objective_line(stage_idx: int) -> str:
    lines = [
        "OBJECTIVE: DEFEAT JOKER, REACH THE FLAG",
        "OBJECTIVE: WATCH YOUR STEP — REACH THE FLAG",
        "OBJECTIVE: AVOID THE WATER — REACH THE FLAG",
        "OBJECTIVE: DEFEAT CATWOMAN, REACH THE FLAG",
        "OBJECTIVE: CROSS THE DOCKS — REACH THE FLAG",
        "OBJECTIVE: SURVIVE ARKHAM — REACH THE FLAG",
        "OBJECTIVE: DEFEAT THE PENGUIN",
        "OBJECTIVE: BONUS GAUNTLET — SURVIVE THE BATCAVE",
    ]
    return lines[min(stage_idx, len(lines) - 1)]


def _draw_intro(surf: pygame.Surface, level: Level, blink: int, stage_idx: int) -> None:
    surf.fill(PALETTE["black"])
    draw_text(surf, f"STAGE {stage_idx + 1}", NATIVE_W // 2 - 30, 40, PALETTE["lightgray"])
    name_x = NATIVE_W // 2 - len(level.stage.name) * 6
    draw_text(surf, level.stage.name, name_x, 60, PALETTE["yellow"], scale=2)
    obj = _stage_objective_line(stage_idx)
    draw_text(surf, obj, NATIVE_W // 2 - len(obj) * 3, 90, PALETTE["white"])

    # Controls panel (boxed)
    box_y = 110
    pygame.draw.rect(surf, PALETTE["dark"], (24, box_y, NATIVE_W - 48, 70))
    pygame.draw.rect(surf, PALETTE["purple"], (24, box_y, NATIVE_W - 48, 70), 1)
    draw_text(surf, "CONTROLS", NATIVE_W // 2 - 24, box_y + 4, PALETTE["yellow"])
    lines = [
        ("ARROWS", "MOVE"),
        ("SPACE", "JUMP"),
        ("Z", "PUNCH"),
        ("X", "KICK / DIVE-KICK"),
        ("C", "BATARANG"),
        ("DOWN", "SLIDE"),
        ("SHIFT", "RUN"),
    ]
    for i, (k, label) in enumerate(lines):
        col = i % 2
        row = i // 2
        x = 32 + col * 144
        y = box_y + 18 + row * 12
        draw_text(surf, k, x, y, PALETTE["yellow"])
        draw_text(surf, label, x + 30, y, PALETTE["lightgray"])

    if blink % 60 < 40:
        draw_text(surf, "GO!", NATIVE_W // 2 - 6, NATIVE_H - 24, PALETTE["white"], scale=2)


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
    settings_cursor: int = 0
    stage_select_cursor: int = 0
    title_cursor: int = 0
    fps_history: list[float] = field(default_factory=list)
    tutorial_step: int = 0
    tutorial_text: str = ""
    tutorial_timer: int = 0
    tutorial_seen_first_enemy: bool = False
    tutorial_active: bool = False
    # Stage clear summary state
    clear_kills: int = 0
    clear_time_frames: int = 0
    clear_damage_taken: int = 0
    clear_combo_max: int = 0
    clear_total_bonus: int = 0
    clear_no_damage: bool = False
    clear_anim_frame: int = 0
    pending_stage_idx: int = 0

    def _title_items(self) -> list[str]:
        last = len(STAGES) - 1
        items = ["NEW GAME"]
        if 0 <= self.save.highest_cleared_stage < last:
            items.append("CONTINUE")
        if self.save.beat_game or self.save.highest_cleared_stage >= 0:
            items.append("STAGE SELECT")
        items.extend(["SETTINGS", "HIGH SCORES", "QUIT"])
        return items

    def _title_select(self, item: str) -> None:
        last = len(STAGES) - 1
        match item:
            case "NEW GAME":
                self.new_run()
            case "CONTINUE":
                next_stage = self.save.highest_cleared_stage + 1
                self.new_run(starting_stage=max(0, min(next_stage, last)))
            case "STAGE SELECT":
                self.state = GameState.STAGE_SELECT
                self.stage_select_cursor = 0
            case "SETTINGS":
                self.state = GameState.SETTINGS
                self.settings_cursor = 0
            case "HIGH SCORES":
                self.state = GameState.HIGH_SCORES
            case "QUIT":
                persistence.save(self.save)
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    def new_run(self, starting_stage: int = 0) -> None:
        self.stage_idx = starting_stage
        self.world = self._make_world(carry=None, carry_tracker=None)
        # Restore previously unlocked achievements (no toasts on restore)
        self.world.achievements.unlocked = set(self.save.unlocked)
        self.world.achievements.reset_for_stage(self.world.player.hp)
        self.state = GameState.LEVEL_INTRO
        self.intro_timer = 180  # 3 seconds — long enough to read the controls
        self.score_recorded = False
        # Tutorial: only on the first-ever run from stage 0
        if not self.save.tutorial_seen and starting_stage == 0:
            self.tutorial_active = True
            self.tutorial_step = 0
        else:
            self.tutorial_active = False
        music.set_volume(self.save.music_volume)
        music.play_stage(self.stage_idx)

    def _make_world(self, carry: Player | None, carry_tracker: AchievementTracker | None) -> World:
        level = Level(STAGES[self.stage_idx])
        scalars = DIFFICULTY_SCALARS[self.save.difficulty]
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
                batarangs=int(scalars["starting_batarangs"]),
                next_extra_life=EXTRA_LIFE_AT,
            )
        w = World(level=level, player=player, difficulty=self.save.difficulty)
        if carry_tracker is not None:
            w.achievements = carry_tracker
        return w

    def advance_stage(self) -> None:
        assert self.world is not None
        # Capture stats for the post-stage summary
        self.clear_kills = self.world.kills
        self.clear_time_frames = self.world.time_frames
        self.clear_damage_taken = self.world.damage_taken
        self.clear_combo_max = self.world.combo_max
        self.clear_no_damage = self.world.damage_taken == 0
        # Compute bonuses
        kill_bonus = self.clear_kills * 500
        time_bonus = max(0, 5000 - self.clear_time_frames * 2)
        no_dmg_bonus = 5000 if self.clear_no_damage else 0
        combo_bonus = max(0, (self.clear_combo_max - 2) * 300)
        self.clear_total_bonus = kill_bonus + time_bonus + no_dmg_bonus + combo_bonus
        self.world.player.score += self.clear_total_bonus

        # Achievement + persistence
        self.world.achievements.on_stage_clear()
        self.save.unlocked = sorted(self.world.achievements.unlocked)
        self.save.highest_cleared_stage = max(self.save.highest_cleared_stage, self.stage_idx)
        persistence.save(self.save)
        # Transition to summary screen; advance world after player dismisses.
        self.pending_stage_idx = self.stage_idx + 1
        self.clear_anim_frame = 0
        self.state = GameState.STAGE_CLEAR

    def commit_stage_advance(self) -> None:
        """Called when the player dismisses the STAGE_CLEAR summary."""
        assert self.world is not None
        # Treat Penguin (stage 6) as the natural campaign end. Everything past
        # that (Batcave, etc.) is endgame content that doesn't auto-advance.
        if self.stage_idx == 6 or self.pending_stage_idx >= len(STAGES):
            self.save.beat_game = True
            self.save.batcave_unlocked = True
            persistence.save(self.save)
            self.state = GameState.VICTORY
            music.stop()
            return
        self.stage_idx = self.pending_stage_idx
        prev_tracker = self.world.achievements
        self.world = self._make_world(carry=self.world.player, carry_tracker=prev_tracker)
        self.world.achievements.reset_for_stage(self.world.player.hp)
        self.state = GameState.LEVEL_INTRO
        self.intro_timer = 180
        music.play_stage(self.stage_idx)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            persistence.save(self.save)
            return False
        if event.type == pygame.VIDEORESIZE:
            # Re-create screen at new size (preserves RESIZABLE flag).
            self.screen = pygame.display.set_mode(
                (event.w, event.h), pygame.RESIZABLE,
            )
            return True
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
        # Global screenshot hotkey (works in any state)
        if event.key == pygame.K_F12:
            _save_screenshot(self.canvas)
            return True

        match self.state:
            case GameState.TITLE:
                items = self._title_items()
                if event.key in {pygame.K_UP, pygame.K_w}:
                    self.title_cursor = (self.title_cursor - 1) % len(items)
                elif event.key in {pygame.K_DOWN, pygame.K_s}:
                    self.title_cursor = (self.title_cursor + 1) % len(items)
                elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self._title_select(items[self.title_cursor])
                elif event.key == pygame.K_h:
                    self.state = GameState.HIGH_SCORES
                elif event.key == pygame.K_ESCAPE:
                    persistence.save(self.save)
                    return False
            case GameState.HIGH_SCORES:
                if event.key in {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self.state = GameState.TITLE
            case GameState.STAGE_CLEAR:
                if event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE}:
                    self.commit_stage_advance()
            case GameState.LEVEL_INTRO:
                # Skip intro with any key (after a brief minimum read time).
                if self.intro_timer < 150:  # require at least 30 frames of view
                    self.intro_timer = 0
                    self.state = GameState.PLAYING
            case GameState.SETTINGS:
                self._handle_settings_key(event)
            case GameState.STAGE_SELECT:
                self._handle_stage_select_key(event)
            case GameState.PAUSE_CONTROLS:
                if event.key in {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER}:
                    self.state = GameState.PAUSED
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
                            self.world.batarangs_used += 1
                            # Launch FX so player can see the throw register.
                            self.world.particles.emit(
                                bat.x, bat.y,
                                count=10, speed=2.2, life=10,
                                color=PALETTE["yellow"],
                            )
                            self.world.shake.kick(1.5)
                    case pygame.K_DOWN | pygame.K_s:
                        p.try_slide()
            case GameState.PAUSED:
                if event.key in {pygame.K_UP, pygame.K_w}:
                    self.pause_cursor = (self.pause_cursor - 1) % 5
                elif event.key in {pygame.K_DOWN, pygame.K_s}:
                    self.pause_cursor = (self.pause_cursor + 1) % 5
                elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
                    if self.pause_cursor == 0:
                        self.state = GameState.PLAYING
                    elif self.pause_cursor == 1:
                        self.state = GameState.PAUSE_CONTROLS
                    elif self.pause_cursor == 2:  # quit to title
                        self._record_score()
                        music.stop()
                        self.state = GameState.TITLE
                    elif self.pause_cursor == 3:
                        self.save.sfx_volume = round((self.save.sfx_volume + 0.25) % 1.25, 2)
                        audio.set_sfx_volume(self.save.sfx_volume)
                        persistence.save(self.save)
                    elif self.pause_cursor == 4:
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

    def _handle_settings_key(self, event: pygame.event.Event) -> None:
        n = 7
        if event.key in {pygame.K_UP, pygame.K_w}:
            self.settings_cursor = (self.settings_cursor - 1) % n
        elif event.key in {pygame.K_DOWN, pygame.K_s}:
            self.settings_cursor = (self.settings_cursor + 1) % n
        elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_RIGHT}:
            match self.settings_cursor:
                case 0:  # difficulty cycle
                    diffs = ["easy", "normal", "hard"]
                    i = (diffs.index(self.save.difficulty) + 1) % 3
                    self.save.difficulty = diffs[i]
                case 1:  # SFX
                    self.save.sfx_volume = round((self.save.sfx_volume + 0.25) % 1.25, 2)
                    audio.set_sfx_volume(self.save.sfx_volume)
                case 2:  # Music
                    self.save.music_volume = round((self.save.music_volume + 0.25) % 1.25, 2)
                    music.set_volume(self.save.music_volume)
                case 3:  # Show FPS
                    self.save.show_fps = not self.save.show_fps
                case 4:  # Language
                    self.save.language = "es" if self.save.language == "en" else "en"
                    i18n.set_language(self.save.language)
                case 5:  # Reset high scores
                    self.save.high_scores = []
                case 6:  # Back
                    self.state = GameState.TITLE
            persistence.save(self.save)
        elif event.key == pygame.K_ESCAPE:
            self.state = GameState.TITLE

    def _handle_stage_select_key(self, event: pygame.event.Event) -> None:
        last = len(STAGES) - 1
        max_unlocked = (self.save.highest_cleared_stage + 1) if not self.save.beat_game else last
        if event.key in {pygame.K_UP, pygame.K_w}:
            self.stage_select_cursor = max(0, self.stage_select_cursor - 1)
        elif event.key in {pygame.K_DOWN, pygame.K_s}:
            self.stage_select_cursor = min(last, self.stage_select_cursor + 1)
        elif event.key in {pygame.K_RETURN, pygame.K_KP_ENTER}:
            if self.stage_select_cursor <= max_unlocked:
                self.new_run(starting_stage=self.stage_select_cursor)
        elif event.key == pygame.K_ESCAPE:
            self.state = GameState.TITLE

    def _tutorial_tick(self) -> None:
        """Step through inline prompts the first time a player runs the game."""
        assert self.world is not None
        steps = [
            ("USE ARROWS / WASD TO MOVE",   240),
            ("PRESS SPACE TO JUMP",         240),
            ("PRESS Z TO PUNCH NEAR ENEMIES", 999),  # waits for first enemy nearby
            ("HOLD SHIFT TO RUN",           240),
            ("PRESS C TO THROW A BATARANG", 240),
        ]
        if self.tutorial_step >= len(steps):
            self.save.tutorial_seen = True
            persistence.save(self.save)
            self.tutorial_active = False
            return
        text, _ = steps[self.tutorial_step]
        self.tutorial_text = text
        self.tutorial_timer += 1
        # Step 2 (PUNCH near enemies) waits until an enemy is on-screen
        # within 80 px of player.
        if self.tutorial_step == 2:
            p = self.world.player
            for e in self.world.enemies:
                if e.alive and not e.is_dying and abs(e.x - p.x) < 80:
                    self.tutorial_seen_first_enemy = True
                    break
            if self.tutorial_seen_first_enemy and self.world.player.combo > 0:
                self.tutorial_step += 1
                self.tutorial_timer = 0
            return
        if self.tutorial_timer >= steps[self.tutorial_step][1]:
            self.tutorial_step += 1
            self.tutorial_timer = 0

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
            case GameState.STAGE_CLEAR:
                self.clear_anim_frame += 1
            case GameState.PLAYING if self.world is not None:
                _update_world(self.world, keys)
                w = self.world
                if self.tutorial_active:
                    self._tutorial_tick()
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
                            music.stop()
                else:
                    midboss_required = w.level.stage.midboss_kind is not None
                    midboss_done = w.midboss_defeated or not midboss_required
                    if midboss_done and w.player.x >= w.level.width_px - NATIVE_W // 2:
                        self.advance_stage()
            case _:
                pass

    def draw(self) -> None:
        c = self.canvas
        match self.state:
            case GameState.TITLE:
                _draw_title(c, self.blink)
                _draw_title_menu(c, self._title_items(), self.title_cursor)
                if self.save.high_scores:
                    draw_text(c, f"BEST {self.save.high_scores[0]:06d}", 4, 4, PALETTE["yellow"])
            case GameState.HIGH_SCORES:
                _draw_high_scores(c, self.save.high_scores)
            case GameState.SETTINGS:
                _draw_title(c, self.blink)
                _draw_settings(c, self.save, self.settings_cursor)
            case GameState.STAGE_SELECT:
                _draw_title(c, self.blink)
                _draw_stage_select(c, self.save, self.stage_select_cursor)
            case GameState.LEVEL_INTRO if self.world is not None:
                _draw_intro(c, self.world.level, self.blink, self.stage_idx)
            case GameState.STAGE_CLEAR if self.world is not None:
                _draw_stage_clear(
                    c, self.stage_idx,
                    self.clear_kills, self.clear_time_frames,
                    self.clear_no_damage, self.clear_combo_max,
                    self.clear_total_bonus, self.clear_anim_frame,
                )
            case GameState.PLAYING if self.world is not None:
                _draw_world(c, self.world)
                if self.tutorial_active and self.tutorial_text:
                    _draw_tutorial(c, self.tutorial_text, self.blink)
            case GameState.PAUSED if self.world is not None:
                _draw_world(c, self.world)
                _draw_pause(c, self.pause_cursor, self.save.sfx_volume, self.save.music_volume)
            case GameState.PAUSE_CONTROLS if self.world is not None:
                _draw_world(c, self.world)
                _draw_controls_screen(c)
            case GameState.GAME_OVER if self.world is not None:
                _draw_world(c, self.world)
                _draw_game_over(c, self.world, self.blink)
            case GameState.VICTORY if self.world is not None:
                _draw_world(c, self.world)
                _draw_victory(c, self.world, self.blink)
        # FPS overlay
        if self.save.show_fps:
            draw_text(c, f"{int(self.clock.get_fps())} FPS", NATIVE_W - 40, 4, PALETTE["green"])

        # Apply screen shake during gameplay (post-draw)
        ox, oy = (0, 0)
        if self.state is GameState.PLAYING and self.world is not None:
            ox, oy = self.world.shake.update()
        # Letterbox to current window size while preserving 320x224 aspect.
        sw, sh = self.screen.get_size()
        ratio = min(sw / NATIVE_W, sh / NATIVE_H)
        scaled_w = int(NATIVE_W * ratio)
        scaled_h = int(NATIVE_H * ratio)
        scaled = pygame.transform.scale(c, (scaled_w, scaled_h))
        self.screen.fill((0, 0, 0))
        offset_x = (sw - scaled_w) // 2 + int(ox * ratio)
        offset_y = (sh - scaled_h) // 2 + int(oy * ratio)
        self.screen.blit(scaled, (offset_x, offset_y))
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


def _save_screenshot(canvas: pygame.Surface) -> None:
    """Save the current 320x224 canvas to ~/batman-returns-screenshots/<ts>.png."""
    import os
    import time
    folder = os.path.expanduser("~/batman-returns-screenshots")
    try:
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"shot-{int(time.time())}.png")
        pygame.image.save(canvas, path)
    except OSError:
        pass


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
    """Wraps pygame.key.get_pressed() with extra virtual-press flags from gamepad.

    Implements the subset of ScancodeWrapper that the game actually uses
    (item access, length, iteration, contains).
    """
    __slots__ = ("_real", "_extra")

    def __init__(self, real: pygame.key.ScancodeWrapper, extra: dict[int, bool]):
        self._real = real
        self._extra = extra

    def __getitem__(self, key: int) -> bool:
        return bool(self._real[key]) or bool(self._extra.get(key))

    def __len__(self) -> int:
        return len(self._real)

    def __iter__(self):
        # pygame.key.ScancodeWrapper isn't iterable; expose indices instead.
        return iter(range(len(self._real)))

    def __contains__(self, key: int) -> bool:
        return bool(self._real[key]) or bool(self._extra.get(key))


def create_game() -> Game:
    audio.init()
    pygame.init()
    pygame.joystick.init()
    pygame.display.set_caption("Batman Returns — Python Homage")
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H), pygame.RESIZABLE)
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
    i18n.set_language(g.save.language)
    return g
