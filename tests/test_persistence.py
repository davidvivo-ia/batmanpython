"""Persistence: save/load round-trip + high-score table size cap."""

from __future__ import annotations

from pathlib import Path

from batman_returns import persistence


def test_high_score_table_keeps_top_5(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(persistence, "CONFIG_PATH", tmp_path / "batman-returns-py" / "save.json")
    sd = persistence.SaveData()
    for s in [100, 5000, 200, 9999, 1, 7777, 3333, 4444]:
        sd.push_score(s)
    assert sd.high_scores == [9999, 7777, 5000, 4444, 3333]


def test_save_load_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setattr(persistence, "CONFIG_PATH", tmp_path / "batman-returns-py" / "save.json")
    a = persistence.SaveData(high_scores=[1, 2, 3], music_volume=0.3, sfx_volume=0.9)
    persistence.save(a)
    b = persistence.load()
    assert b.high_scores == [1, 2, 3]
    assert b.music_volume == 0.3
    assert b.sfx_volume == 0.9


def test_load_missing_returns_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "fresh"))
    sd = persistence.load()
    assert sd.high_scores == []
    assert 0.0 <= sd.music_volume <= 1.0


def test_push_score_returns_true_when_in_table() -> None:
    sd = persistence.SaveData()
    assert sd.push_score(1000) is True
    sd.high_scores = [10_000, 9_000, 8_000, 7_000, 6_000]
    assert sd.push_score(500) is False
    assert sd.push_score(9_500) is True
