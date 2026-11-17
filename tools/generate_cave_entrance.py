"""Generate the ancient cave entrance prop (stdlib only): a mossy rock mound
with a dark mouth, framed by two rune stones that glow like the golem's eyes.

Usage (from the repo root):
    python tools/generate_cave_entrance.py
    python tools/generate_cave_entrance.py --preview preview.png

Output:
    assets/decorations/props/cave_entrance.png   64x48 (feet on the bottom row)
"""

import argparse
import os
import random

from pixelart import Canvas, preview_sheet, rgb

W, H = 64, 48
OUT = rgb(22, 18, 26)
ROCK = {"hi": rgb(140, 134, 126), "base": rgb(104, 98, 96), "sh": rgb(72, 68, 74), "dk": rgb(50, 46, 56)}
MOSS = (rgb(64, 104, 56), rgb(102, 146, 70))
DARK = (rgb(8, 6, 12), rgb(18, 14, 22), rgb(30, 26, 36))      # cave interior, deepest first
GLOW = (rgb(76, 170, 210), rgb(140, 236, 255))


def make_cave():
    rnd = random.Random("cave")
    cv = Canvas(W, H)
    cx = W / 2

    # mound: a cluster of boulders, big in the middle, smaller to the sides
    boulders = [(cx, 30, 26, 19), (cx - 18, 36, 12, 12), (cx + 18, 36, 12, 12),
                (cx - 8, 18, 12, 9), (cx + 9, 19, 11, 9), (cx, 13, 9, 7)]
    for i, (bx, by, rx, ry) in enumerate(boulders):
        def color(x, y, nx, ny, i=i):
            v = -nx * 0.45 - ny * 0.85
            if ny < -0.5 and rnd.random() < 0.7:
                return MOSS[1] if v > 0.8 else MOSS[0]
            if nx * nx + ny * ny > 0.8 and v < 0:
                return ROCK["dk"]
            c = ROCK["hi"] if v > 0.5 else ROCK["sh"] if v < -0.3 else ROCK["base"]
            return ROCK["sh"] if rnd.random() < 0.06 else c
        cv.ellipse(bx, by, rx, ry, color)
    for x in range(W):                                   # flat bottom
        for y in range(H - 2, H):
            if cv.get(x, y - 1) is not None:
                cv.set(x, y, ROCK["dk"])
    cv.outline(OUT)

    # the mouth: an arch, darker towards the inside
    mx, mw, top = cx, 10, 22
    for y in range(top, H):
        half = mw if y > top + 8 else mw * (1 - ((top + 8 - y) / 9) ** 2) ** 0.5
        for x in range(int(mx - half), int(mx + half) + 1):
            edge = min(x - (mx - half), (mx + half) - x)
            c = DARK[0] if edge > 4 else DARK[1] if edge > 1.5 else DARK[2]
            cv.set(x, y, c)
    # stalactite teeth hanging into the mouth
    for tx, length in ((mx - 6, 3), (mx - 2, 4), (mx + 3, 2), (mx + 7, 3)):
        for k in range(length):
            cv.set(tx, top + 3 + k, ROCK["sh"])
    # arch stones around the mouth
    for ang_x in range(-11, 12):
        y = top - 1 + round((ang_x / 11) ** 2 * 7)
        cv.set(mx + ang_x, y, ROCK["hi"] if ang_x < 0 else ROCK["base"])

    # rune stones on both sides of the entrance
    for sx in (cx - 17, cx + 17):
        cv.rect(int(sx) - 2, H - 12, int(sx) + 2, H - 1, ROCK["base"])
        cv.rect(int(sx) - 2, H - 12, int(sx) - 2, H - 1, ROCK["hi"])
        for dy in (3, 5, 6, 8):
            cv.set(sx, H - 12 + dy, GLOW[1])
        cv.set(sx - 1, H - 12 + 5, GLOW[0])
        cv.set(sx + 1, H - 12 + 7, GLOW[0])
        for x in range(int(sx) - 3, int(sx) + 4):
            cv.set(x, H - 13, OUT)
        for y in range(H - 12, H):
            cv.set(sx - 3, y, OUT)
            cv.set(sx + 3, y, OUT)
    return cv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "decorations", "props"))
    ap.add_argument("--preview")
    args = ap.parse_args()
    cv = make_cave()
    cv.save(os.path.join(args.out, "cave_entrance.png"))
    print("cave_entrance.png")
    if args.preview:
        preview_sheet(args.preview, [[cv]], scale=5)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
