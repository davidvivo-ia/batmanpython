"""HUD: bottom panel with lives, score, health bar, batarang count.

Echoes PANEL.EQU's "4-row info panel". We use a chunky bitmap font drawn from
small grids so we don't need TTF support.
"""

from __future__ import annotations

import pygame

from .constants import NATIVE_H, NATIVE_W, PALETTE, PLAYER_MAX_HP
from .entities import Player

# 5x7 bitmap font (caps, digits, a few symbols)
_FONT: dict[str, list[str]] = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
    ".": ["00000", "00000", "00000", "00000", "00000", "00100", "00100"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "'": ["00100", "00100", "00100", "00000", "00000", "00000", "00000"],
    "!": ["00100", "00100", "00100", "00100", "00000", "00000", "00100"],
    "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
    ":": ["00000", "00100", "00100", "00000", "00100", "00100", "00000"],
    "x": ["00000", "00000", "10001", "01010", "00100", "01010", "10001"],
}


def draw_text(
    surf: pygame.Surface,
    text: str,
    x: int,
    y: int,
    color: tuple[int, int, int] = PALETTE["white"],
    scale: int = 1,
    shadow: bool = True,
) -> None:
    cx = x
    for ch in text.upper() if ch_is_letter_safe(text) else text:
        glyph = _FONT.get(ch, _FONT[" "])
        for gy, row in enumerate(glyph):
            for gx, c in enumerate(row):
                if c == "1":
                    px, py = cx + gx * scale, y + gy * scale
                    if shadow:
                        pygame.draw.rect(surf, PALETTE["shadow"], (px + 1, py + 1, scale, scale))
                    pygame.draw.rect(surf, color, (px, py, scale, scale))
        cx += 6 * scale


def ch_is_letter_safe(_text: str) -> bool:
    # Always uppercase: our font only has caps + digits + a few symbols.
    return True


def draw_progress_bar(
    surf: pygame.Surface,
    progress: float,
    midboss_marker: float | None,
    midboss_alive: bool,
) -> None:
    """Thin horizontal bar showing camera progress through the stage."""
    bar_x, bar_y, bar_w, bar_h = 80, 14, 160, 3
    pygame.draw.rect(surf, PALETTE["dark"], (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2))
    fill = max(0.0, min(1.0, progress))
    fill_color = PALETTE["yellow"] if fill > 0.7 else PALETTE["purple"]
    pygame.draw.rect(surf, fill_color, (bar_x, bar_y, int(bar_w * fill), bar_h))
    if midboss_marker is not None:
        mx = bar_x + int(bar_w * midboss_marker)
        # Red dot if midboss still alive, green if defeated.
        col = PALETTE["red"] if midboss_alive else PALETTE["green"]
        pygame.draw.rect(surf, col, (mx - 1, bar_y - 1, 3, bar_h + 2))
    # Bat icon at the far right (the goal)
    pygame.draw.rect(surf, PALETTE["yellow"], (bar_x + bar_w - 2, bar_y - 2, 4, bar_h + 4))


def draw_objective(surf: pygame.Surface, text: str) -> None:
    """Top-centre objective text under the progress bar."""
    x = NATIVE_W // 2 - len(text) * 3
    draw_text(surf, text, x, 22, PALETTE["white"])


