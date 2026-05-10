# Batman Returns — Python Homage

A modern, asset-free Python remake inspired by the **1992 Sega CD _Batman Returns_**
beat-'em-up sections. Built from a structural analysis of the retail 68000 ASM
source code released at
[`RetailGameSourceCode/BatmanReturns`](https://github.com/RetailGameSourceCode/BatmanReturns),
plus the unofficial [Atari 2600 prototype](https://github.com/arthurealike/batman2600)
for the minimal scrolling-jump loop.

> No original code or art is reused. Constants (16×16 tiles, score economy, enemy
> roster) come from `BATMAN.EQU`/`TECH.DOC`/`PANEL.EQU` and the LEVEL_1 module
> filenames. All sprites and SFX are generated procedurally at runtime.

## What got ported, conceptually

| Original (68000 ASM)            | This Python port                              |
|---------------------------------|-----------------------------------------------|
| `BATMAN.EQU` constants          | `constants.py` (`PUNCH_DAMAGE`, score table…) |
| `BASHER.68K` clown thug         | `EnemyKind.BASHER`                            |
| `JACKNBOX.68K` pop-up           | `EnemyKind.JACKBOX`                           |
| `FIRETRUC.68K` + `MINIFIRE.68K` | `EnemyKind.FIREBREATHER`                      |
| `VILLAN.68K` final boss         | `EnemyKind.BOSS_PENGUIN`                      |
| `PANEL.EQU` 4-row HUD           | `hud.py` bottom panel + bitmap font           |
| `OBJECT.68K` projectile pool    | `Batarang` / `EnemyProjectile` dataclasses    |
| 32×24 char playfield, 16×16     | `NATIVE_W=320`, `NATIVE_H=224`, `TILE_SIZE=16`|
| 96 maps per level (TECH.DOC)    | `Stage.length_tiles` (160/180/120 columns)    |
| `SFX_BDFIRE_A` etc.             | `audio.batarang()` / `punch()` / etc.         |
| Score: $500 enemy / $5000 boss  | `SCORE_ENEMY`, `SCORE_BOSS` (verbatim)        |

The driving stages from levels 4–5 (`CAR_CTRL.68K` / `SKI_CTRL.68K`) were
**deliberately omitted** to keep scope tight; pseudo-3D Batmobile chase is left
as a future addition.

## Modern Python (2026) features used

- **PEP 695 `type` aliases** (`type RGB = tuple[int, int, int]`) — `constants.py`
- **PEP 634 structural pattern matching** for state machines & sprite dispatch
- **`StrEnum` / `IntEnum` / `auto()`** for typed states
- **Slotted dataclasses** (`@dataclass(slots=True)`) for cache-friendly entities
- **`typing.Self`**, **PEP 604 `X | Y`**, **`from __future__ import annotations`**
- **`functools.cache`** for sprite-surface memoisation
- **`numpy`** for procedural ADSR/oscillator SFX synthesis
- **`pygame-ce`** (community edition) — actively maintained pygame fork
- Strict `ruff` lint config, hatchling build backend, Python `>=3.12`

## Run it

```bash
python -m pip install -e .
python -m batman_returns       # or just:  batman-returns
```

Requires Python ≥ 3.12 (3.13 recommended).

## Controls

| Key                | Action                |
|--------------------|-----------------------|
| ←/→ or A/D         | Walk                  |
| Shift              | Run (hold)            |
| Space / ↑ / W      | Jump                  |
| Z or J             | Punch (25 dmg)        |
| X or K             | Kick (35 dmg)         |
| C or L             | Throw Batarang (50 dmg, limited) |
| Enter              | Start / Retry         |
| Esc                | Pause to title / quit |

## Stages

1. **Gotham Streets** — clowns, knife-throwers
2. **Ice Plaza** — fire-breather clowns, jack-in-the-boxes (snow particles)
3. **Penguin's Lair** — boss arena: the Penguin paces and lobs knives

Score the original economy: small object 100, pickup 200, enemy 500, mid-boss
2 000, final boss 5 000. Extra life every 20 000 points.

## Project layout

```
src/batman_returns/
  __main__.py     # python -m entry
  game.py         # main loop, state machine, world container
  constants.py    # tunables (mostly from BATMAN.EQU)
  entities.py     # Player, Enemy, Batarang, EnemyProjectile, Pickup
  level.py        # Stage definitions, parallax, tilemap streamer
  sprites.py      # procedural pixel art (string-grid → Surface)
  hud.py          # bottom panel + 5×7 bitmap font
  audio.py        # numpy-synthesised SFX (punch, kick, batarang…)
```

## Notes for the curious

- The original Sega CD title ran the platforming stages on a **32×24 char
  playfield with a 4-row info panel** (`TECH.DOC`). I reduced the playfield to
  20×14 and put the panel inside that to fit a cleaner 320×224 → 960×672 window.
- The original targeted **20 fps** for the driving stages because of CD
  bandwidth; we run a smooth **60 fps** everywhere.
- Boss health bar is a modern affordance — the original Sega CD UI didn't show
  one, but in 2026 nobody wants to memorise Penguin HP.

## Why no BASIC?

The user's prompt asked specifically about a Spectrum-style 10-liner BASIC
Batman; none exists (probably DC licence reasons). This port instead studies
the *real* commercial ASM and brings its mechanics into modern Python. If
you wanted a 10-liner, that's a different (fun) project — start with a
4-direction sprite, two clown UDGs, and a single attack.

## Licence

MIT.
