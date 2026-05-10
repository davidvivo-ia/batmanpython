# Batman Returns (Sega CD, 1992) — source analysis

This is the structural read of the retail 68000 ASM source at
[`RetailGameSourceCode/BatmanReturns`](https://github.com/RetailGameSourceCode/BatmanReturns)
that informed the Python port. It is **not** a port of any code; only of design
choices and tunables that were already published as design docs (`TECH.DOC`)
or expressed as constants in `BATMAN.EQU`.

## Repo layout

```
Source/
  BATMAN.EQU      shared constants, score table, sprite IDs
  TECH.DOC        playfield format, sprite budgets, fps targets
  PANEL.EQU       HUD layout
  LOGIC.68K       game logic dispatch
  OBJECT.68K      generic object/projectile pool
  ROAD.68K        pseudo-3D road for driving levels
  SCALE.68K       sprite scaling tables
  DAMAGE.68K      damage handling
  VISUALS.68K     drawing routines
  CAR_CTRL.68K    Batmobile (level 4)
  SKI_CTRL.68K    Batskiboat (level 5)
  SN_SBAT.68K     Skiboat enemy
  LEVEL_1/
    BASHER.68K        clown thug (melee)
    JACKNBOX.68K      jack-in-the-box pop-up
    FIRETRUC.68K      fire truck / breather clown
    MINIFIRE.68K      its child fire projectile
    VILLAN.68K        named villain / boss
  LEVEL_2/ ... LEVEL_5/
```

## Constants extracted (`BATMAN.EQU`)

- Player: lives counter, 4-byte score, damage byte, X/Y, speed + speed-numerator
- Score values:
  - small object: $200
  - road obstacle: $100
  - standard enemy: $500
  - mid-boss: $2 000
  - final boss: $5 000
- SFX IDs include `SFX_BDFIRE_A` (batarang fire), `BDHIT_A`, `BDHIT_B`

## Display (`TECH.DOC`)

- 32×24 char playfield, 16×16-pixel **stamps** (1 024 stamps total)
- 256×208-pixel maps, 96 maps per stage
- Parallax cloud layer
- 4-row HUD/info panel at the bottom
- Sprite budget ≈ 280 chars (Batmobile is the budget hog)
- Driving target: **20 fps**

## Mapping to Python

See README.md "What got ported, conceptually" table.

The driving stages (`CAR_CTRL.68K`, `SKI_CTRL.68K`, `ROAD.68K`, `SCALE.68K`)
were intentionally not ported in v1. A faithful Python recreation would need a
sprite-scaling pseudo-3D rasterizer; not impossible, but out of scope for an
initial homage.

## Atari 2600 reference

[`arthurealike/batman2600`](https://github.com/arthurealike/batman2600)
(`kernel.asm`) is incomplete — it has a scrolling playfield, a "bat" sprite
with horizontal/vertical movement, gravity, and jump (`IsJumping` /
`IsFalling`), but no enemies or scoring (per its own TODOs). Useful only as a
reminder that **all you need for a credible Batman feel is: scrolling, jump,
attack**. The rest is content.