def draw_goal_arrow(surf: pygame.Surface, frame: int) -> None:
    """Pulsing GOAL chevron on the right edge during the last screen of a stage."""
    pulse = (frame // 15) % 2
    offset = 0 if pulse == 0 else 2
    x = NATIVE_W - 40 - offset
    y = NATIVE_H // 2 - 10
    pygame.draw.polygon(surf, PALETTE["yellow"], [(x, y), (x + 12, y + 8), (x, y + 16)])
    pygame.draw.polygon(surf, PALETTE["black"], [(x + 2, y + 4), (x + 8, y + 8), (x + 2, y + 12)])
    draw_text(surf, "GOAL", x - 30, y + 4, PALETTE["yellow"])


def draw_warning_banner(surf: pygame.Surface, text: str, frames_left: int) -> None:
    """Full-width red/yellow striped warning."""
    if frames_left <= 0:
        return
    y = NATIVE_H // 2 - 14
    # Striped background
    for i in range(0, NATIVE_W, 8):
        c = PALETTE["red"] if (i // 8 + frames_left // 4) % 2 == 0 else PALETTE["yellow"]
        pygame.draw.rect(surf, c, (i, y - 2, 8, 28))
    pygame.draw.rect(surf, PALETTE["black"], (4, y, NATIVE_W - 8, 24))
    # Text — flicker on/off
    if frames_left % 8 < 6:
        text_x = NATIVE_W // 2 - len(text) * 6
        draw_text(surf, text, text_x, y + 5, PALETTE["yellow"], scale=2)


def draw_hud(surf: pygame.Surface, player: Player, stage_name: str, objective: str = "") -> None:
    panel_h = 24
    pygame.draw.rect(surf, PALETTE["black"], (0, NATIVE_H - panel_h, NATIVE_W, panel_h))
    pygame.draw.line(surf, PALETTE["purple"], (0, NATIVE_H - panel_h), (NATIVE_W, NATIVE_H - panel_h))

    # Score
    draw_text(surf, f"SCORE {player.score:06d}", 4, NATIVE_H - panel_h + 4)
    # Lives
    draw_text(surf, f"x{player.lives}", 130, NATIVE_H - panel_h + 4, PALETTE["yellow"])
    pygame.draw.rect(surf, PALETTE["yellow"], (118, NATIVE_H - panel_h + 4, 6, 6))
    pygame.draw.rect(surf, PALETTE["black"], (119, NATIVE_H - panel_h + 5, 4, 1))

    # Batarangs — show key hint + flash on use so the player learns the binding.
    bat_x = 152
    bat_y = NATIVE_H - panel_h + 4
    if player.last_throw_flash > 0:
        # Pulsing yellow halo behind the counter
        pygame.draw.rect(surf, PALETTE["yellow"], (bat_x - 2, bat_y - 2, 70, 11))
        pygame.draw.rect(surf, PALETTE["black"], (bat_x - 1, bat_y - 1, 68, 9))
    bat_color = PALETTE["yellow"] if player.batarangs > 0 else PALETTE["gray"]
    draw_text(surf, f"[C]BAT x{player.batarangs}", bat_x, bat_y, bat_color)

    # Health bar
    bar_x, bar_y, bar_w, bar_h = NATIVE_W - 80, NATIVE_H - panel_h + 6, 70, 10
    pygame.draw.rect(surf, PALETTE["dark"], (bar_x - 1, bar_y - 1, bar_w + 2, bar_h + 2))
    ratio = max(0.0, player.hp / PLAYER_MAX_HP)
    color = PALETTE["green"] if ratio > 0.5 else PALETTE["yellow"] if ratio > 0.25 else PALETTE["red"]
    pygame.draw.rect(surf, color, (bar_x, bar_y, int(bar_w * ratio), bar_h))
    pygame.draw.rect(surf, PALETTE["white"], (bar_x, bar_y, bar_w, bar_h), 1)

    # Stage name top
    draw_text(surf, stage_name, 4, 4, PALETTE["yellow"])

    # Objective text under the progress bar (if provided)
    if objective:
        draw_objective(surf, objective)

    # Combo indicator
    if player.combo >= 2:
        ratio = player.combo_timer / 90 if player.combo_timer else 0
        draw_text(surf, f"COMBO x{player.combo}", NATIVE_W - 80, 4, PALETTE["orange"])
        pygame.draw.rect(surf, PALETTE["dark"], (NATIVE_W - 80, 14, 60, 3))
        pygame.draw.rect(surf, PALETTE["orange"], (NATIVE_W - 80, 14, int(60 * ratio), 3))
