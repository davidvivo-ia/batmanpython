"""Combat math: combo bonus, damage, score scaling, hitbox geometry."""

from __future__ import annotations

from batman_returns.constants import (
    COMBO_DAMAGE_BONUS,
    COMBO_SCORE_BONUS,
    PUNCH_DAMAGE,
    SCORE_ENEMY,
    EnemyKind,
    Facing,
    PlayerState,
)
from batman_returns.entities import Enemy, Hitbox, Player


def test_punch_damage_scales_with_combo() -> None:
    p = Player(x=0)
    p.state = PlayerState.PUNCH
    assert p.attack_damage == PUNCH_DAMAGE
    p.combo = 3
    assert p.attack_damage == int(PUNCH_DAMAGE * (1 + 3 * COMBO_DAMAGE_BONUS))


def test_combo_score_bonus_grows_linearly() -> None:
    p = Player(x=0)
    p.combo = 4
    assert p.combo_score_bonus(SCORE_ENEMY) == int(SCORE_ENEMY * (1 + 4 * COMBO_SCORE_BONUS))


def test_register_combo_hit_resets_window() -> None:
    p = Player(x=0)
    p.combo_timer = 1
    p.register_combo_hit()
    assert p.combo == 1
    assert p.combo_timer > 1


def test_hitbox_intersection_is_aabb() -> None:
    a = Hitbox(0, 0, 10, 10)
    b = Hitbox(5, 5, 10, 10)
    c = Hitbox(20, 20, 5, 5)
    assert a.intersects(b)
    assert not a.intersects(c)


def test_attack_hitbox_facing() -> None:
    p = Player(x=100)
    p.state = PlayerState.PUNCH
    p.facing = Facing.RIGHT
    hb_r = p.attack_hitbox
    p.facing = Facing.LEFT
    hb_l = p.attack_hitbox
    assert hb_r is not None and hb_l is not None
    assert hb_r.x > hb_l.x  # right-facing hitbox sits right of left-facing one


def test_enemy_take_damage_reports_kill() -> None:
    e = Enemy.spawn(EnemyKind.BASHER, 0, 0)
    assert not e.take_damage(10)
    assert e.iframes > 0
    e.iframes = 0  # bypass i-frames for the kill check
    assert e.take_damage(9999)
    assert not e.alive


def test_player_iframes_block_repeat_damage() -> None:
    p = Player(x=0)
    initial = p.hp
    p.take_damage(20)
    after_first = p.hp
    p.take_damage(20)  # should be blocked by i-frames
    assert p.hp == after_first
    assert after_first == initial - 20


def test_extra_life_at_score_threshold() -> None:
    p = Player(x=0, lives=1, next_extra_life=1000)
    p.add_score(999)
    assert p.lives == 1
    p.add_score(2)
    assert p.lives == 2
    assert p.next_extra_life == 21000
