"""Procedural pixel art. Every sprite is drawn at runtime onto a Surface.

Each sprite is described as a string grid; characters map to palette keys via
``LEGEND``. ``make_sprite`` returns a per-pixel-alpha Surface ready to blit.
This keeps the repo asset-free and tweakable.
"""

from __future__ import annotations

from functools import cache

import pygame

from .constants import PALETTE

LEGEND: dict[str, str | None] = {
    ".": None,            # transparent
    "K": "black",
    "D": "dark",
    "N": "night",
    "P": "purple",
    "M": "magenta",
    "G": "gray",
    "L": "lightgray",
    "W": "white",
    "S": "skin",
    "Y": "yellow",
    "O": "orange",
    "R": "red",
    "B": "bloodred",
    "E": "green",
    "Q": "snow",
}


def make_sprite(grid: list[str], scale: int = 1) -> pygame.Surface:
    """Build a Surface from a string grid. Top-left origin."""
    h = len(grid)
    w = max(len(row) for row in grid)
    surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == "." or ch == " ":
                continue
            key = LEGEND.get(ch)
            if key is None:
                continue
            color = PALETTE[key]
            if scale == 1:
                surf.set_at((x, y), color)
            else:
                pygame.draw.rect(surf, color, (x * scale, y * scale, scale, scale))
    return surf


# ----------------------------------------------------------------------
# Batman sprites (16 wide x 24 tall) — chunky, readable silhouette.
# Cape on left when facing right. We mirror at runtime for the other side.
# ----------------------------------------------------------------------

BATMAN_IDLE = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKK......",
    ".KKKKKKKKK......",
    "KKKYYKKYYKKK....",
    "KKKKKKKKKKKK....",
    "KKK.KKKK.KKK....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "...KK..KK.......",
    "...KK..KK.......",
    "..KKK..KKK......",
]

BATMAN_WALK_A = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKK......",
    ".KKKKKKKKK......",
    "KKKYYKKYYKKK....",
    "KKKKKKKKKKKK....",
    ".KK.KKKK.KK.....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "...K....K.......",
    "...K....K.......",
    "..K......K......",
    "..K......K......",
    ".KK......KK.....",
    "KKK......KKK....",
    "KK........KK....",
]

BATMAN_WALK_B = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKK......",
    ".KKKKKKKKK......",
    "KKKYYKKYYKKK....",
    "KKKKKKKKKKKK....",
    "KKKKKKKKKKKK....",
    ".K.KKKKKK.K.....",
    "....KKKK........",
    "....KKKK........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....KKKK........",
    "...KKKKKK.......",
    "..KKK..KKK......",
    ".KK......KK.....",
]

BATMAN_JUMP = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKK......",
    ".KKKKKKKKK..KK..",
    "KKKYYKKYYKKKKKK.",
    "KKKKKKKKKKKKKK..",
    "KKK.KKKK.KKK....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "...KK..KK.......",
    "..KK....KK......",
    ".KK......KK.....",
    "KK........KK....",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
]

BATMAN_PUNCH = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKKKKK...",
    ".KKKKKKKKKSSSK..",
    "KKKYYKKYYKKKKKK.",
    "KKKKKKKKKKKKKK..",
    "KKK.KKKK.KK.....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "...KK..KK.......",
    "...KK..KK.......",
    "..KKK..KKK......",
]

BATMAN_KICK = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKK......",
    ".KKKKKKKKK......",
    "KKKYYKKYYKKK....",
    "KKKKKKKKKKKK....",
    "KKK.KKKK.KKK....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKKKK......",
    "....K..KKKK.....",
    "....K..KKKKK....",
    "....K..K..KK....",
    "...KK..K....KK..",
    "..KK..KK....KKK.",
    ".KKK..KK......KK",
    "KK....KK........",
    "K....KK.........",
    "....KKK.........",
    "...KK...........",
]

BATMAN_THROW = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKK......",
    ".KKKKKKKKKKK....",
    "KKKYYKKYYKKSK...",
    "KKKKKKKKKKKKK...",
    "KKK.KKKK.KKK....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "....K..K........",
    "...KK..KK.......",
    "...KK..KK.......",
    "..KKK..KKK......",
]

BATMAN_SLIDE = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKKKKK...",
    ".KKKKKKKKKKKKK..",
    "KKKYYKKYYKKKK...",
    "KKKKKKKKKKKK....",
    "KKKKKKKKKKKKKK..",
    "KKKKKKKKKKKKKKKK",
    ".KKKKKKKKKKKKKK.",
    "..KKKK....KKKK..",
    "...KK......KK...",
    "................",
    "................",
    "................",
]

