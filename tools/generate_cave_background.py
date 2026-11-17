"""Generate a layered cave parallax background (stdlib only).

Usage (from the repo root):
    python tools/generate_cave_background.py
    python tools/generate_cave_background.py --preview preview.png

Output (each 480x300, drawn at 2x in game, tiles seamlessly left/right):
    assets/background/cave/back.png   opaque: deep cavern wall, a teal glow far away, glints
    assets/background/cave/far.png    distant stalactites + stalagmites in the haze
    assets/background/cave/mid.png    bigger formations with glowing crystal clusters
    assets/background/cave/near.png   dark rock columns and a jagged ceiling fringe

Palette idea: cold violet-grey rock that fades into a teal haze with distance,
so the rock_top floor tiles and bone-white skeletons stand out in front of it.
"""

import argparse
import math
import os
import random

from generate_background import BAYER, composite, lerp, periodic, ramp, wrap_dx
from pixelart import Canvas, rgb, write_png

W, H = 480, 300
HAZE = (54, 92, 104)                # glowing teal fog deep in the cave
CRYSTAL = ((150, 236, 246), (84, 170, 196), (176, 140, 236))


def hazed(color, t, x, y):
    return ramp(color, HAZE, t, x, y, steps=4)


# ---------------------------------------------------------------- layers
def make_back():
    cv = Canvas(W, H)
    rnd = random.Random("back")
    top, mid, bottom = (10, 9, 18), (30, 30, 46), (14, 12, 22)
    gx, gy = 250, 170                                   # far glow
    for y in range(H):
        for x in range(W):
            t = y / H
            c = ramp(top, mid, t * 2, x, y, 4) if t < 0.5 else ramp(mid, bottom, t * 2 - 1, x, y, 4)
            d = math.hypot(wrap_dx(x, gx) / 1.6, y - gy)
            glow = max(0.0, 1 - d / 150)
            if glow > 0:
                c = ramp(c[:3], HAZE, glow * 0.75, x, y, 5)
            cv.set(x, y, c)
    # rock texture: faint blotches on the wall
    for _ in range(140):
        cx, cy, r = rnd.randrange(W), rnd.randrange(H), rnd.randrange(3, 9)
        for y in range(cy - r, cy + r):
            for x in range(cx - r, cx + r):
                if (x - cx) ** 2 + (y - cy) ** 2 < r * r and BAYER[y % 4][x % 4] < 2:
                    base = cv.get(x % W, y)
                    if base:
                        cv.set(x % W, y, rgb(*lerp(base[:3], (0, 0, 0), 0.25)))
    # tiny glints of crystal in the far wall
    for _ in range(60):
        x, y = rnd.randrange(W), rnd.randrange(20, H - 40)
        cv.set(x, y, rgb(*lerp(CRYSTAL[1], HAZE, rnd.uniform(0.2, 0.6))))
    return cv


def spike(cv, cx, base_y, width, length, down, color_fn, rnd):
    """A stalactite (down=True, hanging from base_y) or stalagmite (growing up)."""
    for dx in range(-width, width + 1):
        k = 1 - abs(dx) / (width + 0.5)
        L = length * k ** 1.5 + rnd.uniform(-1.5, 1.5)
        for i in range(int(L) + 1):
            y = base_y + i if down else base_y - i
            x = int(cx + dx) % W
            if 0 <= y < H:
                cv.set(x, y, color_fn(x, y))


def formations(seed, n_top, n_bottom, top_band, bottom_line, size, color, haze_amt):
    rnd = random.Random(seed)
    cv = Canvas(W, H)

    def color_fn(x, y):
        return hazed(color, haze_amt * (1 - abs(y - H * 0.55) / (H * 0.55)), x, y)
    # ceiling mass with hanging stalactites
    for x in range(W):
        depth = top_band + periodic(x, [(6, 3, 0.4), (3, 7, 1.9)])
        for y in range(int(depth)):
            cv.set(x, y, color_fn(x, y))
    for i in range(n_top):
        cx = (i + rnd.uniform(-0.3, 0.3)) * W / n_top
        spike(cv, cx, int(top_band) - 2, rnd.randrange(*size[0]), rnd.randrange(*size[1]), True, color_fn, rnd)
    # floor with stalagmites
    for x in range(W):
        top = bottom_line + periodic(x, [(4, 2, 1.1), (2, 9, 0.3)])
        for y in range(int(top), H):
            cv.set(x, y, color_fn(x, y))
    for i in range(n_bottom):
        cx = (i + 0.5 + rnd.uniform(-0.3, 0.3)) * W / n_bottom
        spike(cv, cx, int(bottom_line) + 2, rnd.randrange(*size[0]), rnd.randrange(*size[1]), False, color_fn, rnd)
    return cv, rnd


