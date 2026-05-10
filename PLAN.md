# PLAN.md v2 — Comprehensive completion roadmap

> Deeper, source-grounded roadmap. Each task lists files to edit, function
> anchors, exact change, and acceptance criterion. A sub-agent should be able
> to execute one task without reading the rest of the plan.
>
> **Citations** to the original 1992 Sega CD source live at
> [`RetailGameSourceCode/BatmanReturns`](https://github.com/RetailGameSourceCode/BatmanReturns)
> and Chris Shrigley's archive
> [`Batman_Returns_SegaCD_Project_Package.zip`](http://shrigley.com/source_code_archive/).
> Filenames cited as `LEVEL_X/FILE.68K` are real modules in the upstream tree.

## Original-source mapping (what we faithfully ported, what's still missing)

### Already ported (from BATMAN.EQU, TECH.DOC, PANEL.EQU)

- 16×16 tile system (`TECH.DOC`) → `constants.TILE_SIZE`
- Score economy (`BATMAN.EQU`): 200/100/500/2000/5000 → `SCORE_*`
- Bottom HUD panel (`PANEL.EQU`) → `hud.draw_hud`
- Per-sprite `OBJ_FLASH1` palette flicker (`DAMAGE.68K`) → `Enemy.iframes` red tint
- KILL_CTRL death pipeline (`DAMAGE.68K`) → `Enemy.is_dying` 18-frame squash
- LEVEL_1 enemies: BASHER, JACKNBOX, FIRETRUC+MINIFIRE, VILLAN
  → `EnemyKind.{BASHER,JACKBOX,FIREBREATHER,KNIFER,MIDBOSS_JOKER}`
- Multi-phase boss (`VILLAN.68K` + score $5000) → 3-phase Penguin
- 20fps target lifted to 60fps (`TECH.DOC`)
- Cinematic shell (`SHELL.EQU` `load_tween1`/`tween2`) → `LEVEL_INTRO` state
- Per-villain game-over (`load_gameover1`/`gameover2`) → restart from title

### Still missing from the original ROM

| Original module                | What it is                                | Status in port |
|--------------------------------|-------------------------------------------|----------------|
| `LEVEL_1/CYCLE.68K`            | Motorcycle clown — fast horizontal threat | **TODO P8.1**  |
| `LEVEL_2/TANK.68K`             | Boss-class tank w/ shells                 | **TODO P8.2**  |
| `LEVEL_2/CANNON.68K`+`MINICAN` | Stationary turret + small cannon           | TODO P8.3       |
| `LEVEL_2/BOLARD.68K`+`TRCONE`  | Street bollards + traffic cones (obstacles)| TODO P8.4       |
| `LEVEL_2/TRUCK.68K` / `ICETRUCK`| Heavy trucks bowling through              | TODO P8.5       |
| `LEVEL_3/WKLITE.68K`           | "Weight-light" — heavy ramming clown       | TODO P8.6       |
| `LEVEL_3/BACKANIM.68K`         | Animated background sprites               | TODO P12.1      |
| `LEVEL_5/PENGUINS.68K`         | Mini-penguin swarm                        | TODO P14.3      |
| `LEVEL_5/MINES.68K`            | Floating mines (water hazard)             | TODO P9.5       |
| `SFX_EXPLDBOSS_A`              | Special boss-only death roar              | TODO P11.5      |
| `SHELL/load_tween1..2`         | Per-stage cutscenes                       | TODO P12.x      |
| `SHELL/load_finale1..2`        | Two-tier ending (driving-only / full)     | TODO P14.5      |
| Driving stages (`CAR_CTRL`)    | Pseudo-3D Batmobile + Batskiboat          | Out of scope    |

The driving stages remain explicitly out-of-scope — they would require a
sprite-scaling rasterizer (`SCALE.68K`) which is a sub-engine of its own.

---

## Implementation contract

For each task:
1. **Files** — exact paths.
2. **Where** — function or section anchor.
3. **What** — concrete change.
4. **Done when** — test name or visible behaviour.

After every task: `ruff check src tests && SDL_VIDEODRIVER=dummy
SDL_AUDIODRIVER=dummy pytest tests/ -q` must pass.

---

## Phase 8 — Faithful enemy expansion (port the cut-content roster)

### 8.1 CYCLE (motorcycle clown) — *high priority*

Original: `LEVEL_1/CYCLE.68K` — fast horizontal mover that closes distance hard.

- **Files**: `entities.py`, `sprites.py`, `constants.py`, `game.py`
- **What**: new `EnemyKind.CYCLE` with a 24×16 sprite (clown on a wheeled bike).
  Behaviour: targets player y, charges horizontally at 4.5 px/frame; on contact
  deals heavy damage (18) then drives off-screen. HP 25 (low — kill with one
  good hit).
- **Spawn weight**: weight 3 in `_spawn_for_stage` for stages 0, 1, 4 (Gotham/Rooftops/Docks).
- **Done when**: a motorcycle enemy occasionally streaks across the screen.

### 8.2 TANK (street tank mid-boss alternative)

Original: `LEVEL_2/TANK.68K` + `CANNON.68K`.

- **Files**: `entities.py`, `sprites.py`, `constants.py`
- **What**: new `EnemyKind.TANK` — slow (0.4 px/f), HP 220, fires a parabolic
  shell every 90 frames. Walking into it deals 22 dmg.
- **Where**: optional spawn after Joker midboss (weight 1 in stage 0/1).
- **Done when**: tanks occasionally appear in late-stage spawn; slow + threatening.

### 8.3 CANNON / MINICAN (stationary turret)

- **Files**: `entities.py`, `sprites.py`, `constants.py`
- **What**: new `EnemyKind.CANNON` — fixed at spawn x; can't move; lobs shells
  every 80 frames. HP 30, score $400.
- **Done when**: stationary turrets appear at fixed mileposts in stage 1 and 4.

### 8.4 BOLARD / TRCONE (path obstacles)

- **Files**: `level.py`, `sprites.py`
- **What**: non-Enemy world props that deal 5 damage on contact and break
  after one hit. Spawn occasionally on Gotham streets / Docks. Pure obstacle —
  no AI.
- **Done when**: visible cones / bollards block the player's path.

### 8.5 ICETRUCK (Ice Plaza heavy)

Original: `LEVEL_3/ICETRUCK.68K`.

- **What**: a slow tank-variant scaled to ICE PLAZA palette.
- **Done when**: tanks appear in Ice Plaza with light-blue trim.

### 8.6 WKLITE (weight-light heavy clown)

- **What**: 24×24 muscular clown that walks slowly (0.6 px/f), HP 90, contact
  damage 18, knocks back the player on hit.
- **Stages**: Sewers and Asylum.

### 8.7 Patrol radius differentiation

Many enemies currently use the same 80px alert radius. Differentiate:
- BASHER: 80
- KNIFER: 120 (keeps distance, alerts further)
- FIREBREATHER: 100
- CYCLE: always alert (doesn't patrol)
- TANK: always alert
- CANNON: always alert (auto-fires)

---

## Phase 9 — Combat depth: returning batarang + magnet pickups

### 9.1 Returning batarang (boomerang motion)

Original spirit: in the comics & 1992 game, the batarang loops back. Currently
it just travels straight.

- **Files**: `entities.py`
- **What**: `Batarang.update` curves the path: after `life < 60`, start
  decelerating vx then reverse direction. If it touches the player on the
  return leg, increment ammo by 1 (re-catch). Pierces enemies on the return
  leg too if charged.
- **Done when**: regular batarangs visibly arc back and can be caught.

### 9.2 Mid-air re-throw

- **Files**: `game.py`
- **What**: while a batarang is airborne, hold C lights up the HUD with a
  cyan halo; pressing X mid-air recalls the batarang to player position
  instantly (used for mid-air dive-kick combos).
- **Done when**: pressing X while batarang is airborne snaps it home.

### 9.3 Magnet pickup

- **Files**: `entities.py`, `game.py`
- **What**: a rare "magnet" pickup attracts all on-screen pickups towards the
  player for 5 seconds.
- **Done when**: walking over magnet pulls floating pickups to you.

### 9.4 Boomerang + piercing combo

- **What**: a charged batarang on the return leg hits the same enemy twice
  (front and back). Update `hit_set` to allow this.

### 9.5 Floating mines (water-stage hazard)

Original: `LEVEL_5/MINES.68K`.

- **Files**: `entities.py`, `level.py`
- **What**: in water-hazard stages (Sewers, Docks), some hazard tiles spawn
  bobbing mines that explode if shot or contacted (14 dmg radius).

---

## Phase 10 — Power-ups (3-stage timed buffs)

### 10.1 Invincibility (~5s)

- **Files**: `entities.py`, `game.py`, `sprites.py`
- **What**: a yellow Bat-emblem pickup grants `Player.invuln_timer = 300`.
  While >0, all damage is negated and the sprite cycles a rainbow tint.
- **Done when**: walking into the bat-emblem pickup makes the player flash
  rainbow and ignore enemy contact for 5s.

### 10.2 Damage doubler (~8s)

- **Files**: `entities.py`, `game.py`
- **What**: a red `2x` icon pickup; while `Player.damage_buff_timer > 0`,
  `attack_damage` is doubled. HUD shows `2X` next to score.
- **Done when**: pickup grants 8s of doubled punch/kick/batarang damage.

### 10.3 Infinite batarangs (~6s)

- **Files**: `entities.py`, `game.py`
- **What**: a blue infinity icon pickup; while `Player.infinite_bat_timer > 0`,
  `try_throw` doesn't decrement `batarangs`. HUD draws `[C]BAT ∞`.
- **Done when**: pickup grants 6s of free batarangs.

### 10.4 Power-up drop logic

- **Files**: `entities.py`
- **What**: 2% drop chance from non-boss enemy kills (separate from `Pickup`
  spawn rolls).

---

## Phase 11 — Boss polish (telegraphs + finale)

### 11.1 Catwoman whip attack

Was in PLAN v1 but never done.

- **Files**: `entities.py`, `sprites.py`
- **What**: between lunges, Catwoman extends a 60-px-long beam (sprite `whip`)
  for 12 frames; intersects player hitbox = 14 dmg. Visually drawn as a
  stretched line of yellow + black pixels.
- **Done when**: Catwoman fight has visibly different lunge vs whip phases.

### 11.2 Boss attack windups (Joker, Catwoman, Penguin)

Original: implicit in slow `attack_cooldown` — but no visual cue. Add
explicit telegraph:

- 30 frames before each Joker fan-throw: red `!` over head + soft beep
- 24 frames before each Catwoman lunge: orange `>` arrow
- 30 frames before each Penguin shot: red `!` (already done)

### 11.3 Boss stagger (group-attack interrupt)

- **What**: if a boss takes ≥80 damage in a single frame (e.g. charged batarang
  + dive-kick combo), they enter a 30-frame stagger state — no attacks, takes
  +50% damage.
- **Done when**: heavy combo on a boss visibly pauses them.

### 11.4 Penguin phase-3 enrage burst

- **What**: when Penguin enters phase 3, all currently-airborne enemy shots
  scatter outward for visual chaos; banner reads "ENRAGED!".
- **Done when**: phase 3 transition is unmistakable.

### 11.5 Special boss death VFX (`SFX_EXPLDBOSS_A`)

- **Files**: `audio.py`, `game.py`
- **What**: dedicated `audio.boss_explode()` + a 90-frame death animation
  where the boss flickers, emits 60 particles, screen flashes white twice
  at 30 frames spacing.
- **Done when**: killing Penguin triggers visible cinematic death sequence.

### 11.6 Penguin minion swarm in phase 3

Original: `LEVEL_5/PENGUINS.68K`.

- **What**: in phase 3, every 90 frames Penguin spawns a small "penguin chick"
  (sprite shared with PENGUIN_BOSS scaled to 8×12) that walks at 1.5 px/f.

---

## Phase 12 — Cinematic stage intros / outros (`SHELL.EQU` parity)

### 12.1 Two-panel pre-stage cutscene

- **Files**: `game.py` (new state `STAGE_CINEMATIC`)
- **What**: between LEVEL_INTRO and PLAYING, draw two static "panels" of
  pixel-art with stylised dialogue. Uses procedural composition: stage name,
  villain portrait, location text. 4 seconds total. Skippable.

### 12.2 Per-stage narrative text

- **Files**: `level.py` (`Stage.intro_lines: tuple[str, ...]`)
- **What**: each stage gets 2-3 short story lines:
  - Streets: "Christmas eve in Gotham. Joker's clowns are loose."
  - Rooftops: "The chase climbs above the city."
  - Sewers: "Penguin's lair lies below — through the slime."
  - Ice Plaza: "Catwoman watches from the rooftops."
  - Docks: "Mines float in the harbour."
  - Asylum: "Echoes of madness fill Arkham's halls."
  - Lair: "The final descent. Penguin makes his stand."

### 12.3 Stage-clear panel

- **Files**: `game.py` (new `STAGE_CLEAR` state)
- **What**: 90-frame post-stage screen showing accumulated stats + bonuses
  (see Phase 13).

### 12.4 Title cinematic loop

- **Files**: `game.py`
- **What**: title screen plays a slow scrolling Gotham silhouette in the
  background; bat-signal pulses; rain falls.

---

## Phase 13 — Stage-clear summary + score bonuses

### 13.1 Stats tracker per stage

- **Files**: `game.py` (`World.stats`)
- **What**: track `kills`, `damage_taken`, `pickups_collected`, `time_frames`,
  `combo_max`, `batarangs_used` per stage.

### 13.2 End-of-stage scoring screen

- **Files**: `game.py`
- **What**: STAGE_CLEAR state shows:
  ```
  STAGE 2 CLEARED — GOTHAM ROOFTOPS
  KILLS               ×12  +6000
  TIME (1:24)              +2400
  NO-DAMAGE BONUS          +5000
  MAX COMBO          7X    +1500
  ───────────────────────────────
  TOTAL                   +14900
  ```
  Each line slides in over 12 frames.

### 13.3 Time-bonus formula

- `+max(0, 5000 - time_frames * 2)` — encourages speed.

### 13.4 No-damage bonus

- `+5000` if `damage_taken == 0` for the stage.

### 13.5 All-pickup bonus

- `+2000` if `pickups_collected == pickups_total` (all pickups in stage).

---

## Phase 14 — Endgame & replayability

### 14.1 New Game Plus

- **Files**: `persistence.py`, `game.py`, `constants.py`
- **What**: after first VICTORY, set `save.beat_game = True`. Title screen
  gains "NEW GAME +" option that:
  - Doubles enemy HP and damage on top of difficulty scalars
  - Gives the player 5 starting batarangs but 1 less life
  - Unlocks a special "ng_plus" achievement on completion
  - Title shows "NG+" indicator

### 14.2 Secret 8th stage: THE BATCAVE

- **Files**: `level.py`, `sprites.py`, `game.py`
- **What**: only accessible from STAGE SELECT after first full clear.
  Dense enemy waves (density 0.25), no hazards, all 6 mook enemy types,
  unique tile sprite. 90 tiles long. Music: lair theme.
- **Done when**: STAGE SELECT shows the 8th stage greyed out before victory,
  unlocked after.

### 14.3 Penguin chick swarm (LEVEL_5/PENGUINS.68K)

- **Files**: `entities.py`
- **What**: see Phase 11.6 above.

### 14.4 Time attack mode

- **Files**: `game.py`, `persistence.py`
- **What**: from settings, toggle "TIME ATTACK". Stages run with a visible
  timer counting up; final score shown is the total time. Best times persist
  per stage.

### 14.5 Ending picture (load_finale1)

- **Files**: `game.py`
- **What**: VICTORY screen shows a procedurally-composed Gotham skyline with
  bat-signal in the centre + "GOTHAM IS SAFE" text fading in over 90 frames.
  Then list 3 lines of credits.

---

## Phase 15 — Localisation (Spanish)

### 15.1 String table

- **Files**: new `src/batman_returns/i18n.py`
- **What**: dict-based string table. `t("score") -> "SCORE"` (en) /
  `"PUNTOS"` (es). All UI strings routed through `t()`.

### 15.2 Settings: language toggle

- **Files**: `persistence.py`, `game.py`
- **What**: `save.language = "en" | "es"`. Settings menu adds `LANGUAGE  ENG/ESP`.

### 15.3 Spanish translation table

- Stage names: Calles de Gotham / Tejados de Gotham / Las Cloacas / Plaza de Hielo /
  Muelle / Manicomio Arkham / Guarida del Pingüino / La Baticueva
- Objectives: DERROTA AL JOKER, ALCANZA LA META, CUIDADO CON EL VACÍO, etc.
- Menu: NUEVA PARTIDA, CONTINUAR, SELECCIONAR FASE, OPCIONES, MEJORES PUNTUACIONES, SALIR

---

## Phase 16 — Polish round 2

### 16.1 Per-enemy unique death SFX

- **Files**: `audio.py`, `entities.py`
- **What**: `audio.death_for(kind: EnemyKind) -> Sound` returning a tinted
  variant: clowns get a "wahwah", knifers a clatter, fire-breathers a hiss.

### 16.2 Animated HUD heart icons (lives)

- **Files**: `hud.py`
- **What**: lives icons pulse softly at 0.5 Hz, brighten when picked up.

### 16.3 Damage-tinted screen edge

- **Files**: `game.py`
- **What**: when `player.hp < 30`, the screen edges pulse red faintly to
  signal critical state.

### 16.4 Slow-mo on dive-kick kill

- **Files**: `game.py`
- **What**: on a dive-kick kill, freeze for 8 frames + emit 16 yellow
  particles upward.

### 16.5 Combo timer ring

- **Files**: `hud.py`
- **What**: replace the linear combo bar with a circular ring that drains
  clockwise when combo timer is decreasing.

### 16.6 Background pedestrian silhouettes

- **Files**: `level.py`
- **What**: at far-parallax (factor 0.15), render small black silhouette
  figures crossing the street on Gotham stages.

### 16.7 Animated bat-signal in title

- **Files**: `game.py`
- **What**: title's bat-signal pulses with rotating beam; bat sprite gently
  bobs vertically.

---

## Phase 17 — Tests & CI

### 17.1 Tests for every new enemy kind

- **Files**: `tests/test_enemies.py` (new)
- **What**: spawn each new kind, verify it doesn't crash on update for 60
  frames, verify damage/score values match constants.

### 17.2 Tests for power-up timers

- **Files**: `tests/test_powerups.py`
- **What**: each power-up sets the right timer; expires correctly.

### 17.3 Tests for stage-clear bonuses

- **Files**: `tests/test_stage_clear.py`
- **What**: clearing a stage with no damage adds NO_DAMAGE_BONUS; max combo
  kicks in COMBO_BONUS.

### 17.4 Localisation roundtrip

- **Files**: `tests/test_i18n.py`
- **What**: every key in EN table exists in ES; switching language updates
  rendered text.

### 17.5 NG+ scaling test

- **Files**: `tests/test_ng_plus.py`
- **What**: enemy spawn under NG+ has 2× HP of normal mode.

### 17.6 Update CI matrix

- Run new tests; ensure ≤ 3min total runtime.

---

## Out-of-scope (deferred, low impact)

- Driving stages 4-5 (require pseudo-3D renderer)
- Online leaderboard / matchmaking
- Mod / level editor
- Controller remap UI (current mapping is fixed)
- Steam achievements integration

---

## Phase ordering rationale

- **Phase 8** is highest immediate impact: faithful enemy roster matches the
  original cut content + adds combat variety.
- **Phase 9** layers boomerang dynamics that turn batarang from one-shot to
  central mechanic.
- **Phase 10** adds the temporary buff loop that makes pickups exciting.
- **Phase 11** finalises bosses to feel set-piece (telegraphs, finale).
- **Phase 12** & **13** wrap the campaign in proper presentation (cinematics,
  stage-clear screen).
- **Phase 14** unlocks endgame replayability.
- **Phase 15** broadens audience.
- **Phase 16-17** polish + safety net.

A sub-agent can claim any task within a phase. Phase 8.x → 9 → 10 → 11 is
the optimal feature order; 12-13 should be done together; 14-17 can run
in parallel.
