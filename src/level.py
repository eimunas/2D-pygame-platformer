"""Build a level from a list of strings. One character = one 16x16 tile cell.

Tiles:        G grass    D dirt     . empty
              =  wooden bridge (one-way: jump up through it, hold S to drop)
Player:       P  (feet on the bottom of this cell)
Enemies:      E  samurai (patrols, chases and slashes the ninja when he spots him)
              A  samurai archer (spots from far away, keeps distance, shoots arcing arrows)
              N  shinobi (enemy ninja: fast, dagger stabs, dashes at you every 3 s)
Trees:        s sakura   p pine     b bamboo                 (behind the player)
Props:        l lantern  T torii                             (behind the player)
Exit:         X  torii gate - walk through it to finish the level
              C  cave entrance - the exit of a boss level (opens once the boss is defeated)
Boss arena:   S  rune seal: the arena entrance (closed until every other enemy is defeated)
              B  where the stone golem lands (he drops in when you walk past the seal)
NPCs:         M  wandering trader (merchant) - press E next to him to open the shop
Rocks/plants: r pebbles  m boulder  c cairn  u bush  v small bush   (in front)

Trees, props, rocks and the player stand on the bottom edge of their cell,
centred horizontally - so put them directly above a ground tile.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.sprites import Archer, CaveEntrance, Enemy, ExitGate, Player, Prop, Rock, Shinobi, Trader, Tree
from src.tilemap import Tilemap

if TYPE_CHECKING:
    from src.game import Game

TILES = {"G": "grass", "D": "dirt", "=": "bridge"}
TREES = {"s": "sakura", "p": "pine", "b": "bamboo"}
ROCKS = {"r": "pebbles", "m": "boulder", "c": "cairn"}
PROPS = {"l": "lantern", "T": "torii", "u": "bush", "v": "bush_small"}

# "Shrine Hill": 90 x 16 tiles. Meadow -> stepped climb -> rocky step ->
# bridge over a ravine -> summit with a torii -> descent past a cliff and a
# bamboo grove -> meadow. Each row is split into 15-column chunks only to
# make it easier to read - Python joins adjacent strings.
HILL_LEVEL = [
    r"..............." r"..............." r"..............." r"..............." r"..............." r"...............",
    r"..............." r"..............." r"..............." r"..............." r"..............." r"...............",
    r"..............." r"..............." r"..............." r"..............." r"..............." r"...............",
    r"..............." r"..............." r"..............." r"..............." r"..............." r"...............",
    r"..............." r"..............." r"..............." r"..............." r"..............." r"...............",
    r"..............." r"..............." r"..............." r"v..T.A........." r"..............." r"...............",
    r"..............." r"..............." r"c..........pE.G" r"GGGGGGG.m......" r"..............." r"...............",
    r"..............." r"..........Al.GG" r"GG=======GGGGGD" r"DDDDDDDGGGGG.p." r"..............." r"...............",
    r"..............." r".......v.GGGGDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDGGG" r"G.............." r"...............",
    r"..............." r"...u.GGGGDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"D...b.........." r"lA.............",
    r".............r." r"GGGGGDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DGGGGGGGE.u..GG" r"GGGG...........",
    r"...P..s...GGGGG" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDGGGGGDD" r"DDDDG.r..sE.Xu.",
    r"GGGGGGGGGGDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDGGGGGGGGGG",
    r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD",
    r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD",
    r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD",
]


# "Bamboo Valley": 122 x 16. Ridge start -> valley with bamboo -> bridges and a
# pit -> archer ridges -> high bridge -> exit. Built with tools/level_builder.py.
BAMBOO_VALLEY = [
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "...p..A........" "..E............" "..............." "..",
    "..P...v........" "..............." "..............." "..............." "..............." ".GGGGGGGG======" "GGGGGG........." "..............." "..",
    "GGGGGGGG......." "..............." "............A.." "...l..c........" "...........u.GG" "GDDDDDDDD......" "DDDDDDGGG.v...." "..............." "..",
    "DDDDDDDDGGGG..r" "..............." "..........GGGGG" "..GGGGGG......." "..........GGGDD" "DDDDDDDDD......" "DDDDDDDDDGGG..." "..............." "..",
    "DDDDDDDDDDDDGGG" "G.b..u........b" "..E..GGGGGDDDDD" "..DDDDDDGGGG.b." ".E..b..GGGDDDDD" "DDDDDDDDD......" "DDDDDDDDDDDD..m" "..b..A.....s..X" "..",
    "DDDDDDDDDDDDDDD" "DGGGGGG=====GGG" "GGGGGDDDDDDDDDD" "..DDDDDDDDDDGGG" "GGGGGGGDDDDDDDD" "DDDDDDDDD......" "DDDDDDDDDDDDGGG" "GGGGGGGGGGGGGGG" "GG",
    "DDDDDDDDDDDDDDD" "DDDDDDD.....DDD" "DDDDDDDDDDDDDDD" "..DDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDD......" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "DDDDDDDDDDDDDDD" "DDDDDDD.....DDD" "DDDDDDDDDDDDDDD" "..DDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDD......" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "DDDDDDDDDDDDDDD" "DDDDDDD.....DDD" "DDDDDDDDDDDDDDD" "..DDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDD......" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
]

# "Mountain Pass": 122 x 20 (taller). Foothills -> stepped cliffs -> bridges
# between peaks -> shrine on the summit. Built with tools/level_builder.py.
MOUNTAIN_PASS = [
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." ".......l..E..X." "l.",
    "..............." "..............." "..............." "..............." ".............p." ".A.........E..." "..............." "...v.GGGGGGGGGG" "GG",
    "..............." "..............." "..............." "..............." "............GGG" "GGG=====GGGGGG." "..............." "..GGGDDDDDDDDDD" "DD",
    "..............." "..............." "..............." ".....l..E......" "......c..GGGDDD" "DDD.....DDDDDDG" "GG.u..........G" "GGDDDDDDDDDDDDD" "DD",
    "..............." "..............." "..............." "....GGGGGGGG===" "====GGGGGDDDDDD" "DDD.....DDDDDDD" "DDGGG...A..GGGD" "DDDDDDDDDDDDDDD" "DD",
    "..............." "..............." "..............." ".GGGDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDGGGGGGDDDD" "DDDDDDDDDDDDDDD" "DD",
    "..............." "..............." ".A.......u...GG" "GDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "..............." "...........v.GG" "GGGG===GGGGGGDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "..............." "..........GGGDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "..............." "....E..GGGDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "..............r" ".GGGGGGDDDDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "............GGG" "GDDDDDDDDDDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "..P..s..GGGGDDD" "DDDDDDDDDDDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "GGGGGGGGDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD...DDDDDDDD" "DDDDDDDDDDDD..." "....DDDDDDDDDDD" "DDD.....DDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DD",
]

# "Shadow Woods": a trader at the start; introduces the shinobi. Open flat to learn his dash -> shinobi
# under archer cover -> a pair -> samurai + shinobi -> exit. Built with tools/level_builder.py.
SHADOW_WOODS = [
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "............",
    "..............." "..............." "......A........" "p....N........." "..............." "...........u..." "b..E..N.b......" "...A..........." "............",
    "..............." "..............." ".r.GGGGGG====GG" "GGGGGGGGGG....." "..............." "..........GGGGG" "GGGGGGGGGG=====" "GGGGGG........." "............",
    "..P..M.p......." "..............." "GGGDDDDDD....DD" "DDDDDDDDDDGGG.c" "......l...N...." ".N...v.GGGDDDDD" "DDDDDDDDDD....." "DDDDDDGGG..m..." "............",
    "GGGGGGGGG..v..." ".b.....N..u.GGG" "DDDDDDDDD....DD" "DDDDDDDDDDDDDGG" "GG..GGGGGGGGGGG" "GGGGGGGDDDDDDDD" "DDDDDDDDDD....." "DDDDDDDDDGGGG.." "p...N...X.l.",
    "DDDDDDDDDGGGGGG" "GGGGGGGGGGGGDDD" "DDDDDDDDD....DD" "DDDDDDDDDDDDDDD" "DD..DDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDD....." "DDDDDDDDDDDDDGG" "GGGGGGGGGGGG",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDD....DD" "DDDDDDDDDDDDDDD" "DD..DDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDD....." "DDDDDDDDDDDDDDD" "DDDDDDDDDDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDD....DD" "DDDDDDDDDDDDDDD" "DD..DDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDD....." "DDDDDDDDDDDDDDD" "DDDDDDDDDDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDD....DD" "DDDDDDDDDDDDDDD" "DD..DDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDD....." "DDDDDDDDDDDDDDD" "DDDDDDDDDDDD",
]

# "Crimson Ridge": stage 5, at sunset (evening background), trader at the start.
# A step up from Shadow Woods - wider pits the shinobi leap across, shinobi pairs
# under archer fire, three on one flat, mixed squads at the exit.
# Built with tools/level_builder.py.
CRIMSON_RIDGE = [
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." ".............A." "l.............." "..............." "..............." "..............." "..............." "......",
    "..............." "..............." "..............." "...........GGGG" "GG.....p..E..N." ".c............." "..............." "....A.........v" "..............." "......",
    "..............." "..............." "...A.........b." ".N..N.b.GGGDDDD" "DD...GGGGGGGGGG" "GGGG..........." "..............." "..GGGGG======GG" "GG............." "......",
    "..P..M.s......." ".............r." "GGGGGG=====GGGG" "GGGGGGGGDDDDDDD" "DD...DDDDDDDDDD" "DDDDGGG.u......" "l..N...N...N..G" "GGDDDDD......DD" "DDGGG..m..E..N." "..X.l.",
    "GGGGGGGG.v....." "N....E.u...GGGG" "DDDDDD.....DDDD" "DDDDDDDDDDDDDDD" "DD...DDDDDDDDDD" "DDDDDDDGGGG..GG" "GGGGGGGGGGGGGGD" "DDDDDDD......DD" "DDDDDGGGGGGGGGG" "GGGGGG",
    "DDDDDDDDGGGGGGG" "GGGGGGGG...DDDD" "DDDDDD.....DDDD" "DDDDDDDDDDDDDDD" "DD...DDDDDDDDDD" "DDDDDDDDDDD..DD" "DDDDDDDDDDDDDDD" "DDDDDDD......DD" "DDDDDDDDDDDDDDD" "DDDDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDD...DDDD" "DDDDDD.....DDDD" "DDDDDDDDDDDDDDD" "DD...DDDDDDDDDD" "DDDDDDDDDDD..DD" "DDDDDDDDDDDDDDD" "DDDDDDD......DD" "DDDDDDDDDDDDDDD" "DDDDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDD...DDDD" "DDDDDD.....DDDD" "DDDDDDDDDDDDDDD" "DD...DDDDDDDDDD" "DDDDDDDDDDD..DD" "DDDDDDDDDDDDDDD" "DDDDDDD......DD" "DDDDDDDDDDDDDDD" "DDDDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDD...DDDD" "DDDDDD.....DDDD" "DDDDDDDDDDDDDDD" "DD...DDDDDDDDDD" "DDDDDDDDDDD..DD" "DDDDDDDDDDDDDDD" "DDDDDDD......DD" "DDDDDDDDDDDDDDD" "DDDDDD",
]

# "Golem's Gate": stage 6, at night. A trader under the moon, the usual enemies
# on the way (all of them must fall to break the rune seal S), then the arena:
# the stone golem drops in at B and guards the cave entrance C (the exit).
# Built with tools/level_builder.py.
GOLEMS_GATE = [
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "..............." "..............." "..............." "..............." "..............." "....",
    "..............." "..............." "...A..c........" ".b..N..E.b....." "..............." "..............." "..............." "....",
    "..P..M..l......" "..............r" ".GGGGGGGG=====G" "GGGGGGGGGGG...." "..............." "..u..l.S......." "......B........" ".C..",
    "GGGGGGGGGG.v..." ".p..E..N....GGG" "GDDDDDDDD.....D" "DDDDDDDDDDDGGG." "r........A..N.l" ".GGGGGGGGGGGGGG" "GGGGGGGGGGGGGGG" "GGGG",
    "DDDDDDDDDDGGGGG" "GGGGGGGGGG..DDD" "DDDDDDDDD.....D" "DDDDDDDDDDDDDDG" "GGG...GGGGGGGGG" "GDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDD..DDD" "DDDDDDDDD.....D" "DDDDDDDDDDDDDDD" "DDD...DDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDD..DDD" "DDDDDDDDD.....D" "DDDDDDDDDDDDDDD" "DDD...DDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDD..DDD" "DDDDDDDDD.....D" "DDDDDDDDDDDDDDD" "DDD...DDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDD",
]


# Levels in play order. Reaching the exit gate (X) loads the next one.
LEVELS = [
    # "coins": how many coins hide at random spots in the stage (each found only once)
    {"name": "Shrine Hill", "layout": HILL_LEVEL, "coins": 1},
    {"name": "Bamboo Valley", "layout": BAMBOO_VALLEY, "coins": 1},
    {"name": "Mountain Pass", "layout": MOUNTAIN_PASS, "coins": 1},
    {"name": "Shadow Woods", "layout": SHADOW_WOODS, "coins": 1},
    # "background": a theme from settings.BACKGROUND_THEMES (default "day")
    {"name": "Crimson Ridge", "layout": CRIMSON_RIDGE, "coins": 1, "background": "evening"},
    # "night": dark-blue veil over the world (settings.NIGHT_TINT)
    {"name": "Golem's Gate", "layout": GOLEMS_GATE, "coins": 1, "background": "night", "night": True},
]


def load_level(game: Game, layout):
    """Create the tilemap, decorations and player. Returns the Tilemap."""
    rows, cols = len(layout), max(len(line) for line in layout)
    tilemap = Tilemap(game, cols, rows)
    ts = tilemap.tile_size

    for row, line in enumerate(layout):
        for col, ch in enumerate(line):
            feet = (col * ts + ts // 2, (row + 1) * ts)  # midbottom of the cell
            if ch in TILES:
                tilemap.set_tile(col, row, TILES[ch])
            elif ch in TREES:
                Tree(game, TREES[ch], feet)
            elif ch in ROCKS:
                Rock(game, ROCKS[ch], feet)
            elif ch in PROPS:
                Prop(game, PROPS[ch], feet)
            elif ch == "P":
                game.player = Player(game, feet)
            elif ch == "E":
                Enemy(game, feet)
            elif ch == "A":
                Archer(game, feet)
            elif ch == "N":
                Shinobi(game, feet)
            elif ch == "M":
                Trader(game, feet)
            elif ch == "X":
                ExitGate(game, feet)
            elif ch == "C":
                CaveEntrance(game, feet)
            elif ch == "S":
                game.seal_pos = feet
            elif ch == "B":
                game.boss_spawn = feet
            elif ch != ".":
                raise ValueError(f"Unknown level character '{ch}' at column {col}, row {row}")
    return tilemap
