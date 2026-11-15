"""Build a level from a list of strings. One character = one 16x16 tile cell.

Tiles:        G grass    D dirt     . empty
              =  wooden bridge (one-way: jump up through it, hold S to drop)
Player:       P  (feet on the bottom of this cell)
Enemies:      E  samurai (patrols, chases and slashes the ninja when he spots him)
Trees:        s sakura   p pine     b bamboo                 (behind the player)
Props:        l lantern  T torii                             (behind the player)
Rocks/plants: r pebbles  m boulder  c cairn  u bush  v small bush   (in front)

Trees, props, rocks and the player stand on the bottom edge of their cell,
centred horizontally - so put them directly above a ground tile.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.sprites import Enemy, Player, Prop, Rock, Tree
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
    r"..............." r"..............." r"..............." r"v..T..........." r"..............." r"...............",
    r"..............." r"..............." r"c..........pE.G" r"GGGGGGG.m......" r"..............." r"...............",
    r"..............." r"...........l.GG" r"GG=======GGGGGD" r"DDDDDDDGGGGG.p." r"..............." r"...............",
    r"..............." r".......v.GGGGDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDGGG" r"G.............." r"...............",
    r"..............." r"...u.GGGGDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"D...b.........." r"l..............",
    r".............r." r"GGGGGDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DGGGGGGGE.u..GG" r"GGGG...........",
    r"...P..s...GGGGG" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDGGGGGDD" r"DDDDG.r..sE..u.",
    r"GGGGGGGGGGDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDGGGGGGGGGG",
    r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD",
    r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD",
    r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DD.......DDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD" r"DDDDDDDDDDDDDDD",
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
            elif ch != ".":
                raise ValueError(f"Unknown level character '{ch}' at column {col}, row {row}")
    return tilemap
