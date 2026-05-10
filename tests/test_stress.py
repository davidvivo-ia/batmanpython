"""Adversarial stress tests: try to break invariants by chaotic input."""

from __future__ import annotations

import random

import pygame
import pytest


@pytest.fixture
def game(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns.game import create_game
    g = create_game()
    g.new_run()
    return g


def _random_event(rng: random.Random) -> pygame.event.Event:
    keys = [
        pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN,
        pygame.K_SPACE, pygame.K_z, pygame.K_x, pygame.K_c,
        pygame.K_p, pygame.K_RETURN, pygame.K_LSHIFT,
    ]
    return pygame.event.Event(pygame.KEYDOWN, {"key": rng.choice(keys)})


def test_chaos_monkey_5000_frames(game) -> None:
    """Random input for 5000 frames must not crash."""
    rng = random.Random(42)
    for _ in range(5000):
        if rng.random() < 0.4:
            game.handle_event(_random_event(rng))
        game.update(pygame.key.get_pressed())
        game.draw()


def test_player_x_never_escapes_world(game) -> None:
    """No matter the input, player.x stays in level bounds."""
    rng = random.Random(7)
    for _ in range(800):
        game.handle_event(_random_event(rng))
        game.update(pygame.key.get_pressed())
        if game.world is None:
            return
        p = game.world.player
        assert 0 <= p.x <= game.world.level.width_px


def test_player_y_never_below_ground(game) -> None:
    from batman_returns.constants import GROUND_Y
    for _ in range(300):
        game.update(pygame.key.get_pressed())
    assert game.world.player.y <= GROUND_Y - 1


def test_batarang_inventory_never_negative(game) -> None:
    """Spamming throw must not let batarang count drop below 0."""
    p = game.world.player
    for _ in range(200):  # past intro
        game.update(pygame.key.get_pressed())
    for _ in range(100):
        p.try_throw()
    assert p.batarangs >= 0


def test_score_only_increases(game) -> None:
    p = game.world.player
    seen_scores = []
    for _ in range(400):
        game.update(pygame.key.get_pressed())
        seen_scores.append(p.score)
    for a, b in zip(seen_scores, seen_scores[1:], strict=False):
        assert b >= a


def test_enemy_projectile_pool_bounded_under_boss_phase3(game, monkeypatch) -> None:
    """Penguin phase-3 sustained fire shouldn't grow projectile list unboundedly
    over a reasonable window (projectiles must self-expire)."""
    from batman_returns.constants import GROUND_Y, EnemyKind
    from batman_returns.entities import Enemy
    boss = Enemy.spawn(EnemyKind.BOSS_PENGUIN, 200, GROUND_Y - 32)
    boss.hp = 50  # phase 3
    game.world.enemies.append(boss)
    for _ in range(300):
        game.update(pygame.key.get_pressed())
    # Should be high, but each projectile lives 140 frames; pool shouldn't
    # exceed a sane upper bound (cadence 28 frames * 3 spread * lifespan/cadence).
    assert len(game.world.enemy_shots) < 200


def test_pause_resume_preserves_game_state(game) -> None:
    from batman_returns.constants import GameState
    for _ in range(200):
        game.update(pygame.key.get_pressed())
    p = game.world.player
    cam = game.world.level.cam_x
    p_x = p.x
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_p}))
    assert game.state is GameState.PAUSED
    for _ in range(60):
        game.update(pygame.key.get_pressed())
        game.draw()
    assert p.x == p_x
    assert game.world.level.cam_x == cam


def test_jack_in_box_activates_only_in_proximity(game) -> None:
    from batman_returns.constants import GROUND_Y, EnemyKind
    from batman_returns.entities import Enemy
    e = Enemy.spawn(EnemyKind.JACKBOX, 1000, GROUND_Y - 24)  # far from player
    game.world.enemies.append(e)
    for _ in range(60):
        game.update(pygame.key.get_pressed())
    assert e.activated is False  # nobody nearby


def test_dead_player_eventually_triggers_game_over(game) -> None:
    from batman_returns.constants import GameState
    for _ in range(200):
        game.update(pygame.key.get_pressed())
    p = game.world.player
    p.lives = 0
    p.take_damage(9999)
    transitioned = False
    for _ in range(300):
        game.update(pygame.key.get_pressed())
        if game.state is GameState.GAME_OVER:
            transitioned = True
            break
    assert transitioned


def test_advance_to_victory(game) -> None:
    """Advance through all stages by setting boss_defeated; verify VICTORY.

    advance_stage() now opens a STAGE_CLEAR summary screen which the player
    dismisses via commit_stage_advance(). We tick a watchdog so this can't
    spin forever if the state machine drifts.
    """
    from batman_returns.constants import GameState
    safety = 50
    while game.state is not GameState.VICTORY and safety > 0:
        if game.state is GameState.STAGE_CLEAR:
            game.commit_stage_advance()
        elif game.state is GameState.LEVEL_INTRO:
            game.intro_timer = 0
            game.state = GameState.PLAYING
        elif game.state is GameState.PLAYING:
            game.world.boss_defeated = True
            game.advance_stage()
        else:
            game.update(pygame.key.get_pressed())
        safety -= 1
    assert game.state is GameState.VICTORY


def test_high_scores_persist_across_runs(game, tmp_path, monkeypatch) -> None:
    from batman_returns import persistence
    game.world.player.score = 5555
    game._record_score()
    # Reload save data fresh
    sd = persistence.load()
    assert 5555 in sd.high_scores