BATMAN_DIVEKICK = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SSSSSSS......",
    "..KKSSSSKK......",
    ".KKKKKKKKK......",
    "KKKYYKKYYKKK....",
    "KKKKKKKKKKKK....",
    "KKK.KKKK.KKK....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "....KKKK........",
    "....KKKKK.......",
    "....K..KKK......",
    "....K...KKK.....",
    "....K....KKK....",
    "....K.....KKK...",
    "...KK......KKK..",
    "...KK.......KKK.",
    "..KKK........KK.",
    "..KKK.........K.",
]

BATMAN_HURT = [
    "....KKKK........",
    "...KKKKKK.......",
    "..KK.KK.KK......",
    "..KKKKKKKK......",
    "...KSSSSK.......",
    "...SROOORS......",
    "..KKSSSSKK......",
    ".KKKKKKKKK......",
    "KKKYYKKYYKKK....",
    "KKKKKKKKKKKK....",
    "KKK.KKKK.KKK....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "...K..K.K.......",
    "..K...K..K......",
    ".K....K...K.....",
    ".K....K...K.....",
    "K.....K....K....",
    "K.....K....K....",
    "K....KK....K....",
    ".KK..KK...KK....",
    ".KK..KK...KK....",
    "..KKK..KKKK.....",
]

# ----------------------------------------------------------------------
# Enemies (16x24 unless noted)
# ----------------------------------------------------------------------

CLOWN_BASHER_A = [
    "....RRRR........",
    "...RRWWRR.......",
    "..RR.WW.RR......",
    "..RRWWWWRR......",
    "..WWSSSSWW......",
    ".W.SKSSKS.W.....",
    ".W.SSSSSS.W.....",
    "..W.SOOS.W......",
    "...WSSSSW.......",
    "..WMMWWMMW......",
    ".WMMMMMMMMW.....",
    "WMMMMMMMMMMW....",
    "WMMMYMMMYMMW....",
    "WMMMMMMMMMMW....",
    ".WMMMMMMMMW.....",
    "..MMMM.MMMM.....",
    "..MMMM.MMMM.....",
    "..MM....MM......",
    "..MM....MM......",
    ".MMM....MMM.....",
    ".LL......LL.....",
    ".LL......LL.....",
    "LLLL....LLLL....",
    "LLLL....LLLL....",
]

CLOWN_BASHER_B = [
    "....RRRR........",
    "...RRWWRR.......",
    "..RR.WW.RR......",
    "..RRWWWWRR......",
    "..WWSSSSWW......",
    ".W.SKSSKS.W.....",
    ".W.SSSSSS.W.....",
    "..W.SOOS.W......",
    "...WSSSSW.......",
    "..WMMWWMMW......",
    ".WMMMMMMMMW.....",
    "WMMMMMMMMMMW....",
    "WMMMYMMMYMMW....",
    "WMMMMMMMMMMW....",
    ".WMMMMMMMMW.....",
    ".MMMMM.MMM......",
    "MMMMMM.MMM......",
    "MMM.....MMM.....",
    "MMM.....MMM.....",
    "MMMM.....MMM....",
    "LLL......LLL....",
    "LLL......LLL....",
    "LLLL.....LLL....",
    "LLLL.....LLL....",
]

JACK_IN_BOX_CLOSED = [
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "................",
    "PPPPPPPPPPPPPPPP",
    "PYYPPPPPPPPPPYYP",
    "PYYPMMPPPPMMPYYP",
    "PPPPMMPPPPMMPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPMPPPPPPPPP",
    "PPPPPPMPPPPPPPPP",
    "PPPPPMMPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
]

JACK_IN_BOX_OPEN = [
    "....RRRRR.......",
    "...RWRRRWR......",
    "..RRWRWRWRR.....",
    "..RWSWSWSWR.....",
    "..WSSKSKSSW.....",
    "..WSSSSSSSW.....",
    "..WSOOOOOSW.....",
    "..WSSSSSSSW.....",
    "..WMMMMMMMW.....",
    "..MWMWMWMWM.....",
    "..MMMMMMMMM.....",
    "...MMMMMMM......",
    "....MMMMM.......",
    "PPPPMMMMMPPPPPPP",
    "PYYPMMMMMPPPPYYP",
    "PYYPMMPPPPMMPYYP",
    "PPPPMMPPPPMMPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPMPPPPPPPPP",
    "PPPPPPMPPPPPPPPP",
    "PPPPPMMPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
    "PPPPPPPPPPPPPPPP",
]

