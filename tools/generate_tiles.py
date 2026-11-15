"""Generate the Samurai-era tileset and decorations (stdlib only).

Usage (from the repo root):
    python tools/generate_tiles.py
    python tools/generate_tiles.py --preview preview.png

Output:
    assets/tiles/grass/grass_MM_V.png    16 autotile masks x 3 variants
    assets/tiles/dirt/dirt_MM_V.png      16 autotile masks x 3 variants
    assets/decorations/rocks/{pebbles,boulder,cairn}.png
    assets/decorations/trees/{sakura,pine,bamboo}/<name>_00..05.png

Autotile mask: a bit is SET when that side is EXPOSED (neighbour is empty):
    N = 1, E = 2, S = 4, W = 8      e.g. 0 = fully surrounded, 15 = lone tile
"""

import argparse
import math
import os
import random

from pixelart import Canvas, preview_sheet, rgb

N, E, S, W = 1, 2, 4, 8
VARIANTS = 3
FRAMES = 6

OUT = rgb(30, 20, 22)

DIRT = {
    "base": rgb(122, 78, 52),
    "dark": rgb(94, 58, 40),
    "light": rgb(150, 100, 66),
    "pebble": rgb(176, 152, 128),
}
GRASS = {
    "deep": rgb(36, 84, 56),
    "main": rgb(70, 136, 72),
    "hi": rgb(130, 186, 90),
    "petal": rgb(246, 188, 206),
    "flower": rgb(242, 236, 214),
}


# ================================================================== tiles
def dirt_fill(cv, rnd):
    for y in range(16):
        for x in range(16):
            r = rnd.random()
            cv.set(x, y, DIRT["dark"] if r < 0.12 else DIRT["light"] if r < 0.17 else DIRT["base"])
    for _ in range(2):  # small pebbles
        x, y = rnd.randrange(2, 13), rnd.randrange(3, 13)
        cv.set(x, y, DIRT["pebble"])
        cv.set(x + 1, y, DIRT["pebble"])
        cv.set(x, y + 1, DIRT["dark"])
        cv.set(x + 1, y + 1, DIRT["dark"])


def make_tile(kind, mask, variant):
    rnd = random.Random(f"{kind}-{mask}-{variant}")
    cv = Canvas(16, 16)
    dirt_fill(cv, rnd)

    if kind == "grass":
        if mask & N:
            for x in range(16):
                cv.set(x, 2, GRASS["hi"] if rnd.random() < 0.6 else GRASS["main"])
                cv.set(x, 3, GRASS["main"])
                cv.set(x, 4, GRASS["main"] if rnd.random() < 0.7 else GRASS["deep"])
                cv.set(x, 5, GRASS["deep"])
                if rnd.random() < 0.45:          # roots hanging into the dirt
                    cv.set(x, 6, GRASS["deep"])
            # tufts poking up: row 0 = outline tip, row 1 = blade
            tufts = set(rnd.sample(range(1, 15), 5))
            for x in range(16):
                if x in tufts:
                    cv.set(x, 0, OUT)
                    cv.set(x, 1, GRASS["hi"])
                else:
                    cv.set(x, 0, None)
                    cv.set(x, 1, OUT)
            if variant == 1:                      # a fallen sakura petal
                cv.set(rnd.randrange(3, 13), 3, GRASS["petal"])
            elif variant == 2:                    # a tiny white flower
                fx = rnd.randrange(3, 13)
                cv.set(fx, 2, GRASS["flower"])
                cv.set(fx, 1, GRASS["flower"])
        if mask & E:
            for y in range(16):
                cv.set(14, y, GRASS["main"])
                if rnd.random() < 0.5:
                    cv.set(13, y, GRASS["deep"])
        if mask & W:
            for y in range(16):
                cv.set(1, y, GRASS["main"])
                if rnd.random() < 0.5:
                    cv.set(2, y, GRASS["deep"])
        if mask & S:
            for x in range(16):
                cv.set(x, 14, GRASS["main"])
                if rnd.random() < 0.5:
                    cv.set(x, 13, GRASS["deep"])
        top = 1 if mask & N else 0   # side outlines start below the tufts
    else:  # dirt
        if mask & N:
            cv.rect(0, 0, 15, 0, OUT)
            cv.rect(0, 1, 15, 1, DIRT["light"])
        if mask & E:
            cv.rect(14, 0, 14, 15, DIRT["dark"])
        if mask & W:
            cv.rect(1, 0, 1, 15, DIRT["light"])
        if mask & S:
            cv.rect(0, 14, 15, 14, DIRT["dark"])
        top = 0

    # outlines on exposed sides
    if mask & E:
        cv.rect(15, top, 15, 15, OUT)
    if mask & W:
        cv.rect(0, top, 0, 15, OUT)
    if mask & S:
        cv.rect(0, 15, 15, 15, OUT)

    # rounded outer corners
    for bits, corner, inner in (
        (N | E, (15, 0), (14, 1)), (N | W, (0, 0), (1, 1)),
        (S | E, (15, 15), (14, 14)), (S | W, (0, 15), (1, 14)),
    ):
        if mask & bits == bits:
            cv.set(*corner, None)
            if kind == "grass" and bits & N:
                cv.set(corner[0], 1, None)    # tufts row: round the cap a bit more
            cv.set(*inner, OUT)
    return cv


