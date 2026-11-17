"""Generate the ancient-caves tileset and props (stdlib only).

Usage (from the repo root):
    python tools/generate_cave_assets.py
    python tools/generate_cave_assets.py --preview preview.png

Output:
    assets/tiles/rock_top/rock_top_MM_V.png   16 autotile masks x 3 variants - the floor
                                              surface (rubble + pale lichen on top)
    assets/tiles/rock/rock_MM_V.png           16 x 3 - solid rock (fill, walls, ceiling;
                                              exposed undersides drip little stalactites)
    assets/decorations/props/barrel.png             12x16  old wooden barrel
    assets/decorations/props/bones.png              16x8   a scattered pile of bones
    assets/decorations/props/samurai_remains.png    24x12  a fallen samurai: skull in a
                                                    rusted kabuto, ribs, armour plates, katana

Autotile mask (same as tools/generate_tiles.py): a bit is SET when that side is
exposed:  N = 1, E = 2, S = 4, W = 8.
"""

import argparse
import os
import random

from pixelart import Canvas, preview_sheet, rgb

N, E, S, W = 1, 2, 4, 8
VARIANTS = 3
OUT = rgb(18, 14, 22)

ROCK = {
    "base": rgb(74, 70, 84), "dark": rgb(52, 48, 62), "deep": rgb(38, 34, 46),
    "light": rgb(98, 94, 108), "rim": rgb(128, 122, 132),
    "crystal": rgb(120, 220, 236), "crystal_dk": rgb(60, 140, 170),
}
LICHEN = (rgb(96, 128, 112), rgb(136, 168, 140))