FIREBREATHER = [
    "....RRRR........",
    "...RRWWRR.......",
    "..RR.WW.RR......",
    "..RRWWWWRR......",
    "..WWSSSSWW......",
    ".W.SKSSKS.W.....",
    ".W.SSSSSS.W.....",
    "..W.SOO..W......",
    "...WSSOOO.......",
    "..WOOOOOOOO.....",
    ".WOOOYYYOOOOOO..",
    "WOOOYYYYOOOOOOY.",
    "WOOOYYYYOOOOY...",
    "WOOOOOOOOOO.....",
    ".WOOOOOOOO......",
    "..OOOO.OOOO.....",
    "..MMMM.MMMM.....",
    "..MM....MM......",
    "..MM....MM......",
    ".MMM....MMM.....",
    ".LL......LL.....",
    ".LL......LL.....",
    "LLLL....LLLL....",
    "LLLL....LLLL....",
]

KNIFER = [
    "....NNNN........",
    "...NNDDNN.......",
    "..NN.DD.NN......",
    "..NNDDDDNN......",
    "..DDSSSSDD......",
    ".D.SKSSKS.D.....",
    ".D.SSSSSS.D.....",
    "..D.SLLS.D......",
    "...DSSSSD.......",
    "..NNDDDDNN......",
    ".NNNDDDDNNNL....",
    "NNNNDDDDNNNNL...",
    "NNNNDDDDNNNN....",
    "NNNNDDDDNNNN....",
    ".NNNDDDDNNN.....",
    "..NNNN.NNNN.....",
    "..NNNN.NNNN.....",
    "..NN....NN......",
    "..NN....NN......",
    ".NNN....NNN.....",
    ".LL......LL.....",
    ".LL......LL.....",
    "LLLL....LLLL....",
    "LLLL....LLLL....",
]

# Joker midboss (20x28) — purple suit, green hair
JOKER_MIDBOSS = [
    "....EEEEEE..........",
    "...EEEEEEEE.........",
    "..EEEEEEEEEE........",
    "..EEEWWSSWWEE.......",
    "..EESKWWWWKSEE......",
    "...SSSSSSSSSS.......",
    "...SSSWWWWSSS.......",
    "...SSWRRRRWSS.......",
    "....SSSSSSSS........",
    "....SSWMMWSS........",
    "....SSWWWWSS........",
    "...PPPPPPPPPP.......",
    "..PPPPYYYYPPPP......",
    "..PPPYYYYYYPPP......",
    "..PPPYYYYYYPPP......",
    "..PPPYYYYYYPPP......",
    "..PPPPYYYYPPPP......",
    "..PPPPPPPPPPPP......",
    "..PPPP....PPPP......",
    "..PPPP....PPPP......",
    "..PPP......PPP......",
    "..PPP......PPP......",
    ".PPPP......PPPP.....",
    ".PPPP......PPPP.....",
    "LLLL........LLLL....",
    "LLLL........LLLL....",
    "LLLL........LLLL....",
    "LLLLL.......LLLLL...",
]

# Catwoman midboss (16x28) — sleek black suit, mask, claws
CATWOMAN_MIDBOSS = [
    "...K..K.........",
    "..KKK.KKK.......",
    "..KK.K.KK.......",
    "..KK.K.KK.......",
    "...KKKKK........",
    "...KSSSSK.......",
    "..KK.SS.KK......",
    "..K.KSSSK.K.....",
    "..KSSSSSSK......",
    "..KKSSSSKK......",
    ".KKKKKKKKKK.....",
    "KKKKKKKKKKKKL...",
    "KKKKKKKKKKKKLL..",
    "KKKKKKKKKKKK....",
    "KKKKKKKKKKKK....",
    "KKKKKKKKKKKK....",
    ".KKKKKKKKKK.....",
    ".KKK.KK.KKK.....",
    ".KK.KKKK.KK.....",
    ".KK.KKKK.KK.....",
    ".K..KKKK..K.....",
    ".K..KKKK..K.....",
    "....KKKK........",
    "....KKKK........",
    "...KK..KK.......",
    "...KK..KK.......",
    "..KKK..KKK......",
    "..KKK..KKK......",
]

