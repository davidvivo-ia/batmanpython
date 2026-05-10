"""Achievements: unlockable badges with toast notifications.

Tracks progress in-memory; unlocks persist via persistence.SaveData.unlocked.
Each achievement is just a key + display name; predicates live in ``check()``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Final

ACHIEVEMENTS: Final[dict[str, str]] = {
    "first_blood":   "FIRST BLOOD",
    "combo_5":       "COMBO MASTER",
    "combo_10":      "BRUTAL COMBO",
    "no_damage":     "UNTOUCHABLE",       # finish a stage without taking damage
    "boss_joker":    "JOKER'S OUT",
    "boss_catwoman": "CAT-NAPPED",
    "boss_penguin":  "GOTHAM SAVED",
    "score_10k":     "PYRRHIC HERO",
    "batarang_kill": "DARK KNIGHT",       # kill an enemy with batarang
    "fall_kill":     "GRAVITY ASSISTS",   # land a dive-kick kill
}


@dataclass(slots=True)
class Toast:
    text: str
    life: int = 180
    alive: bool = True


@dataclass(slots=True)
class AchievementTracker:
    unlocked: set[str] = field(default_factory=set)
    toasts: deque[Toast] = field(default_factory=deque)
    stage_damage_taken: int = 0
    stage_started_hp: int = 100

    def reset_for_stage(self, hp: int) -> None:
        self.stage_damage_taken = 0
        self.stage_started_hp = hp

    def unlock(self, key: str) -> None:
        if key in self.unlocked:
            return
        self.unlocked.add(key)
        self.toasts.append(Toast(text=ACHIEVEMENTS.get(key, key.upper())))

    def update(self) -> None:
        for t in self.toasts:
            t.life -= 1
            if t.life <= 0:
                t.alive = False
        while self.toasts and not self.toasts[0].alive:
            self.toasts.popleft()

    # Predicates --------------------------------------------------------
    def on_kill(self, was_batarang: bool, was_divekick: bool) -> None:
        self.unlock("first_blood")
        if was_batarang:
            self.unlock("batarang_kill")
        if was_divekick:
            self.unlock("fall_kill")

    def on_combo(self, combo: int) -> None:
        if combo >= 5:
            self.unlock("combo_5")
        if combo >= 10:
            self.unlock("combo_10")

    def on_boss_killed(self, key: str) -> None:
        self.unlock(key)

    def on_score(self, score: int) -> None:
        if score >= 10_000:
            self.unlock("score_10k")

    def on_damage(self, dmg: int) -> None:
        self.stage_damage_taken += dmg

    def on_stage_clear(self) -> None:
        if self.stage_damage_taken == 0:
            self.unlock("no_damage")
