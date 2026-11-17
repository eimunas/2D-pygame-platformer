"""Sketch levels as a height profile instead of typing every row.

A level is a list of segments, left to right. Each segment says how wide it is
and what's there; things standing on the ground are placed by column offset.

    b = LevelBuilder(rows=16)
    b.flat(8, 12, on={2: "P", 5: "s"})   # 8 columns of ground, top at row 12;
                                          # player at +2, sakura at +5
    b.bridge(5)                           # 5-wide wooden bridge at the current height
    b.gap(2)                              # 2-wide pit (bottomless)
    b.flat(6, 10, on={3: "A"})            # ground 2 rows higher (a 2-tile step up)
    print(b.as_python("MY_LEVEL"))

    LevelBuilder(rows=16, ceiling_air=(5, 6))   # caves: a rock ceiling 5-6 rows above the floor

Characters are the same as in src/level.py (P player, E samurai, A archer, N shinobi, M trader,
X exit gate, C cave exit, S rune seal, B golem, Z skeleton, W banshee, U guardian, o/j/K cave props, s/p/b trees, l/T/u/v props, r/m/c rocks).

Run this file to print the built-in levels as Python code:
    python tools/level_builder.py
"""


import math


class LevelBuilder:
    def __init__(self, rows=16, ceiling_air=None):
        """ceiling_air: (min, max) rows of open air between the floor and a wavy
        rock ceiling (caves); None = open sky."""
        self.rows = rows
        self.ceiling_air = ceiling_air
        self.columns = []          # per column: ("ground", top) | ("gap",) | ("bridge", deck_row)
        self.things = {}           # column -> character standing on the ground there
        self.height = None         # current ground top row (for bridges)

    def flat(self, width, top, on=None):
        start = len(self.columns)
        self.columns += [("ground", top)] * width
        self.height = top
        for offset, ch in (on or {}).items():
            assert 0 <= offset < width, f"offset {offset} outside a {width}-wide segment"
            self.things[start + offset] = ch
        return self

    def gap(self, width):
        self.columns += [("gap",)] * width
        return self

    def bridge(self, width, on=None):
        assert self.height is not None, "a bridge needs ground before it"
        start = len(self.columns)
        self.columns += [("bridge", self.height)] * width
        for offset, ch in (on or {}).items():
            self.things[start + offset] = ch
        return self

    # ------------------------------------------------------------ output
    def build(self):
        grid = [["."] * len(self.columns) for _ in range(self.rows)]
        last_surface = self.rows - 1
        for c, col in enumerate(self.columns):
            if col[0] == "ground":
                top = col[1]
                grid[top][c] = "G"
                for r in range(top + 1, self.rows):
                    grid[r][c] = "D"
                surface = top
            elif col[0] == "bridge":
                grid[col[1]][c] = "="
                surface = col[1]
            else:
                surface = None
            if c in self.things:
                assert surface is not None, f"'{self.things[c]}' at column {c} has nothing to stand on"
                assert grid[surface - 1][c] == ".", f"column {c}: something is already there"
                grid[surface - 1][c] = self.things[c]
            if self.ceiling_air:
                last_surface = surface if surface is not None else last_surface
                self.add_ceiling(grid, c, last_surface)
        return ["".join(row) for row in grid]

    def add_ceiling(self, grid, c, surface):
        """Rock from the top of the map down to `air` rows above the floor
        (smoothly wavy, so stalactite edges vary along the cave)."""
        lo, hi = self.ceiling_air
        wave = 0.5 + 0.25 * math.sin(c * 0.53) + 0.25 * math.sin(c * 0.21 + 1.3)
        air = lo + round((hi - lo) * wave)
        for r in range(0, max(0, surface - air)):
            if grid[r][c] == ".":
                grid[r][c] = "D"

    def as_python(self, name, chunk=15):
        lines = [f"{name} = ["]
        for row in self.build():
            parts = [row[i:i + chunk] for i in range(0, len(row), chunk)]
            lines.append("    " + " ".join(f'"{p}"' for p in parts) + ",")
        lines.append("]")
        return "\n".join(lines)


