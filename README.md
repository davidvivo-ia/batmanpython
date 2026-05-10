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

- **PEP 634 structural pattern matching** for state machines & sprite dispatch
- **`StrEnum` / `IntEnum` / `auto()`** for typed states
- **Slotted dataclasses** (`@dataclass(slots=True)`) for cache-friendly entities
- **`typing.Self`**, **PEP 604 `X | Y`**, **`from __future__ import annotations`**
- **`functools.cache`** for sprite-surface memoisation
- **`numpy`** for procedural ADSR/oscillator SFX synthesis
- **`pygame-ce`** (community edition) — actively maintained pygame fork
- Strict `ruff` lint config, hatchling build backend, Python `>=3.11`
- **GitHub Actions CI** matrix on Python 3.11 / 3.12 / 3.13 (ruff + pytest with SDL dummy drivers)

## Features beyond the original

### Combat
- **6 enemy archetypes** (basher, jack-in-the-box, fire-breather, knife-thrower, **skater clown** on Ice Plaza, plus 3 bosses)
- **Joker** (stage 1 midboss) + **Catwoman** (stage 2 midboss) + multi-phase **Penguin** with attack telegraphs and umbrella shield
- **Combo system** with named milestones (`DOUBLE`, `TRIPLE`, `MEGA COMBO!`, `INSANE!`, `UNSTOPPABLE!`) — boosts damage and score
- **Slide** (Down) with brief i-frames, **dive-kick** (Kick mid-air), **charged batarang** (hold C ≥0.75s, releases a piercing shot for free)
- **First-blood hit-stop** — extra freeze frames + banner on the first kill of a run
- **Smoke bomb** rare pickup wipes nearby enemies AOE
- **Patrol → chase AI** — enemies pace at spawn until alerted by proximity or being hit
- **Enemy death animation** — 18-frame squash + alpha fade

### UX visibility (addressing player feedback)
- **HUD batarang counter** shows `[C]BAT x5` with key hint and pulsing flash on use
- **Stage progress bar** at top of screen with red/green midboss marker and yellow goal flag
- **Goal flag** sprite at end of stages 1 and 2; boss arena for stage 3
- **Pulsing GOAL ▶ chevron** on the right edge during the last screen
- **Live objective text** under the progress bar (`DEFEAT JOKER`, `REACH THE FLAG ▶`, etc.)
- **Striped warning banner** before each midboss / boss spawn
- **Extended LEVEL_INTRO** (3 s) with full controls panel; skippable with any key
- **First-run tutorial** — inline prompts walk you through MOVE / JUMP / PUNCH / RUN / BATARANG; auto-disabled after first completion

### Visuals & audio
- **Procedural platforms** — one-way (top-only) AABB collision
- **Stage-specific platform sprites** — brick, ice block, lair stone
- **Foreground parallax** — lamp posts, icicles, lair pillars at 1.4× scroll
- **Particle FX** — 256-slot recycled pool: hit sparks, blood bursts, landing dust, pickup confetti, batarang launch flash
- **Screen shake + hit-freeze** for game-feel
- **Yellow afterimage trail** on every batarang
- **Floating score popups** ("+500", "MEGA COMBO!", "FIRST BLOOD!")
- **Weather** — rain + lightning + procedural thunder rumble in Gotham; snow particles in Ice Plaza
- **Procedural chiptune music** — square-lead + triangle-bass loops, one per stage

### Difficulty & progression
- **Three difficulties** (EASY / NORMAL / HARD) scaling enemy HP, contact damage, starting batarangs
- **Continue from cleared stage** offered on title screen if you've cleared at least one
- **Stage select** unlocked after first clear or in progress
- **Highest cleared stage** persisted to save data
- **10 achievements** with unlock toasts and persistence

### Quality of life
- **Pause menu** with `RESUME / CONTROLS / QUIT TO TITLE / SFX VOL / MUSIC VOL`
- **Settings screen** from title with `DIFFICULTY / SFX VOL / MUSIC VOL / SHOW FPS / RESET HIGH SCORES`
- **Resizable window** with letterboxed scaling (preserves 320×224 aspect)
- **F12 screenshot** to `~/batman-returns-screenshots/<ts>.png`
- **High-score persistence** in JSON (XDG/AppData/Application Support)
- **Gamepad support** — Xbox-style mapping, hot-plug, analog stick + dpad-hat

## Tests

```bash
pip install -e . pytest
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/ -q
```

58 tests covering combat math, persistence round-trip, level geometry, end-to-end smoke
runs, chaos-monkey input, regression tests for bugs caught in code review, and Phase 1–7
feature tests (HUD progression, tutorial activation, charged-batarang piercing, smoke-bomb
AOE, difficulty scaling, skater motion, Penguin shield window, enemy death animation,
settings reset, screenshot creation).

## Run it

```bash
python -m pip install -e .
python -m batman_returns       # or just:  batman-returns
```

Requires Python ≥ 3.11 (3.12 / 3.13 recommended).

## Controls

| Key                | Action                |
|--------------------|-----------------------|
| ←/→ or A/D         | Walk                  |
| Shift              | Run (hold)            |
| Space / ↑ / W      | Jump                  |
| ↓ or S             | Slide (low profile + brief i-frames) |
| Z or J             | Punch (25 dmg)        |
| X or K             | Kick (35 dmg) — **mid-air = dive-kick (50 dmg)** |
| C or L             | Throw Batarang (50 dmg, limited) |
| P or Esc           | Pause                 |
| Enter              | Start / Retry         |
| H (on title)       | High scores           |
| Gamepad            | A=jump, X=punch, Y=kick, B=batarang, LB/RB=slide, Start=pause |

## Stages

1. **Gotham Streets** — clowns, knife-throwers, **rain + lightning + thunder**, midboss **Joker** (3-card fan)
2. **Ice Plaza** — fire-breather clowns, jack-in-the-boxes, snow particles, midboss **Catwoman** (lunge + jump-over)
3. **Penguin's Lair** — final boss the **Penguin** in 3 phases (single shot → double + dive → triple spread)

Score the original economy: small object 100, pickup 200, enemy 500, mid-boss
2 000, final boss 5 000. Extra life every 20 000 points.

## Project layout

```
src/batman_returns/
  __main__.py        # python -m entry
  game.py            # main loop, state machine, world container
  constants.py       # tunables (mostly from BATMAN.EQU)
  entities.py        # Player, Enemy, Batarang, EnemyProjectile, Pickup
  level.py           # Stage defs, parallax, platforms, weather, tilemap streamer
  sprites.py         # procedural pixel art (string-grid → Surface)
  hud.py             # bottom panel + 5×7 bitmap font
  audio.py           # numpy-synthesised SFX (punch, kick, batarang…)
  music.py           # procedural chiptune loops (one per stage)
  effects.py         # particle pool, screen shake, hit-freeze, floating text
  achievements.py    # 10 unlockable badges + toast queue
  persistence.py     # save.json (XDG/AppData/Application Support)
  input.py           # gamepad helper layer (also baked into game.py dispatch)
tests/
  test_combat.py             # damage / score / hitbox / i-frames
  test_persistence.py        # save round-trip, top-5 cap
  test_level.py              # platform geometry, camera clamp
  test_game_loop.py          # 2000-frame headless smoke runs
  test_stress.py             # chaos-monkey input + invariants
  test_bug_regressions.py    # guards 8 specific bugs caught in review
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