def crystals(cv, rnd, n, y_range, scale=1):
    """Small glowing crystal clusters stuck on the formations."""
    placed = tries = 0
    while placed < n and tries < n * 200:
        tries += 1
        x0, y0 = rnd.randrange(W), rnd.randrange(*y_range)
        if cv.get(x0, y0) is None or cv.get(x0, y0 - 6) is not None:
            continue                                   # only on an upward-facing rock edge
        placed += 1
        hue = rnd.choice((0, 0, 2))
        for k in range(rnd.randrange(2, 4)):
            h = rnd.randrange(3, 7) * scale
            lean = rnd.choice((-1, 0, 1))
            for i in range(h):
                x = (x0 + k * 2 * scale + lean * i // 3) % W
                cv.set(x, y0 - i, rgb(*CRYSTAL[hue]))
                cv.set((x + 1) % W, y0 - i, rgb(*lerp(CRYSTAL[hue], (40, 40, 60), 0.45)))
        for dx in range(-3, 6):                        # soft glow around it
            for dy in range(-6, 2):
                x, y = (x0 + dx) % W, y0 + dy
                if cv.get(x, y) is None and BAYER[y % 4][x % 4] < 4:
                    cv.set(x, y, rgb(*CRYSTAL[hue], 60))


def make_far():
    cv, rnd = formations("far", 14, 11, 34, 236, ((6, 12), (30, 70)), (44, 46, 66), 0.8)
    return cv


def make_mid():
    cv, rnd = formations("mid", 7, 6, 22, 248, ((10, 18), (50, 110)), (24, 22, 36), 0.25)
    crystals(cv, rnd, 14, (60, 290))
    return cv


def make_near():
    rnd = random.Random("near")
    cv = Canvas(W, H)
    col = (16, 14, 24)
    edge = (34, 32, 48)
    # jagged ceiling fringe along the top
    for x in range(W):
        depth = 14 + periodic(x, [(6, 4, 0.7), (3, 11, 2.2)]) + rnd.uniform(-1, 1)
        for y in range(int(depth)):
            cv.set(x, y, rgb(*col))
        if rnd.random() < 0.18:                         # drips
            for y in range(int(depth), int(depth) + rnd.randrange(3, 10)):
                cv.set(x, y, rgb(*col))
    # three massive columns (stalactite + stalagmite fused), full height
    for i in range(3):
        cx = (i + rnd.uniform(-0.2, 0.2)) * W / 3 + 60
        for y in range(H):
            pinch = 1 - 0.55 * math.exp(-((y - H * 0.55) / 60) ** 2)   # waisted in the middle
            half = (14 + 4 * math.sin(y / 23 + i)) * pinch
            for dx in range(-int(half), int(half) + 1):
                x = int(cx + dx) % W
                c = edge if dx == -int(half) or (dx == -int(half) + 1 and y % 7 < 3) else col
                cv.set(x, y, rgb(*c))
    crystals(cv, rnd, 5, (60, 296), scale=2)
    return cv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "background", "cave"))
    ap.add_argument("--preview")
    args = ap.parse_args()
    layers = {"back": make_back(), "far": make_far(), "mid": make_mid(), "near": make_near()}
    for name, cv in layers.items():
        cv.save(os.path.join(args.out, f"{name}.png"))
        print(f"{name}.png")
    if args.preview:
        flat = composite(list(layers.values()), [0, 0, 0, 0])
        write_png(args.preview, flat.rgba_rows(2), W * 2, H * 2)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