# Penguin boss is bigger (24x32)
SKATER_CLOWN = [
    "....RRRR........",
    "...RRWWRR.......",
    "..RR.WW.RR......",
    "..RRWWWWRR......",
    "..WWSSSSWW......",
    ".W.SKSSKS.W.....",
    ".W.SSSSSS.W.....",
    "..W.SOOS.W......",
    "...WSSSSW.......",
    "..NNNNWWNN......",
    ".NNNNNNNNNN.....",
    "NNNNNNNNNNNN....",
    "NNNNYNNNYNNN....",
    "NNNNNNNNNNNN....",
    ".NNNNNNNNNN.....",
    "..NNNN.NNNN.....",
    "..NNNN.NNNN.....",
    "...LLL.LLL......",
    "..LLLLLLLLLL....",
    "LLLLLLLLLLLLLL..",
    "LLLLLLLLLLLLLLLL",
    ".LLLLLLLLLLLLLL.",
    "................",
    "................",
]


PENGUIN_BOSS = [
    "........KKKKKKKK........",
    ".......KKKKKKKKKK.......",
    "......KKKKKKKKKKKK......",
    "......KKKWWKKWWKKK......",
    ".....KKKWLLWWLLWKKK.....",
    ".....KKKWLLWWLLWKKK.....",
    "......KKKKKKKKKKKK......",
    ".......KKOOOOOOKK.......",
    "......KKKOOOOOOKKK......",
    ".....KKKKKOOOOKKKKK.....",
    "....KKKKWWWWWWWKKKKK....",
    "...KKKWWWWWWWWWWWKKK....",
    "..KKKWWWWWWWWWWWWWKKK...",
    "..KKWWWWWKKKKKWWWWKKK...",
    ".KKKWWWWKKKKKKKWWWWKKK..",
    ".KKWWWWWKYYYYYKWWWWWKK..",
    ".KKWWWWWKKKKKKKWWWWWKK..",
    ".KKWWWWWWKKKKKWWWWWWKK..",
    ".KKWWWWWWWWWWWWWWWWWKK..",
    "..KKWWWWWWWWWWWWWWWKK...",
    "..KKKWWWWWWWWWWWWWKKK...",
    "...KKKWWWWWWWWWWWKKK....",
    "....KKKKWWWWWWWKKKK.....",
    ".....KKKKKKKKKKKKK......",
    "......KKKKKKKKKKK.......",
    ".....KKKK....KKKKK......",
    "....KKKK......KKKK......",
    "...OOOO........OOOO.....",
    "..OOOO..........OOOO....",
    "..OO.............OOO....",
    ".OOO..............OO....",
    "OOOO..............OOO...",
]

# ----------------------------------------------------------------------
# Projectiles & FX (small)
# ----------------------------------------------------------------------

BATARANG = [
    "...YY......YY...",
    "..YKKY....YKKY..",
    ".YKKKKY..YKKKKY.",
    "YKKKKKKYYKKKKKKY",
    "YKKKYKKKKKKYKKKY",
    "YKKKKYKKKKYKKKKY",
    "YKKKKKYKKYKKKKKY",
    "YKKKKKKKKKKKKKKY",
    "YKKKKKYKKYKKKKKY",
    "YKKKKYKKKKYKKKKY",
    ".YKKKKY..YKKKKY.",
    "..YKKY....YKKY..",
    "...YY......YY...",
]

KNIFE_PROJ = [
    "L.......",
    "LL......",
    "LLL.....",
    "LLLL....",
    "LLLLL...",
    ".LLLLD..",
    "..LLDD..",
    "...DDD..",
]

FIRE_PROJ = [
    ".YYY.....",
    "YYOOY....",
    "YOOROY...",
    "YOROOY...",
    ".YOOY....",
    "..YY.....",
]

# ----------------------------------------------------------------------
# Goal flag (24x32) — bat-flag pole at end of stage
# ----------------------------------------------------------------------

GOAL_FLAG = [
    "...YYYYYYYYYY...........",
    "..YKKKKKKKKKKY..........",
    ".YKKKYKKYYKKYKY.........",
    ".YKKYY.YYYY.YYY.........",
    ".YKKKKYY..YYKKY.........",
    ".YKYY.YYYYYYYY..........",
    ".YKKKYKKYYKKYY..........",
    "..YYYYYYYYYYYY..........",
    "...YYYYYYYYY............",
    "....YYYYYYY.............",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "....KK..................",
    "...DDDD.................",
]