# ================================================================== rocks
STONE = {
    "hi": rgb(178, 174, 162),
    "mid": rgb(128, 124, 118),
    "sh": rgb(86, 84, 84),
    "moss": rgb(92, 132, 70),
    "moss_hi": rgb(132, 172, 92),
    "rope": rgb(214, 184, 112),
    "rope_sh": rgb(160, 128, 70),
    "paper": rgb(246, 244, 236),
}


def stone_shade(rnd, moss=0.0):
    def fn(x, y, nx, ny):
        light = -(nx * 0.6 + ny * 0.8) + rnd.uniform(-0.12, 0.12)
        if ny < -moss and moss:
            return STONE["moss_hi"] if ny < -moss - 0.25 and rnd.random() < 0.7 else STONE["moss"]
        if light > 0.35:
            return STONE["hi"]
        if light < -0.3:
            return STONE["sh"]
        return STONE["mid"]
    return fn


def make_pebbles():
    rnd = random.Random("pebbles")
    cv = Canvas(16, 16)
    cv.ellipse(6, 11.5, 4.5, 3, stone_shade(rnd))
    cv.ellipse(11.5, 12.5, 3, 2, stone_shade(rnd))
    cv.outline(OUT)
    return cv


def make_boulder():
    """Mossy boulder wrapped in a shimenawa (sacred straw rope)."""
    rnd = random.Random("boulder")
    cv = Canvas(24, 16)
    cv.ellipse(12, 9, 10, 5.5, stone_shade(rnd, moss=0.45))
    for x in range(3, 21):                     # rope follows the rock's curve
        y = 9 + round(1.5 * ((x - 12) / 9) ** 2)
        cv.set(x, y, STONE["rope"])
        cv.set(x, y + 1, STONE["rope_sh"])
    for x in (7, 12, 17):                      # shide paper zig-zags
        y = 9 + round(1.5 * ((x - 12) / 9) ** 2) + 2
        cv.set(x, y, STONE["paper"])
        cv.set(x + 1, y + 1, STONE["paper"])
        cv.set(x, y + 2, STONE["paper"])
    cv.outline(OUT)
    return cv


def make_cairn():
    """Stacked zen stones."""
    rnd = random.Random("cairn")
    cv = Canvas(24, 32)
    for cx, cy, rx, ry in ((12, 27, 9, 3.5), (12.5, 20.5, 7, 3), (11.5, 14.5, 5.5, 2.5), (12, 9.5, 3.5, 2)):
        cv.ellipse(cx, cy, rx, ry, stone_shade(rnd))
        for x in range(int(cx - rx) + 1, int(cx + rx)):   # dark seam under each stone
            cv.set(x, int(cy + ry), STONE["sh"])
    cv.outline(OUT)
    return cv


# ================================================================== trees
def sway(anchor_y, amp, p, power=1.3):
    def off(y):
        if y >= anchor_y:
            return 0
        return round(amp * ((anchor_y - y) / anchor_y) ** power * math.sin(p))
    return off