# ====================================================================== levels
def bamboo_valley():
    """Stage 2: ridge start -> valley with bamboo -> bridges & a pit -> archer
    ridges -> high bridge -> down to the exit."""
    b = LevelBuilder(rows=16)
    b.flat(8, 9, on={2: "P", 6: "v"})              # start ridge
    b.flat(4, 10)
    b.flat(4, 11, on={2: "r"})
    b.flat(6, 12, on={1: "b", 4: "u"})             # valley floor
    b.bridge(5)                                    # first gap
    b.flat(8, 12, on={2: "b", 5: "E"})             # samurai in the grove
    b.flat(5, 11)
    b.flat(5, 10, on={2: "A"})                     # archer ledge
    b.gap(2)                                       # jump it
    b.flat(6, 10, on={1: "l", 4: "c"})
    b.flat(4, 11)
    b.flat(10, 12, on={1: "b", 4: "E", 7: "b"})    # bamboo grove + samurai
    b.flat(3, 11)
    b.flat(3, 10, on={1: "u"})
    b.flat(3, 9)
    b.flat(8, 8, on={2: "p", 5: "A"})              # high ridge with an archer
    b.bridge(6)                                    # high bridge
    b.flat(6, 8, on={2: "E"})
    b.flat(3, 9)
    b.flat(3, 10, on={1: "v"})
    b.flat(12, 12, on={2: "m", 5: "b", 8: "A"})    # last valley, archer covering the exit path
    b.flat(8, 12, on={2: "s", 5: "X"})             # exit gate
    return b


def mountain_pass():
    """Stage 3 (taller map): foothills -> stepped cliffs -> bridges between
    peaks -> shrine on the summit."""
    b = LevelBuilder(rows=20)
    b.flat(8, 16, on={2: "P", 5: "s"})             # foothills
    b.flat(4, 15)
    b.flat(4, 14, on={2: "r"})
    b.flat(6, 13, on={3: "E"})                     # first plateau guard
    b.flat(3, 12)
    b.flat(3, 11, on={1: "v"})
    b.flat(6, 10, on={3: "A"})                     # archer on the first cliff
    b.bridge(3)
    b.flat(6, 10, on={2: "u"})
    b.flat(3, 9)
    b.flat(3, 8)
    b.flat(8, 7, on={1: "l", 4: "E"})              # plateau with a lantern
    b.bridge(7)                                    # chasm
    b.flat(5, 7, on={2: "c"})
    b.flat(3, 6)
    b.flat(6, 5, on={1: "p", 4: "A"})              # peak archer
    b.bridge(5)
    b.flat(6, 5, on={3: "E"})
    b.flat(3, 6)
    b.flat(3, 7, on={1: "u"})
    b.flat(6, 8, on={3: "A"})                      # archer in the saddle
    b.flat(3, 7)
    b.flat(3, 6)
    b.flat(3, 5, on={1: "v"})
    b.flat(12, 4, on={2: "l", 5: "E", 8: "X", 10: "l"})   # summit shrine + exit gate
    return b


def shadow_woods():
    """Stage 4: introduces the shinobi. A lone shinobi on open ground first
    (room to learn his dash), then shinobi with archer cover, a pair on a
    long flat, a samurai + shinobi team, and a last guard at the exit."""
    b = LevelBuilder(rows=16)
    b.flat(9, 11, on={2: "P", 5: "M", 7: "p"})     # quiet start: the trader waits under the pines
    b.flat(4, 12, on={2: "v"})
    b.flat(14, 12, on={3: "b", 9: "N", 12: "u"})   # 1st shinobi: long open flat to learn the dash
    b.flat(3, 11)
    b.flat(3, 10, on={1: "r"})
    b.flat(6, 9, on={3: "A"})                      # archer ledge overlooking the next flat
    b.bridge(4)
    b.flat(12, 9, on={2: "p", 7: "N"})             # shinobi under archer cover
    b.flat(3, 10)
    b.flat(4, 11, on={1: "c"})
    b.gap(2)
    b.flat(18, 11, on={2: "l", 6: "N", 12: "N", 16: "v"})   # a pair of shinobi
    b.flat(3, 10)
    b.flat(3, 9, on={1: "u"})
    b.flat(12, 9, on={2: "b", 5: "E", 8: "N", 10: "b"})     # samurai + shinobi team
    b.bridge(5)
    b.flat(6, 9, on={3: "A"})
    b.flat(3, 10)
    b.flat(4, 11, on={2: "m"})
    b.flat(14, 12, on={2: "p", 6: "N", 10: "X", 12: "l"})   # last guard + exit gate
    return b