# ----------------------------------------------------------------------
# Tile / scenery (16x16)
# ----------------------------------------------------------------------

TILE_GROUND = [
    "GGGGGGGGGGGGGGGG",
    "GLLGGGLLGGGLLGGG",
    "GGGGGGGGGGGGGGGG",
    "GGGLLGGGLLGGGLLG",
    "GGGGGGGGGGGGGGGG",
    "GLLGGGLLGGGLLGGG",
    "GDGGGGGGDGGGGGGG",
    "DDDDDDDDDDDDDDDD",
    "DDDDDDDDDDDDDDDD",
    "DDDDDDDDDDDDDDDD",
    "KDDDDDDDDDDDDDDD",
    "KKDDDDDDDDDDDDDD",
    "KKKDDDDDDDDDDDDD",
    "KKKKDDDDDDDDDDDD",
    "KKKKKDDDDDDDDDDD",
    "KKKKKKKKKKKKKKKK",
]

TILE_BRICK = [
    "BBBBBBBBBBBBBBBB",
    "BDDDDDDDDDDDDDDB",
    "BDDDDDDDDDDDDDDB",
    "BDDDDDDDDDDDDDDB",
    "BBBBBBBBBBBBBBBB",
    "BDDDDDDDDDDDDDDB",
    "BDDDDDDDDDDDDDDB",
    "BBBBBBBBBBBBBBBB",
    "BBBBBBBBBBBBBBBB",
    "BDDDDDDDDDDDDDDB",
    "BDDDDDDDDDDDDDDB",
    "BDDDDDDDDDDDDDDB",
    "BBBBBBBBBBBBBBBB",
    "BDDDDDDDDDDDDDDB",
    "BDDDDDDDDDDDDDDB",
    "BBBBBBBBBBBBBBBB",
]

TILE_SNOW = [
    "QQQQQQQQQQQQQQQQ",
    "QWWWWWWWQQQWWWQQ",
    "WWWWWWWWWWWWWWWQ",
    "WLLLLLLWWWLLWWLW",
    "WLLLLLLWWWLLWWLW",
    "WLLLLLLLLLLLLLLL",
    "LLLLLLLLLLLLLLLL",
    "LLLLLLLLLLLLLLLL",
    "LLLLLLLLLLLLLLLL",
    "LLLLLLLLLLLLLLLL",
    "LLGLGLGLGLGGLLGL",
    "LGLLLGLGGLGLGLGL",
    "GLLGLLGLGLLLGGLG",
    "GGGGGGGGGGGGGGGG",
    "DGGGDGGGDGGGGGDG",
    "DDDDDDDDDDDDDDDD",
]


# ----------------------------------------------------------------------
# Cache: build sprites once, mirror lazily
# ----------------------------------------------------------------------

@cache
def get(name: str) -> pygame.Surface:
    """Return the named sprite surface (built lazily, cached)."""
    grid = SPRITE_REGISTRY[name]
    return make_sprite(grid)


@cache
def get_flipped(name: str) -> pygame.Surface:
    return pygame.transform.flip(get(name), True, False)


SPRITE_REGISTRY: dict[str, list[str]] = {
    "batman_idle": BATMAN_IDLE,
    "batman_walk_a": BATMAN_WALK_A,
    "batman_walk_b": BATMAN_WALK_B,
    "batman_jump": BATMAN_JUMP,
    "batman_punch": BATMAN_PUNCH,
    "batman_kick": BATMAN_KICK,
    "batman_throw": BATMAN_THROW,
    "batman_hurt": BATMAN_HURT,
    "batman_slide": BATMAN_SLIDE,
    "batman_divekick": BATMAN_DIVEKICK,
    "clown_a": CLOWN_BASHER_A,
    "clown_b": CLOWN_BASHER_B,
    "jack_closed": JACK_IN_BOX_CLOSED,
    "jack_open": JACK_IN_BOX_OPEN,
    "firebreather": FIREBREATHER,
    "knifer": KNIFER,
    "skater": SKATER_CLOWN,
    "penguin": PENGUIN_BOSS,
    "joker": JOKER_MIDBOSS,
    "catwoman": CATWOMAN_MIDBOSS,
    "batarang": BATARANG,
    "knife_proj": KNIFE_PROJ,
    "fire_proj": FIRE_PROJ,
    "tile_ground": TILE_GROUND,
    "tile_brick": TILE_BRICK,
    "tile_snow": TILE_SNOW,
    "goal_flag": GOAL_FLAG,
}