def make_sakura_frames():
    rnd = random.Random("sakura")
    bark, bark_hi = rgb(92, 58, 48), rgb(132, 88, 68)
    pink = {"hi": rgb(252, 216, 228), "mid": rgb(238, 166, 192),
            "sh": rgb(206, 114, 152), "deep": rgb(166, 82, 122)}

    base = Canvas(48, 48)
    base.line(22, 46, 23, 30, bark, width=3)
    base.set(21, 46, bark)
    base.set(26, 46, bark)
    base.line(23, 34, 23, 30, bark_hi)
    base.line(24, 32, 15, 22, bark, width=2)
    base.line(25, 31, 34, 21, bark, width=2)
    base.line(23, 30, 23, 18, bark, width=2)

    def blossom(x, y, nx, ny):
        light = -(nx * 0.5 + ny * 0.85) + rnd.uniform(-0.18, 0.18)
        if light > 0.45:
            return pink["hi"]
        if light > -0.1:
            return pink["mid"]
        if light > -0.55:
            return pink["sh"]
        return pink["deep"]

    for cx, cy, rx, ry in ((24, 23, 9, 5), (11, 27, 6, 4), (37, 26, 6, 4.5),
                           (15, 20, 8, 6), (33, 19, 9, 6.5), (24, 12, 10, 7)):
        base.ellipse(cx, cy, rx, ry, blossom)
    base.set(22, 29, bark)   # trunk peeking through the canopy
    base.set(23, 29, bark)

    petals = [(rnd.randrange(8, 40), rnd.randrange(26, 29), rnd.randrange(18)) for _ in range(5)]
    frames = []
    for i in range(FRAMES):
        p = 2 * math.pi * i / FRAMES
        cv = base.shear_rows(sway(32, 1.6, p))
        cv.outline(rgb(70, 32, 44))
        for px, py, start in petals:          # falling petals, loop every 6 frames
            k = (start + i * 3) % 18
            cv.set(px - k // 3, py + k, pink["hi"])
        frames.append(cv)
    return frames


def make_pine_frames():
    rnd = random.Random("pine")
    bark, bark_hi = rgb(84, 62, 52), rgb(120, 92, 72)
    green = {"hi": rgb(126, 170, 96), "mid": rgb(68, 118, 72),
             "sh": rgb(40, 80, 56), "deep": rgb(28, 58, 44)}

    base = Canvas(48, 48)
    for y in range(18, 47):                    # twisting trunk
        x = 22 + round(3 * math.sin((47 - y) / 9))
        base.rect(x, y, x + 2, y, bark)
        if y % 3 == 0:
            base.set(x, y, bark_hi)
    base.line(22, 31, 12, 27, bark, width=2)
    base.line(24, 25, 34, 21, bark, width=2)
    base.line(21, 19, 16, 13, bark, width=2)

    def needles(x, y, nx, ny):
        if ny > 0.65 and rnd.random() < 0.45:  # ragged underside
            return None
        n = ny + rnd.uniform(-0.15, 0.15)
        if n < -0.45:
            return green["hi"]
        if n < 0.15:
            return green["mid"]
        if n < 0.55:
            return green["sh"]
        return green["deep"]

    for cx, cy, rx, ry in ((12, 26, 9, 3.5), (34, 20, 10, 4), (17, 12, 9, 3.5), (27, 7, 6, 3)):
        base.ellipse(cx, cy, rx, ry, needles)

    frames = []
    for i in range(FRAMES):
        p = 2 * math.pi * i / FRAMES
        cv = base.shear_rows(sway(34, 1.2, p))
        cv.outline(rgb(20, 34, 28))
        frames.append(cv)
    return frames


def make_bamboo_frames():
    rnd = random.Random("bamboo")
    stalk = {"hi": rgb(184, 212, 116), "mid": rgb(124, 172, 82),
             "sh": rgb(80, 124, 62), "node": rgb(62, 98, 50)}
    leaf, leaf_hi = rgb(92, 148, 68), rgb(150, 196, 96)
    ground = 46
    stalks = [(7, 42, 0.0), (14, 38, 1.3), (19, 45, 2.2), (25, 34, 0.7)]
    leaves = {}
    for sx, h, _ in stalks:
        top = ground - h
        leaves[sx] = [(y, rnd.choice((-1, 1))) for y in range(top + 3, top + int(h * 0.55), 5)]

    frames = []
    for i in range(FRAMES):
        p = 2 * math.pi * i / FRAMES
        cv = Canvas(32, 48)
        for sx, h, phase in stalks:
            top = ground - h

            def off(y, h=h, phase=phase):
                return round(2.2 * ((ground - y) / h) ** 2 * math.sin(p + phase))

            for y in range(top, ground + 1):
                x = sx + off(y)
                is_node = (ground - y) % 7 == 0 and y != ground
                cv.set(x, y, stalk["node"] if is_node else stalk["mid"])
                cv.set(x + 1, y, stalk["node"] if is_node else stalk["sh"])
                if not is_node and (ground - y) % 7 == 3:
                    cv.set(x, y, stalk["hi"])
            for ly, d in leaves[sx]:
                x0 = sx + off(ly) + (2 if d > 0 else -1)
                for k in range(4):
                    cv.set(x0 + d * k, ly + k // 2, leaf if k < 3 else leaf_hi)
                cv.set(x0 + d, ly - 1, leaf_hi)
        cv.outline(rgb(24, 44, 28))
        frames.append(cv)
    return frames


# ================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets")
    ap.add_argument("--preview", help="write a scaled preview sheet to this path")
    args = ap.parse_args()

    tiles = {}
    for kind in ("grass", "dirt"):
        for mask in range(16):
            for v in range(VARIANTS):
                cv = make_tile(kind, mask, v)
                tiles[(kind, mask, v)] = cv
                cv.save(os.path.join(args.out, "tiles", kind, f"{kind}_{mask:02d}_{v}.png"))
        print(f"{kind}: {16 * VARIANTS} tiles")

    rocks = {"pebbles": make_pebbles(), "boulder": make_boulder(), "cairn": make_cairn()}
    for name, cv in rocks.items():
        cv.save(os.path.join(args.out, "decorations", "rocks", f"{name}.png"))
    print(f"rocks: {', '.join(rocks)}")

    trees = {"sakura": make_sakura_frames(), "pine": make_pine_frames(), "bamboo": make_bamboo_frames()}
    for name, frames in trees.items():
        for i, cv in enumerate(frames):
            cv.save(os.path.join(args.out, "decorations", "trees", name, f"{name}_{i:02d}.png"))
    print(f"trees: {', '.join(trees)} ({FRAMES} frames each)")

    if args.preview:
        rows = [[tiles[("grass", m, 0)] for m in range(16)],
                [tiles[("dirt", m, 0)] for m in range(16)],
                list(rocks.values())]
        rows += [frames for frames in trees.values()]
        preview_sheet(args.preview, rows, scale=5)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
