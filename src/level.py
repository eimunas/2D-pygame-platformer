"""Build a level from a list of strings. One character = one 16x16 tile cell.

Tiles:        G grass    D dirt     . empty
Player:       P  (feet on the bottom of this cell)
Trees:        s sakura   p pine     b bamboo      (behind the player)
Rocks:        r pebbles  m boulder  c cairn       (in front of the player)

Trees, rocks and the player stand on the bottom edge of their cell,
centred horizontally - so put them directly above a ground tile.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.sprites import Player, Rock, Tree
from src.tilemap import Tilemap

if TYPE_CHECKING:
    from src.game import Game

TILES = {"G": "grass", "D": "dirt"}
TREES = {"s": "sakura", "p": "pine", "b": "bamboo"}
ROCKS = {"r": "pebbles", "m": "boulder", "c": "cairn"}

# 45 x 9 tiles (three screens wide). Each row is split into 15-column
# chunks only to make it easier to read - Python joins adjacent strings.
#
# The player jumps ~2.6 tiles, so every platform here is at most 2 tiles
# above the place you jump from.
DEMO_LEVEL = [
    "..............." "..............." "...............",
    "..............." "..............." "............GGG",
    "..............." "..............." "...............",
    "..........GGGG." "..........GGGG." "........GGGG...",
    "..........DDDD." "..............." "........DDDD...",
    ".......GG......" ".......GG......" ".....GG........",
    ".s..c.P....m..." ".p..b.rDD......" ".s.....m.....c.",
    "GGGGGGGGGGGGGGG" "GGGGGGGGGGGGGGG" "GGGGGGGGGGGGGGG",
    "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD" "DDDDDDDDDDDDDDD",
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
            elif ch == "P":
                game.player = Player(game, feet)
            elif ch != ".":
                raise ValueError(f"Unknown level character '{ch}' at column {col}, row {row}")
    return tilemap
