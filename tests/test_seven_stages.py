"""Tests for the 7-stage expansion and the hazard (pit/water) system."""

from __future__ import annotations

import pygame
import pytest

from batman_returns.constants import GROUND_Y
from batman_returns.entities import Player
from batman_returns.level import STAGES, Level


@pytest.fixture(autouse=True)
def _ensure_pygame():
    pygame.init()


def test_all_seven_stages_have_unique_names() -> None:
    names = [s.name for s in STAGES]
    assert len(set(names)) == 7
    assert "GOTHAM ROOFTOPS" in names
    assert "THE SEWERS" in names
    assert "HARBOR DOCKS" in names
    assert "ARKHAM ASYLUM" in names


def test_stages_with_hazards_generate_hazard_zones() -> None:
    for s in STAGES:
        if s.hazard_kind:
            lvl = Level(s)
            assert len(lvl.hazards) > 0, f"{s.name} should have hazards"
            # Every hazard must be inside the playable range
            for start, end in lvl.hazards:
                assert 0 < start <= end < s.length_tiles


def test_safe_stages_have_no_hazards() -> None:
    for s in STAGES:
        if not s.hazard_kind:
            lvl = Level(s)
            assert lvl.hazards == []


def test_is_hazard_at_returns_true_inside_zone() -> None:
    s = STAGES[1]  # GOTHAM ROOFTOPS — pits
    lvl = Level(s)
    assert lvl.hazards
    start, end = lvl.hazards[0]
    # Center of the hazard tile should report True
    middle_x = (start + 0.5) * 16
    assert lvl.is_hazard_at(middle_x)
    # Just outside should report False
    outside_x = (start - 1) * 16 + 8
    assert not lvl.is_hazard_at(outside_x)


def test_player_falling_into_pit_is_killed() -> None:
    s = STAGES[1]
    lvl = Level(s)
    p = Player(x=200, hp=100, lives=3)
    # Place player above a pit
    if lvl.hazards:
        start, _ = lvl.hazards[0]
        p.x = (start + 0.5) * 16
        p._last_safe_x = (start - 2) * 16
    initial_lives = p.lives
    # Simulate falling: drop player far below ground
    p.y = GROUND_Y + 200
    p.update(pygame.key.get_pressed(), lvl)
    # Either dead, or respawned at safe x with reduced lives
    assert p.lives < initial_lives or p.hp == 0 or p.x == p._last_safe_x


def test_player_on_safe_ground_is_not_in_hazard() -> None:
    s = STAGES[0]  # no hazards
    lvl = Level(s)
    p = Player(x=200)
    p.update(pygame.key.get_pressed(), lvl)
    assert not lvl.is_hazard_at(p.x)
    assert p.on_ground


def test_rescue_platforms_present_above_wide_pits() -> None:
    """Wide hazards should spawn a rescue platform so the gap is jumpable."""
    s = STAGES[1]  # rooftops — pits
    lvl = Level(s)
    # At least one platform should sit above a hazard zone, providing a recovery option.
    has_rescue = False
    for plat in lvl.platforms:
        center = plat.x + plat.w / 2
        if lvl.is_hazard_at(center) or lvl.is_hazard_at(plat.x):
            has_rescue = True
            break
    # Note: not strictly required if all hazards happened to be width 2, but
    # over the deterministic seed at least one wide hazard should appear.
    assert has_rescue or len([h for h in lvl.hazards if h[1] - h[0] >= 2]) == 0


def test_stage_select_unlocks_progressively(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns import persistence
    from batman_returns.game import create_game
    sd = persistence.SaveData(highest_cleared_stage=2)
    persistence.save(sd)
    g = create_game()
    items = g._title_items()
    assert "CONTINUE" in items
    assert "STAGE SELECT" in items


def test_continue_after_full_clear_does_not_offer(tmp_path, monkeypatch) -> None:
    """If the player beat the final stage, CONTINUE shouldn't appear (no further stage to resume)."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    from batman_returns import persistence
    from batman_returns.game import create_game
    sd = persistence.SaveData(highest_cleared_stage=len(STAGES) - 1, beat_game=True)
    persistence.save(sd)
    g = create_game()
    items = g._title_items()
    assert "CONTINUE" not in items
    assert "STAGE SELECT" in items
