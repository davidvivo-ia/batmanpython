# PLAN.md — Improvement roadmap for Batman Returns (Python)

> Granular task list. Each item is self-contained: file paths, exact change,
> acceptance criterion. A sub-agent should be able to execute one task without
> reading the rest of the plan.

## Player feedback driving this round

- **"No veo cómo disparas"** — the user can't tell how to throw the batarang.
  Root cause: HUD shows just `BAT x5`, no key hint. Title-screen control
  reference is gone once you start. Batarang sprite is 10×9 px and travels at
  4.5 px/frame so it's easy to miss visually.
- **"Tampoco veo cómo pasar de nivel"** — the user can't tell how to advance.
  Root causes: stages are 2 560–2 880 px wide with no on-screen progress bar,
  no goal flag, no objective text. Stage-clear gating on midboss-defeat means
  hitting the right edge before killing the midboss silently does nothing.

## Implementation contract for any sub-agent picking up a task

Each task lists:
1. **Files** — exact paths to edit / create.
2. **Where** — function or section anchor.
3. **What** — the concrete change.
4. **Done when** — test name or visible behaviour.

If a task touches `entities.py` Player/Enemy state, also add a regression test
in `tests/test_bug_regressions.py` (or a new `tests/test_<feature>.py`).

Run `ruff check src tests && SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
pytest tests/ -q` after every task; both must pass.

---

## Phase 1 — Critical UX (player can actually play)

### 1.1 HUD: show key hint next to batarang counter

- **Files**: `src/batman_returns/hud.py`
- **Where**: `draw_hud()`
- **What**: replace `f"BAT x{player.batarangs}"` with `f"[C]BAT x{player.batarangs}"`. Use yellow when player has ≥1 batarang, gray when 0.
- **Done when**: HUD visibly shows `[C]BAT x5` during gameplay.

### 1.2 HUD: pulse-highlight batarang ammo when full or just-thrown

- **Files**: `src/batman_returns/hud.py`, `src/batman_returns/entities.py`
- **Where**: `Player.try_throw` (set `last_throw_frame = 0`), HUD reads it
- **What**: when `Player.last_throw_frame > 0`, draw a yellow flash circle behind the BAT counter for 8 frames; decrement each frame in `Player.update`.
- **Done when**: throwing batarang produces visible flash on the HUD.

### 1.3 Stage progress bar at the top

- **Files**: `src/batman_returns/hud.py`, `src/batman_returns/game.py`
- **Where**: new `draw_stage_progress(surf, level)` called in `_draw_world`.
- **What**: thin 2-px-tall bar, `bar_x=80, y=2, w=160`. Fill ratio = `cam_x / (width_px - NATIVE_W)`. Use purple → yellow gradient. Add a tick mark at `midboss_at_tile / length_tiles` if midboss exists.
- **Done when**: `tests/test_hud.py::test_progress_bar_position_matches_cam` passes by computing pixel positions.

### 1.4 Goal arrow indicator (right edge)

- **Files**: `src/batman_returns/game.py`
- **Where**: `_draw_world` after HUD draw
- **What**: when `world.player.x > width_px - NATIVE_W * 1.5` and stage is non-boss, draw an animated `▶ GOAL` chevron pulsing on the right edge (use draw_text with two sizes alternating every 30 frames).
- **Done when**: visible chevron on right edge of screen during the last screen of any stage.

### 1.5 End-of-stage goal flag entity (visible target)

