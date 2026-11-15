"""Generate a layered, misty-forest parallax background (stdlib only).

Usage (from the repo root):
    python tools/generate_background.py
    python tools/generate_background.py --preview preview.png

Output (each 480x300, drawn at 2x in game, tiles seamlessly left/right):
    assets/background/sky.png           opaque gradient, pale sun, cloud streaks
    assets/background/mountains.png     two ridges + a pagoda silhouette
    assets/background/forest_far.png    pale pine treeline in mist
    assets/background/forest_mid.png    larger pines
    assets/background/forest_near.png   tall trunks, overhanging canopy, light rays

Palette idea: cool, desaturated blue-grey/teal that gets paler with distance
(atmospheric perspective), so the saturated green grass, brown dirt and the
dark navy ninja always stand out in front of it.
"""

import argparse
import math
import os
import random

from pixelart import Canvas, rgb, write_png

W, H = 480, 300
MIST = (222, 230, 226)
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


# ---------------------------------------------------------------- helpers
def clamp01(t):
    return max(0.0, min(1.0, t))


def lerp(c1, c2, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def ramp(c1, c2, t, x, y, steps=4):
    """Pixel-art gradient: `steps` flat colour bands, ordered dither between them."""
    v = clamp01(t) * steps
    lo = math.floor(v)
    if (v - lo) * 16 > BAYER[y % 4][x % 4] + 0.5:
        lo += 1
    return rgb(*lerp(c1, c2, min(lo, steps) / steps))


def periodic(x, terms):
    """Sum of sines that repeats every W pixels -> seamless horizontal tiling."""
    return sum(a * math.sin(2 * math.pi * k * x / W + ph) for a, k, ph in terms)


def wrap_dx(x, cx):
    return (x - cx + W / 2) % W - W / 2


def fogged(color, fog_start, fog_len, fog_max):
    """Colour function that fades `color` into mist towards the bottom."""
    def fn(x, y):
        return ramp(color, MIST, (y - fog_start) / fog_len * fog_max, x, y, steps=5)
    return fn


# ---------------------------------------------------------------- layers
def make_sky():
    cv = Canvas(W, H)
    top, horizon = (166, 190, 204), (232, 234, 224)
    for y in range(H):
        for x in range(W):
            cv.set(x, y, ramp(top, horizon, y / 215, x, y, steps=6))

    # pale sun with a dithered glow
    sx, sy, r = 300, 96, 22
    for y in range(sy - 50, sy + 51):
        for x in range(sx - 50, sx + 51):
            d = math.hypot(x - sx, y - sy)
            if d <= r:
                cv.set(x, y, rgb(250, 246, 228))
            elif d <= r + 26:
                base = cv.get(x % W, y)
                if base:
                    t = 1 - (d - r) / 26
                    cv.set(x, y, ramp(base[:3], (244, 240, 222), t * 0.8, x, y, steps=3))

    # long horizontal cloud streaks
    rnd = random.Random("clouds")
    for _ in range(7):
        cx, cy = rnd.randrange(W), rnd.randrange(30, 170)
        length, thick = rnd.randrange(40, 110), rnd.uniform(2, 4.5)
        for x in range(W):
            dx = wrap_dx(x, cx) / length
            if abs(dx) >= 1:
                continue
            half = thick * (1 - dx * dx)
            for y in range(int(cy - half), int(cy + half) + 1):
                if BAYER[y % 4][x % 4] < 13 or abs(y - cy) < half - 1:
                    cv.set(x, y, rgb(240, 242, 236))
    return cv


def make_mountains():
    cv = Canvas(W, H)
    ranges = [
        # base y, sine terms, colour, fog
        (150, [(30, 1, 0.3), (14, 3, 1.1), (6, 7, 2.0)], (178, 196, 204)),
        (178, [(22, 2, 2.2), (10, 5, 0.4), (5, 11, 1.3)], (160, 180, 190)),
    ]
    for base, terms, color in ranges:
        for x in range(W):
            top = round(base + periodic(x, terms))
            for y in range(top, H):
                cv.set(x, y, ramp(color, MIST, (y - top) / 90 * 0.75, x, y, steps=4))

    # pagoda on the near ridge
    px = 110
    base_y = round(178 + periodic(px, ranges[1][1])) + 3
    col = rgb(142, 162, 174)
    y = base_y
    for body_w, roof_w in ((12, 24), (10, 20), (8, 16)):
        cv.rect(px - body_w // 2, y - 6, px + body_w // 2, y, col)      # walls
        y -= 7
        cv.rect(px - roof_w // 2, y, px + roof_w // 2, y, col)          # roof
        cv.rect(px - roof_w // 2 + 2, y - 1, px + roof_w // 2 - 2, y - 1, col)
        cv.set(px - roof_w // 2 - 1, y - 1, col)                        # upturned eaves
        cv.set(px + roof_w // 2 + 1, y - 1, col)
        y -= 1
    cv.rect(px, y - 7, px, y, col)                                      # spire
    return cv


def pine(cv, cx, base, h, color_fn, rnd):
    """Tiered conifer silhouette, wrapped horizontally."""
    tiers = max(3, h // 14)
    top = base - h
    for y in range(top, base + 1):
        rel = (y - top) / h
        tier_pos = (rel * tiers) % 1.0
        half = (1.5 + rel * h * 0.3) * (0.6 + 0.4 * tier_pos) + rnd.uniform(-0.6, 0.6)
        for x in range(int(cx - half), int(cx + half) + 1):
            cv.set(x % W, y, color_fn(x % W, y))
    cv.set(int(cx) % W, top - 1, color_fn(int(cx) % W, top - 1))    # pointed tip


def make_forest(seed, n, h_range, base_line, color, fog_start, fog_len, fog_max):
    rnd = random.Random(seed)
    cv = Canvas(W, H)
    color_fn = fogged(color, fog_start, fog_len, fog_max)
    for i in range(n):
        cx = (i + rnd.uniform(-0.35, 0.35)) * W / n
        pine(cv, cx, base_line + rnd.randrange(-4, 5), rnd.randrange(*h_range), color_fn, rnd)
    # undergrowth mass joining the bases
    for x in range(W):
        top = base_line - 6 + round(periodic(x, [(2, 9, 0.5), (1.5, 23, 1.7)]))
        for y in range(top, H):
            cv.set(x, y, color_fn(x, y))
    return cv


def make_near():
    rnd = random.Random("near")
    cv = Canvas(W, H)
    trunk, trunk_hi = (96, 122, 134), (110, 136, 148)
    canopy = (90, 116, 128)
    trunk_fn = fogged(trunk, 190, 110, 0.8)

    # tall straight cedar trunks, full height
    for i in range(4):
        cx = (i + rnd.uniform(-0.25, 0.25)) * W / 4 + 40
        w = rnd.randrange(10, 16)
        for y in range(H):
            for dx in range(w):
                x = int(cx + dx) % W
                c = trunk_fn(x, y)
                if dx == 1 or (dx == 2 and y % 9 < 5):          # lit edge + bark marks
                    c = ramp(trunk_hi, MIST, (y - 190) / 110 * 0.8, x, y, steps=5)
                cv.set(x, y, c)
        # a couple of short branch stubs
        for by in (rnd.randrange(40, 70), rnd.randrange(80, 120)):
            d = rnd.choice((-1, 1))
            for k in range(rnd.randrange(8, 16)):
                x = int(cx + (w if d > 0 else 0) + d * k) % W
                cv.set(x, by - k // 4, rgb(*trunk))
                cv.set(x, by - k // 4 + 1, rgb(*trunk))

    # overhanging canopy along the top edge
    for x in range(W):
        depth = 16 + periodic(x, [(7, 3, 0.2), (4, 8, 1.4), (2, 19, 2.6)]) + rnd.uniform(-1.5, 1.5)
        for y in range(int(depth)):
            cv.set(x, y, rgb(*canopy))
        # hanging needle tufts
        if x % 6 in (0, 1) and rnd.random() < 0.6:
            for y in range(int(depth), int(depth) + rnd.randrange(2, 6)):
                cv.set(x, y, rgb(*canopy))

    # soft diagonal light rays (semi-transparent, only over empty pixels)
    for y in range(H):
        for x in range(W):
            if cv.get(x, y) is None and (x + y * 0.6) % 160 < 16 and y > 10:
                alpha = round(42 * (1 - y / H))
                if alpha > 4 and BAYER[y % 4][x % 4] < 12:
                    cv.set(x, y, rgb(250, 246, 222, alpha))
    return cv


# ---------------------------------------------------------------- main
def composite(layers, offsets):
    """Flatten layers (alpha-blended) into one canvas for the preview."""
    out = Canvas(W, H)
    for cv, ox in zip(layers, offsets):
        for y in range(H):
            for x in range(W):
                c = cv.get((x + ox) % W, y)
                if c is None:
                    continue
                under = out.get(x, y)
                if c[3] == 255 or under is None:
                    out.set(x, y, c)
                else:
                    a = c[3] / 255
                    out.set(x, y, rgb(*lerp(under[:3], c[:3], a)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "background"))
    ap.add_argument("--preview", help="write a 2x composited preview to this path")
    args = ap.parse_args()

    layers = {
        "sky": make_sky(),
        "mountains": make_mountains(),
        "forest_far": make_forest("far", 22, (40, 76), 228, (140, 166, 176), 185, 70, 0.8),
        "forest_mid": make_forest("mid", 9, (80, 132), 238, (116, 144, 156), 200, 80, 0.75),
        "forest_near": make_near(),
    }
    for name, cv in layers.items():
        cv.save(os.path.join(args.out, f"{name}.png"))
        print(f"{name}.png")

    if args.preview:
        flat = composite(list(layers.values()), [0, 0, 0, 0, 0])
        write_png(args.preview, flat.rgba_rows(2), W * 2, H * 2)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
