"""Level: stage definitions, platform geometry, deterministic generation."""

from __future__ import annotations

from batman_returns.constants import NATIVE_W, TILE_SIZE
from batman_returns.level import STAGES, Level


def test_three_stages_with_expected_metadata() -> None:
    assert len(STAGES) == 3
    assert STAGES[0].midboss_kind == "midboss_joker"
    assert STAGES[1].midboss_kind == "midboss_catwoman"
    assert STAGES[2].boss is True


def test_platform_top_below_returns_top_when_falling_through() -> None:
    lvl = Level(STAGES[0])
    assert lvl.platforms, "stage 0 should have platforms"
    plat = lvl.platforms[0]
    x = plat.x + plat.w / 2
    # foot moves from above to below the top of the platform
    top = lvl.platform_top_below(x, plat.y + 1, plat.y - 5)
    assert top == plat.y


def test_platform_top_below_returns_none_when_rising() -> None:
    lvl = Level(STAGES[0])
    plat = lvl.platforms[0]
    x = plat.x + plat.w / 2
    assert lvl.platform_top_below(x, plat.y - 5, plat.y + 1) is None


def test_camera_clamps_to_world_bounds() -> None:
    lvl = Level(STAGES[0])
    lvl.update(target_cam_x=-1000, dt=1.0)
    assert lvl.cam_x >= 0
    lvl.update(target_cam_x=10**9, dt=1.0)
    assert lvl.cam_x <= lvl.width_px - NATIVE_W


def test_world_to_screen_translates_by_camera() -> None:
    lvl = Level(STAGES[0])
    lvl.cam_x = 100
    assert lvl.world_to_screen(150) == 50


def test_stage_widths_use_tile_units() -> None:
    for s in STAGES:
        lvl = Level(s)
        assert lvl.width_px == s.length_tiles * TILE_SIZE