- **Files**: `src/batman_returns/sprites.py`, `src/batman_returns/level.py`, `src/batman_returns/game.py`
- **Where**: new sprite `BAT_FLAG`, drawn at `(width_px - 32, GROUND_Y - 32)` for non-boss stages.
- **What**: a yellow flag with a bat silhouette (24×32 sprite). Drawn each frame in `Level._draw_ground`. Player crossing `x >= flag_x` triggers stage advance (replaces width_px-NATIVE_W//2 condition).
- **Done when**: visible flag sprite appears at end of stages 1 and 2 (not stage 3, which has Penguin).

### 1.6 Mid-boss / boss approach warning banner

- **Files**: `src/batman_returns/game.py`
- **Where**: in `_spawn_for_stage` when midboss/boss spawns, set `world.warning_timer = 90`, `world.warning_text = ...`
- **What**: draw a full-width red/yellow striped banner with text `WARNING — JOKER APPROACHING` for 90 frames after spawn. Banner overlays the stage at y=NATIVE_H/2-12.
- **Done when**: banner visible for 1.5s when each midboss/boss spawns.

### 1.7 Brighter, slower, traced batarang

- **Files**: `src/batman_returns/sprites.py` (resize sprite), `src/batman_returns/entities.py` (`Batarang` class)
- **Where**: `BATARANG` grid (12×9 → 14×11, brighter palette), `Batarang.update` (vx default 4.5 → 3.2)
- **What**: redesign sprite with yellow highlight pixels in addition to black; lower vx; render a 4-frame trail (store last 4 positions in `Batarang.trail`, draw each as a fading dot).
- **Done when**: batarang visibly leaves a yellow trail and travels noticeably slower.

### 1.8 Batarang launch FX

- **Files**: `src/batman_returns/game.py`
- **Where**: in the KEYDOWN K_C / pad-button case, after `bat = p.try_throw()`
- **What**: when `bat is not None`, call `world.particles.emit(bat.x, bat.y, count=8, speed=2.0, color=PALETTE["yellow"], life=10)` and `world.shake.kick(1.5)` for a brief visible launch.
- **Done when**: throwing batarang produces a yellow particle burst at the throw point.

### 1.9 LEVEL_INTRO shows controls + objective; longer duration

- **Files**: `src/batman_returns/game.py`
- **Where**: `_draw_intro`, `new_run`/`advance_stage` (`intro_timer=90` → `180`)
- **What**: extend intro to 3 seconds. Add three lines under stage name:
  ```
  OBJECTIVE: DEFEAT JOKER, REACH THE FLAG
  Z PUNCH   X KICK   C BATARANG   ↓ SLIDE
  ←→ MOVE   SPACE JUMP   P PAUSE
  ```
- **Done when**: intro screen shows all controls for 3s.

### 1.10 Pause menu adds CONTROLS page

- **Files**: `src/batman_returns/game.py`
- **Where**: `_draw_pause`, pause cursor count goes 4 → 5
- **What**: new menu item `CONTROLS`. Selecting it pushes a sub-state showing keys + gamepad mapping. Esc/B returns to pause menu.
- **Done when**: pause menu lists CONTROLS and the sub-screen renders with full mapping.

### 1.11 Objective text on HUD (top centre)

- **Files**: `src/batman_returns/hud.py`, `src/batman_returns/game.py`
- **Where**: `draw_hud` accepts optional `objective: str` parameter
- **What**: show an objective string centre-top: `DEFEAT JOKER` while midboss alive; `REACH THE FLAG ▶` after midboss dies; `DEFEAT THE PENGUIN` on stage 3.
- **Done when**: HUD shows live objective state matching world progression.

---

## Phase 2 — First-run tutorial

### 2.1 Persisted `tutorial_seen` flag in SaveData

- **Files**: `src/batman_returns/persistence.py`
- **What**: add `tutorial_seen: bool = False` to `SaveData`.
- **Done when**: round-trip save/load preserves the flag.

### 2.2 Tutorial overlay during first stage

- **Files**: `src/batman_returns/game.py`
- **What**: when `not save.tutorial_seen` and stage_idx == 0, show inline prompts that fade in/out:
  - 0–4s: `←→ TO MOVE`
  - 4–8s: `SPACE TO JUMP`
  - on first enemy spawn: `Z TO PUNCH`
  - on first hit landed: `HOLD SHIFT TO RUN`
  - on second enemy spawn: `C TO THROW BATARANG`
  After all prompts shown, set `save.tutorial_seen = True` and persist.
- **Done when**: prompts appear in order on a fresh save dir.

### 2.3 Skip tutorial in subsequent runs

- **Files**: `src/batman_returns/game.py`
- **What**: gate prompt logic behind `not save.tutorial_seen`.
- **Done when**: deleting save file shows tutorial; running again does not.

---

## Phase 3 — Combat polish

### 3.1 Charged batarang (hold C)

- **Files**: `src/batman_returns/entities.py`, `src/batman_returns/game.py`
- **What**: track `Player.charge_frames` while C held; at ≥45 frames release fires a "piercing" batarang (passes through enemies, double damage, doesn't decrement count).
- **Done when**: holding C ≥0.75s and releasing fires a glowing batarang that doesn't consume ammo.

### 3.2 Combo names

- **Files**: `src/batman_returns/game.py`, `src/batman_returns/effects.py`
- **What**: emit floating text on combo milestones: 2=`DOUBLE`, 3=`TRIPLE`, 5=`MEGA COMBO`, 10=`UNSTOPPABLE`.
- **Done when**: hitting 5 enemies in window shows `MEGA COMBO` floating text.

### 3.3 Hit-stop on first kill of run

- **Files**: `src/batman_returns/game.py`, `src/batman_returns/effects.py`
- **What**: track `world.first_kill_done = False`; on first enemy kill freeze for 8 extra frames and emit a yellow flash overlay.
- **Done when**: first kill noticeably pauses; subsequent kills do not.

### 3.4 Boss attack telegraph

- **Files**: `src/batman_returns/entities.py`
- **What**: 30 frames before each Penguin shot, render a red `!` over Penguin's head and play a soft warning beep (new `audio.warn()`).
- **Done when**: boss telegraphs each shot with visible `!` and audible cue.

### 3.5 Smoke bomb pickup (rare)

- **Files**: `src/batman_returns/entities.py`, `src/batman_returns/sprites.py`, `src/batman_returns/game.py`
- **What**: new `Pickup("smoke")`; on pickup, deals 999 damage to all enemies within 64 px; rate ≈3% of pickup spawns.
- **Done when**: walking into a smoke pickup wipes nearby enemies.

### 3.6 Enemy death animation

- **Files**: `src/batman_returns/entities.py`
- **What**: on `Enemy.alive=False`, set `Enemy.death_timer=18` instead of immediate cleanup; during decay, draw with horizontal squash and fade alpha.
- **Done when**: enemies briefly squash + fade instead of vanishing.

---

## Phase 4 — Level structure

### 4.1 Cleaner stage transition (black wipe)

- **Files**: `src/batman_returns/game.py`
- **What**: new state `STAGE_TRANSITION` — black overlay grows from 0% to 100% alpha over 30 frames, then advances stage, then shrinks back. Replaces hard cut.
- **Done when**: stage advance shows 1s wipe-out and wipe-in.

### 4.2 Difficulty selection

- **Files**: `src/batman_returns/persistence.py`, `src/batman_returns/game.py`, `src/batman_returns/constants.py`
- **What**: add `Difficulty(StrEnum)`; on title screen offer EASY/NORMAL/HARD as a third menu item. Apply scalars to enemy HP / contact damage / batarang ammo.
- **Done when**: difficulty selection visibly changes enemy HP totals (verify via test).

### 4.3 Continue from highest cleared stage

- **Files**: `src/batman_returns/persistence.py`, `src/batman_returns/game.py`
- **What**: persist `highest_cleared_stage`; offer `CONTINUE FROM STAGE N` on title when >0.
- **Done when**: clearing stage 1 then quitting and restarting offers continue from stage 2.

### 4.4 Stage select after first full clear

- **Files**: `src/batman_returns/persistence.py`, `src/batman_returns/game.py`
- **What**: after VICTORY, set `save.beat_game = True`. Title screen gains `STAGE SELECT` menu item that lets player choose any unlocked stage.
- **Done when**: completing the game unlocks stage select.

---

## Phase 5 — Enemy variety + combat depth

### 5.1 Patrol → chase AI states

- **Files**: `src/batman_returns/entities.py`
- **What**: new `Enemy.alert: bool` — false at spawn, set true when player enters 80 px or attacks land. Patrolling enemies pace 32 px around spawn point at half speed.
- **Done when**: walking past an unalerted enemy at distance ≥120 px doesn't aggro them.

### 5.2 Skater clown (Ice Plaza)

- **Files**: `src/batman_returns/entities.py`, `src/batman_returns/sprites.py`, `src/batman_returns/constants.py`
- **What**: new `EnemyKind.SKATER` — slides at 3.0 px/frame on flat ground, can't change direction quickly; dodges punch by sliding under, vulnerable to dive-kick.
- **Done when**: Ice Plaza spawns occasional skaters that slide past the player.

### 5.3 Penguin umbrella shield

- **Files**: `src/batman_returns/entities.py`
- **What**: in phase 2, after each shot, Penguin enters `shielded` state for 30 frames during which `take_damage` returns False without changing HP. Visual: white outline around sprite.
- **Done when**: hitting Penguin during shield window shows outline and no HP loss.

### 5.4 Catwoman whip

- **Files**: `src/batman_returns/entities.py`
- **What**: between lunges, Catwoman occasionally lashes a horizontal whip beam (renderable as fast knife_proj variant with sprite `whip`).
- **Done when**: Catwoman fight has a long-range whip in addition to lunges.

---

## Phase 6 — World polish

### 6.1 Foreground parallax layer

- **Files**: `src/batman_returns/level.py`, `src/batman_returns/sprites.py`
- **What**: add `Level._draw_foreground` after entity draws — lamp posts, ice spikes, columns at 1.4× parallax. Stage-specific.
- **Done when**: visible foreground objects scroll faster than player.

### 6.2 Stage-specific platform sprites

- **Files**: `src/batman_returns/sprites.py`, `src/batman_returns/level.py`
- **What**: per-stage `platform_sprite` field; stage 1 = brick, stage 2 = ice block, stage 3 = lair stone.
- **Done when**: each stage uses different platform tile.

### 6.3 Background pedestrians silhouettes

- **Files**: `src/batman_returns/level.py`
- **What**: at stage 1's far parallax, render small black silhouettes walking across.
- **Done when**: tiny figures visible in Gotham background.

---

## Phase 7 — Quality of life

### 7.1 Settings screen

- **Files**: `src/batman_returns/game.py`
- **What**: separate state `SETTINGS` reachable from title; expand current pause options (SFX/music vol) and add `FULLSCREEN`, `SHOW FPS`, `RESET HIGH SCORES`.
- **Done when**: settings persist and apply.

### 7.2 Window resizable + scaled

- **Files**: `src/batman_returns/game.py`
- **What**: pass `pygame.RESIZABLE` flag; on `pygame.VIDEORESIZE` recompute scaled blit rect maintaining 320×224 aspect with letterboxing.
- **Done when**: dragging the window edge keeps the game letterboxed without distortion.

### 7.3 Screenshot key

- **Files**: `src/batman_returns/game.py`
- **What**: F12 saves current canvas to `~/batman-returns-screenshots/<timestamp>.png`.
- **Done when**: pressing F12 writes a PNG.

### 7.4 Show FPS overlay

- **Files**: `src/batman_returns/game.py`, `src/batman_returns/hud.py`
- **What**: when `save.show_fps`, draw `clock.get_fps()` integer in upper-right corner.
- **Done when**: toggling the setting shows a live FPS number.

---

## Out-of-scope for this round (deferred)

- Full controller remapping UI
- Online leaderboard
- Modding / level editor
- Batmobile driving stages (would need pseudo-3D rasterizer; original used SCALE.68K)
- Network multiplayer

---

## Phase ordering rationale

Phase 1 fixes the immediate "I don't know what to do" pain. Phase 2 covers
new players. Phases 3–7 are quality / depth in descending impact order. A
sub-agent should be able to claim any task in any phase as long as Phase 1.x
items are done first (especially 1.1, 1.5, 1.9, 1.11 — these reshape the HUD
and intro that other tasks lean on).