def crimson_ridge():
    """Stage 5 (evening): a step up from Shadow Woods. A trader at the start,
    then wider pits, shinobi that leap after you, archers covering the fights,
    and mixed squads at the end."""
    b = LevelBuilder(rows=16)
    b.flat(8, 11, on={2: "P", 5: "M", 7: "s"})     # short breather: the trader waits at sunset
    b.flat(3, 12, on={1: "v"})
    b.flat(12, 12, on={4: "N", 9: "E", 11: "u"})   # shinobi + samurai right away
    b.gap(3)                                       # wider pit (double jump)
    b.flat(4, 11, on={2: "r"})
    b.flat(6, 10, on={3: "A"})                     # archer ledge
    b.bridge(5)
    b.flat(12, 10, on={2: "b", 5: "N", 8: "N", 10: "b"})   # shinobi pair under fire
    b.flat(3, 9)
    b.flat(6, 8, on={2: "A", 4: "l"})              # high archer
    b.gap(3)                                       # pit - the shinobi leap these
    b.flat(14, 9, on={2: "p", 5: "E", 8: "N", 11: "c"})   # samurai + shinobi
    b.flat(3, 10)
    b.flat(4, 11, on={1: "u"})
    b.gap(2)
    b.flat(16, 11, on={2: "l", 5: "N", 9: "N", 13: "N"})  # three shinobi on a long flat
    b.flat(3, 10)
    b.flat(5, 9, on={2: "A"})                      # archer covering the last bridge
    b.bridge(6)
    b.flat(4, 9, on={1: "v"})
    b.flat(3, 10)
    b.flat(16, 11, on={2: "m", 5: "E", 8: "N", 12: "X", 14: "l"})  # exit guards
    return b


def golems_gate():
    """Stage 6 (night): a trader under the moon, the usual enemies on the way
    (they must ALL fall to break the rune seal), then the flat arena where the
    stone golem drops in, guarding the cave entrance at the end of the map."""
    b = LevelBuilder(rows=16)
    b.flat(10, 11, on={2: "P", 5: "M", 8: "l"})    # trader under the moon
    b.flat(3, 12, on={1: "v"})
    b.flat(12, 12, on={3: "p", 6: "E", 9: "N"})    # samurai + shinobi
    b.gap(2)
    b.flat(4, 11, on={2: "r"})
    b.flat(8, 10, on={2: "A", 5: "c"})             # archer ledge
    b.bridge(5)
    b.flat(12, 10, on={2: "b", 5: "N", 8: "E", 10: "b"})   # shinobi + samurai in the bamboo
    b.flat(3, 11)
    b.flat(4, 12, on={1: "r"})
    b.gap(3)
    b.flat(10, 12, on={3: "A", 6: "N", 8: "l"})    # last guards before the arena
    b.flat(3, 11, on={1: "u"})
    b.flat(30, 11, on={1: "l", 3: "S", 17: "B", 27: "C"})   # arena: seal, golem, cave
    return b


def ancient_caves():
    """Stage 7 (inside the caves the golem guarded): rocky floor and ceiling,
    only skeletons - who rise again 5 s after falling. A trader waits at the
    cave mouth (bombs destroy skeletons for good); old mine bridges, pits,
    a high ledge, then a last hall with the passage deeper in (the exit)."""
    b = LevelBuilder(rows=16, ceiling_air=(5, 6))
    b.flat(10, 11, on={2: "P", 5: "M", 8: "o"})    # the trader, sheltering in the cave mouth
    b.flat(4, 12, on={1: "j"})
    b.flat(12, 12, on={3: "K", 7: "Z", 10: "o"})   # first skeleton, by a fallen samurai
    b.flat(3, 11)
    b.flat(6, 10, on={2: "j"})
    b.gap(2)
    b.flat(10, 10, on={2: "o", 4: "Z", 7: "j"})
    b.bridge(5)                                    # old mine bridge
    b.flat(12, 10, on={2: "K", 5: "Z", 9: "Z"})    # a pair
    b.flat(3, 11)
    b.flat(4, 12, on={1: "r"})
    b.gap(3)
    b.flat(14, 12, on={2: "j", 5: "Z", 9: "o", 11: "Z"})
    b.flat(3, 11)
    b.flat(3, 10, on={1: "j"})
    b.flat(10, 9, on={3: "Z", 6: "K"})             # high ledge
    b.bridge(6)
    b.flat(4, 9)
    b.flat(3, 10)
    b.flat(18, 11, on={2: "o", 4: "Z", 8: "Z", 11: "j", 15: "C"})   # last hall + the way deeper
    return b


