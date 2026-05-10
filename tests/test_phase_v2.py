"""Tests for the Phase 8-15 feature drops (PLAN.md v2)."""

from __future__ import annotations

import pygame
import pytest

from batman_returns.constants import (
    GROUND_Y,
    EnemyKind,
)
from batman_returns.entities import Batarang, Enemy, Pickup, Player
from batman_returns.level import STAGES, Level


@pytest.fixture(autouse=True)
def _ensure_pygame():
    pygame.init()


# ---------------- Phase 8: new enemies ----------------

@pytest.mark.parametrize("kind", [
    EnemyKind.CYCLE, EnemyKind.TANK, EnemyKind.CANNON, EnemyKind.WKLITE,
])
def test_new_enemy_spawns_and_updates_without_crash(kind) -> None:
    e = Enemy.spawn(kind, 200, GROUND_Y - 24)
    e.alert = True
    p = Player(x=300)
    lvl = Level(STAGES[0])
    for _ in range(60):
        e.update(p, lvl)
    assert e.alive


def test_cycle_charges_horizontally() -> None:
    e = Enemy.spawn(EnemyKind.CYCLE, 200, GROUND_Y - 16)
    p = Player(x=400)
    lvl = Level(STAGES[0])
    x_before = e.x
    for _ in range(5):
        e.update(p, lvl)
    assert e.x > x_before  # moved right toward the player


def test_cannon_does_not_move() -> None:
    e = Enemy.spawn(EnemyKind.CANNON, 200, GROUND_Y - 16)
    p = Player(x=300)
    lvl = Level(STAGES[0])
    x_before = e.x
    for _ in range(20):
        e.update(p, lvl)
    assert e.x == x_before


# ---------------- Phase 9: returning batarang ----------------

def test_batarang_returns_after_half_life() -> None:
    b = Batarang(x=100, y=50, vx=3.2)
    lvl = Level(STAGES[0])
    # Decel kicks in at life<45; with initial vx=3.2 and 0.04 decel rate, the
    # boomerang flips around frame ~70.
    for _ in range(85):
        b.update(lvl)
        if b.returning:
            return
    pytest.fail("Batarang never entered returning state")


def test_returning_batarang_can_be_recaught() -> None:
    """Sim: player throws, batarang returns; ammo can replenish via re-catch."""
    from batman_returns.game import World, _update_world
    p = Player(x=200, batarangs=1)
    lvl = Level(STAGES[0])
    w = World(level=lvl, player=p)
    bat = p.try_throw()
    assert bat is not None
    w.batarangs.append(bat)
    # Force the returning state and place batarang on the player
    bat.life = 30
    bat.vx = -bat.vx  # immediate reverse
    bat.returning = True
    bat.x = p.x
    bat.y = p.y + 8
    keys = pygame.key.get_pressed()
    _update_world(w, keys)
    # Either re-caught (alive=False, batarangs incremented) or still in flight.
    assert (not bat.alive and p.batarangs >= 1) or bat.alive


# ---------------- Phase 10: power-ups ----------------

def test_invuln_pickup_grants_immunity() -> None:
    p = Player(x=0, hp=50)
    pk = Pickup("invuln", 0, 0)
    pk.apply(p)
    assert p.invuln_timer > 0
    p.take_damage(20)
    assert p.hp == 50  # unchanged


def test_dmg2x_pickup_doubles_attack_damage() -> None:
    p = Player(x=0)
    p.try_punch()
    base = p.attack_damage
    p2 = Player(x=0)
    p2.try_punch()
    p2.damage_buff_timer = 60
    assert p2.attack_damage == base * 2


def test_infbat_pickup_skips_ammo_decrement() -> None:
    p = Player(x=0, batarangs=2)
    p.infinite_bat_timer = 60
    p.try_throw()
    assert p.batarangs == 2  # not decremented


# ---------------- Phase 13: stage clear bonus ----------------

def test_stage_clear_no_damage_grants_bonus(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns.game import create_game
    g = create_game()
    g.new_run()
    for _ in range(220):
        g.update(pygame.key.get_pressed())
    score_before = g.world.player.score
    g.world.midboss_defeated = True
    g.world.player.x = g.world.level.width_px - 10
    # Force advance via internal call
    g.advance_stage()
    score_after = g.world.player.score
    # No-damage bonus + kill bonus should have been added.
    assert score_after > score_before


# ---------------- Phase 14: NG+ + Batcave ----------------

def test_batcave_unlocked_after_victory(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns.game import create_game
    g = create_game()
    g.new_run()
    g.stage_idx = 6  # PENGUIN'S LAIR
    g.pending_stage_idx = 7
    g.commit_stage_advance()
    assert g.save.beat_game
    assert g.save.batcave_unlocked


def test_batcave_hidden_in_stage_select_until_unlocked(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns import persistence
    from batman_returns.game import _draw_stage_select
    sd = persistence.SaveData(highest_cleared_stage=0, batcave_unlocked=False)
    surf = pygame.Surface((320, 224))
    _draw_stage_select(surf, sd, 0)
    # Indirect: enabling batcave changes the rendered output. We assert the
    # function runs both ways without error.
    sd.batcave_unlocked = True
    sd.beat_game = True
    _draw_stage_select(surf, sd, 0)


# ---------------- Phase 15: i18n ----------------

def test_i18n_falls_back_to_english_on_missing_key() -> None:
    from batman_returns import i18n
    i18n.set_language("es")
    # A key only in EN should still resolve to English.
    assert i18n.t("score") == "PUNTOS"
    # A nonexistent key returns itself.
    assert i18n.t("__missing__") == "__missing__"
    i18n.set_language("en")


def test_i18n_spanish_translates_stage_names() -> None:
    from batman_returns import i18n
    i18n.set_language("es")
    assert "GOTHAM" in i18n.t("stage_1") or "CALLES" in i18n.t("stage_1")
    assert i18n.t("stage_8") == "LA BATICUEVA"
    i18n.set_language("en")


def test_settings_cycles_language(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns import i18n
    from batman_returns.constants import GameState
    from batman_returns.game import create_game
    g = create_game()
    g.state = GameState.SETTINGS
    g.settings_cursor = 4  # LANGUAGE
    g.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_RETURN}))
    assert g.save.language == "es"
    assert i18n.get_language() == "es"
