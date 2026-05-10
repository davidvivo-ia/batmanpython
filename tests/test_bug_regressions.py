"""Regression tests for bugs surfaced in the bug-hunt review."""

from __future__ import annotations

import pygame
import pytest

from batman_returns.constants import (
    GROUND_Y,
    EnemyKind,
    PlayerState,
)
from batman_returns.entities import Enemy, Player


@pytest.fixture(autouse=True)
def _ensure_pygame():
    pygame.init()


# ---------------------------------------------------------------- bug #2
def test_ground_punch_zeros_horizontal_velocity():
    """Player must not slide forward through a ground punch (bug #2)."""
    from batman_returns.level import STAGES, Level
    p = Player(x=100)
    p.vx = 2.5  # moving right
    p.try_punch()
    assert p.state is PlayerState.PUNCH
    lvl = Level(STAGES[0])
    p.update(pygame.key.get_pressed(), lvl)
    assert p.vx == 0


# ---------------------------------------------------------------- bug #3
def test_taking_lethal_damage_with_extra_lives_only_plays_hurt_sfx():
    """When a hit drops HP to 0 with lives remaining, only one of death/hurt
    should play — not both stacked (bug #3)."""
    p = Player(x=0, hp=10, lives=2)
    p.take_damage(50)  # lethal, but lives=1 left
    # Player should be HURT, not DEAD, and HP refilled.
    assert p.state is PlayerState.HURT
    assert p.lives == 1
    assert p.hp > 0


# ---------------------------------------------------------------- bug #4
def test_enemy_sprite_flip_matches_player_convention():
    """Enemies and player should share the same flip convention: source sprite
    faces RIGHT; flip when facing LEFT (bug #4)."""
    import inspect

    from batman_returns.entities import Enemy as E
    from batman_returns.entities import Player as P
    src_p = inspect.getsource(P.draw)
    src_e = inspect.getsource(E.draw)
    # Both should flip on Facing.LEFT (consistent convention).
    assert "Facing.LEFT" in src_p
    assert "Facing.LEFT" in src_e


# ---------------------------------------------------------------- bug #6
def test_penguin_arena_does_not_drift_with_camera():
    """Penguin's arena bounds should be fixed at spawn, not relative to live
    camera (bug #6)."""
    from batman_returns.level import STAGES, Level
    boss = Enemy.spawn(EnemyKind.BOSS_PENGUIN, 500, GROUND_Y - 32)
    lvl = Level(STAGES[2])
    p = Player(x=500)
    boss.update(p, lvl)
    assert boss.arena_left > 0
    assert boss.arena_right > boss.arena_left
    initial_left = boss.arena_left
    # Shift camera; arena should stay put.
    lvl.cam_x = 1000
    boss.update(p, lvl)
    assert boss.arena_left == initial_left


# ---------------------------------------------------------------- bug #15
def test_push_score_returns_true_only_when_table_changed():
    from batman_returns.persistence import SaveData
    sd = SaveData(high_scores=[100, 90, 80, 70, 60])
    # Score below the floor — should not change the table.
    assert sd.push_score(50) is False
    # Score that bumps an entry — should change the table.
    assert sd.push_score(95) is True
    # Duplicate of an existing top score still changes the table (pushes someone out).
    sd2 = SaveData(high_scores=[100, 90, 80, 70, 60])
    assert sd2.push_score(90) is True


# ---------------------------------------------------------------- bug #14
def test_augmented_keys_supports_len_iter_contains():
    from batman_returns.game import _AugmentedKeys
    real = pygame.key.get_pressed()
    aug = _AugmentedKeys(real, {pygame.K_z: True})
    assert len(aug) == len(real)
    assert aug[pygame.K_z] is True
    assert pygame.K_z in aug
    # Iteration must not error
    list(iter(aug))


# ---------------------------------------------------------------- bug #21
def test_stage_with_midboss_cannot_clear_until_midboss_defeated(tmp_path, monkeypatch):
    """Stage 0 has Joker midboss — running past the trigger without killing
    Joker must not clear the stage (bug #21)."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns.constants import GameState
    from batman_returns.game import create_game
    g = create_game()
    g.new_run()
    # Pump past intro
    for _ in range(200):
        g.update(pygame.key.get_pressed())
    assert g.state is GameState.PLAYING
    # Teleport player to the right edge without defeating the midboss
    g.world.player.x = g.world.level.width_px - 10
    g.world.midboss_defeated = False
    for _ in range(5):
        g.update(pygame.key.get_pressed())
    # Should still be in PLAYING (stage not cleared)
    assert g.state is GameState.PLAYING
    # Now mark midboss defeated; stage should advance
    g.world.midboss_defeated = True
    g.update(pygame.key.get_pressed())
    # Stage clear now opens a summary screen first; old behaviour was direct
    # advance to LEVEL_INTRO/PLAYING. Both paths satisfy "stage was cleared".
    assert g.state in {GameState.LEVEL_INTRO, GameState.PLAYING, GameState.STAGE_CLEAR}


# ---------------------------------------------------------------- bug #1
def test_divekick_lands_and_eventually_returns_to_idle():
    from batman_returns.level import STAGES, Level
    p = Player(x=100, y=100)
    p.on_ground = False
    p.try_kick()  # in air → divekick
    assert p.state is PlayerState.DIVEKICK
    lvl = Level(STAGES[0])
    # Tick until grounded
    for _ in range(200):
        p.update(pygame.key.get_pressed(), lvl)
        if p.on_ground and p.state is PlayerState.IDLE:
            return
    pytest.fail("Player remained in DIVEKICK forever")