def wailing_depths():
    """Stage 8, deeper in the caves: introduces the banshee. A lone banshee first
    (room to learn her scream), one waiting on a bridge, banshees
    backed by skeletons, a pair on a high ledge, then the passage onwards."""
    b = LevelBuilder(rows=16, ceiling_air=(5, 6))
    b.flat(10, 11, on={2: "P", 5: "M", 8: "o"})    # the trader again
    b.flat(4, 12, on={1: "j"})
    b.flat(14, 12, on={4: "K", 10: "W", 12: "o"})  # first banshee, alone: learn the scream
    b.flat(3, 11)
    b.gap(3)
    b.flat(10, 11, on={2: "j", 6: "Z"})
    b.bridge(6, on={3: "W"})                       # one waits on the old bridge
    b.flat(12, 11, on={2: "o", 5: "W", 9: "Z"})    # banshee + skeleton
    b.flat(3, 10)
    b.flat(4, 9, on={1: "j"})
    b.gap(2)
    b.flat(12, 9, on={3: "W", 8: "W", 10: "K"})    # two banshees on a ledge
    b.flat(3, 10)
    b.flat(4, 11)
    b.gap(3)
    b.flat(14, 12, on={2: "Z", 7: "W", 11: "Z"})   # screamed at while skeletons close in
    b.flat(3, 11)
    b.flat(18, 11, on={2: "o", 5: "W", 9: "Z", 15: "C"})   # last stand, then onwards
    return b


def guardian_halls():
    """Stage 9, an ancient fortress under the mountain: introduces the guardian
    (spear + shield, arrows bounce off until it breaks). Guardians are rare -
    only three, each with room around him (no skeleton right behind him, so
    you aren't caught between a spear and a sword that keeps getting up):
    one alone first, one holding the line while a banshee screams, and one in
    the last hall before the old shrine gate out of the depths."""
    b = LevelBuilder(rows=16, ceiling_air=(5, 6))
    b.flat(10, 11, on={2: "P", 5: "M", 8: "l"})    # the trader; stone lanterns light the halls
    b.flat(4, 12, on={1: "j"})
    b.flat(16, 12, on={3: "K", 11: "U", 14: "l"})  # first guardian, alone: learn his thrust
    b.flat(3, 11)
    b.gap(3)                                       # too heavy to jump: he can't follow you
    b.flat(10, 11, on={2: "o", 6: "Z"})
    b.bridge(6)
    b.flat(14, 11, on={3: "U", 10: "W", 12: "l"})  # he holds the line while she screams
    b.flat(3, 10)
    b.flat(4, 9, on={1: "j"})
    b.gap(2)
    b.flat(12, 9, on={3: "Z", 8: "j"})            # just a skeleton up here
    b.flat(3, 10)
    b.flat(4, 11, on={1: "o"})
    b.gap(3)
    b.flat(16, 12, on={2: "W", 7: "l", 11: "Z"})   # a banshee and a skeleton
    b.flat(3, 11)
    b.flat(20, 11, on={2: "l", 9: "U", 14: "l", 17: "X"})   # the last hall: one guardian, the gate out
    return b


if __name__ == "__main__":
    print(bamboo_valley().as_python("BAMBOO_VALLEY"))
    print()
    print(mountain_pass().as_python("MOUNTAIN_PASS"))
    print()
    print(shadow_woods().as_python("SHADOW_WOODS"))
    print()
    print(crimson_ridge().as_python("CRIMSON_RIDGE"))
    print()
    print(golems_gate().as_python("GOLEMS_GATE"))
    print()
    print(ancient_caves().as_python("ANCIENT_CAVES"))
    print()
    print(wailing_depths().as_python("WAILING_DEPTHS"))
    print()
    print(guardian_halls().as_python("GUARDIAN_HALLS"))