# ================================================================== tiles
def rock_fill(cv, rnd, variant):
    """Irregular stone blocks: a base colour with darker seams and lighter specks."""
    for y in range(16):
        for x in range(16):
            r = rnd.random()
            cv.set(x, y, ROCK["dark"] if r < 0.1 else ROCK["light"] if r < 0.15 else ROCK["base"])
    # a couple of cracks / seams between blocks
    for _ in range(2):
        x, y = rnd.randrange(1, 14), rnd.randrange(2, 13)
        for k in range(rnd.randrange(3, 6)):
            cv.set(x + k, y + (k // 2 if rnd.random() < 0.5 else 0), ROCK["deep"])
    if variant == 2 and rnd.random() < 0.6:          # a tiny crystal glint in the rock
        x, y = rnd.randrange(3, 12), rnd.randrange(4, 12)
        cv.set(x, y, ROCK["crystal"])
        cv.set(x + 1, y + 1, ROCK["crystal_dk"])


def make_tile(kind, mask, variant):
    rnd = random.Random(f"cave-{kind}-{mask}-{variant}")
    cv = Canvas(16, 16)
    rock_fill(cv, rnd, variant)
    top = 0

    if mask & N:
        if kind == "rock_top":                       # walkable floor: rubble + lichen
            for x in range(16):
                bump = 1 if rnd.random() < 0.35 else 0
                for y in range(0, bump):
                    cv.set(x, y, None)
                cv.set(x, bump, OUT)
                cv.set(x, bump + 1, LICHEN[1] if rnd.random() < 0.5 else ROCK["rim"])
                cv.set(x, bump + 2, LICHEN[0] if rnd.random() < 0.6 else ROCK["light"])
                if rnd.random() < 0.3:
                    cv.set(x, bump + 3, LICHEN[0])
            if variant == 1:                         # a loose pebble on top
                px = rnd.randrange(3, 12)
                cv.set(px, 2, ROCK["rim"])
                cv.set(px + 1, 2, ROCK["light"])
            top = 1
        else:
            cv.rect(0, 0, 15, 0, OUT)
            cv.rect(0, 1, 15, 1, ROCK["light"])
    if mask & E:
        cv.rect(14, top, 14, 15, ROCK["deep"])
    if mask & W:
        cv.rect(1, top, 1, 15, ROCK["light"])
    if mask & S:                                     # underside (cave ceiling): dark + drips
        cv.rect(0, 13, 15, 14, ROCK["deep"])
        for x in range(16):
            if rnd.random() < 0.25:
                cv.set(x, 12, ROCK["deep"])

    if mask & E:
        cv.rect(15, top, 15, 15, OUT)
    if mask & W:
        cv.rect(0, top, 0, 15, OUT)
    if mask & S:
        cv.rect(0, 15, 15, 15, OUT)
        # small stalactite points poking down out of the bottom edge
        for x in (rnd.randrange(2, 6), rnd.randrange(9, 14)):
            cv.set(x, 14, ROCK["dark"])
            cv.set(x, 15, OUT)

    for bits, corner, inner in (
        (N | E, (15, 0), (14, 1)), (N | W, (0, 0), (1, 1)),
        (S | E, (15, 15), (14, 14)), (S | W, (0, 15), (1, 14)),
    ):
        if mask & bits == bits:
            cv.set(*corner, None)
            cv.set(*inner, OUT)
    return cv


# ================================================================== props
WOOD = {"hi": rgb(150, 104, 62), "base": rgb(116, 78, 48), "sh": rgb(80, 52, 34)}
IRON = (rgb(78, 76, 84), rgb(112, 108, 112))
BONE = (rgb(226, 218, 196), rgb(176, 166, 146))
RUST = (rgb(132, 48, 40), rgb(96, 36, 34), rgb(150, 92, 52))


def make_barrel():
    cv = Canvas(12, 16)
    for y in range(1, 16):
        bulge = 1 if 4 <= y <= 11 else 0             # wider in the middle
        for x in range(1 - bulge, 11 + bulge):
            rel = (x + bulge) / (11 + 2 * bulge)
            c = WOOD["hi"] if rel < 0.3 else WOOD["sh"] if rel > 0.75 else WOOD["base"]
            if x in (3, 7):                          # gaps between staves
                c = WOOD["sh"]
            cv.set(x, y, c)
    for y in (3, 12):                                # iron hoops
        for x in range(0, 12):
            if cv.get(x, y):
                cv.set(x, y, IRON[1] if x < 5 else IRON[0])
    for x in range(1, 11):                           # lid
        cv.set(x, 1, WOOD["hi"] if x < 6 else WOOD["base"])
    cv.outline(OUT)
    return cv


def bone(cv, x0, y0, x1, y1, color=BONE[0]):
    cv.line(x0, y0, x1, y1, color)
    for x, y in ((x0, y0), (x1, y1)):                # knobbly ends
        cv.set(x, y - 1, color)
        cv.set(x, y + 1, color)


def skull(cv, x, y, eye=rgb(24, 18, 26)):
    cv.rect(x, y, x + 3, y + 2, BONE[0])
    cv.set(x, y + 2, BONE[1])
    cv.set(x + 2, y + 1, eye)
    cv.set(x + 3, y + 1, eye)
    cv.rect(x + 1, y + 3, x + 3, y + 3, BONE[1])     # jaw


def make_bones():
    cv = Canvas(16, 8)
    bone(cv, 2, 6, 9, 5, BONE[1])
    bone(cv, 6, 6, 13, 7)
    bone(cv, 4, 7, 7, 4)
    skull(cv, 9, 2)
    cv.outline(OUT)
    return cv


def make_samurai_remains():
    """A samurai who never left the caves: slumped skeleton in rusted armour."""
    cv = Canvas(24, 12)
    # katana lying in front, rusty
    for x in range(1, 13):
        cv.set(x, 11, RUST[2] if x > 3 else rgb(64, 44, 34))
    cv.set(4, 10, rgb(196, 152, 68))                 # tsuba
    # legs (bones) stretched out
    bone(cv, 12, 10, 18, 10)
    bone(cv, 13, 11, 20, 11, BONE[1])
    # ribcage leaning against nothing, armour plates over it
    for y, (x0, x1) in zip(range(5, 10), ((7, 10), (6, 11), (6, 11), (7, 11), (8, 11))):
        for x in range(x0, x1 + 1):
            cv.set(x, y, BONE[0] if (y % 2) else rgb(40, 32, 40))
    cv.rect(6, 7, 7, 9, RUST[0])                     # faded red lacquer plates
    cv.rect(10, 6, 11, 8, RUST[1])
    # skull in a rusted kabuto, tilted
    skull(cv, 6, 2)
    cv.rect(5, 1, 9, 1, RUST[1])
    cv.rect(6, 0, 8, 0, RUST[0])
    cv.set(4, 2, RUST[1])                            # neck guard
    cv.set(4, 3, RUST[1])
    cv.set(7, -1, rgb(196, 152, 68))
    # an arm bone draped over the knees
    bone(cv, 11, 7, 15, 9, BONE[1])
    cv.outline(OUT)
    return cv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="assets")
    ap.add_argument("--preview")
    args = ap.parse_args()

    rows = []
    for kind in ("rock_top", "rock"):
        row = []
        for mask in range(16):
            for v in range(VARIANTS):
                cv = make_tile(kind, mask, v)
                cv.save(os.path.join(args.out, "tiles", kind, f"{kind}_{mask:02d}_{v}.png"))
                if v == 0:
                    row.append(cv)
        rows.append(row)
        print(f"{kind}: {16 * VARIANTS} tiles")
    props = {"barrel": make_barrel(), "bones": make_bones(), "samurai_remains": make_samurai_remains()}
    for name, cv in props.items():
        cv.save(os.path.join(args.out, "decorations", "props", f"{name}.png"))
        print(f"{name}.png")
    if args.preview:
        preview_sheet(args.preview, rows + [list(props.values())], scale=5)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
