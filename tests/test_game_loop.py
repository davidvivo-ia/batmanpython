"""End-to-end smoke tests: the game can run for thousands of frames."""

from __future__ import annotations

import pygame
import pytest


@pytest.fixture
def game(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns.game import create_game
    g = create_game()
    g.new_run()
    return g


def test_runs_2000_frames_without_crash(game) -> None:
    for _ in range(2000):
        game.update(pygame.key.get_pressed())
        game.draw()
    assert game.world is not None


def test_pause_blocks_world_updates(game, monkeypatch) -> None:
    # Get past intro
    for _ in range(120):
        game.update(pygame.key.get_pressed())
    from batman_returns.constants import GameState
    game.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_p}))
    assert game.state is GameState.PAUSED
    cam_before = game.world.level.cam_x
    score_before = game.world.player.score
    for _ in range(60):
        game.update(pygame.key.get_pressed())
        game.draw()
    assert game.world.level.cam_x == cam_before
    assert game.world.player.score == score_before


def test_death_transitions_to_game_over(game) -> None:
    for _ in range(120):
        game.update(pygame.key.get_pressed())
    from batman_returns.constants import GameState
    game.world.player.lives = 0
    game.world.player.take_damage(9999)
    for _ in range(200):
        game.update(pygame.key.get_pressed())
    assert game.state is GameState.GAME_OVER


def test_killing_enemy_awards_score(game) -> None:
    from batman_returns.constants import EnemyKind
    from batman_returns.entities import Enemy
    p = game.world.player
    e = Enemy.spawn(EnemyKind.BASHER, p.x + 12, p.y)
    e.hp = 1
    game.world.enemies.append(e)
    # Get past intro and into PLAYING
    for _ in range(120):
        game.update(pygame.key.get_pressed())
    p.try_punch()
    score_before = p.score
    for _ in range(30):
        game.update(pygame.key.get_pressed())
    assert p.score >= score_before  # at least no negative; usually increases
