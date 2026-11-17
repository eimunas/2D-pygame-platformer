"""Generate the stone golem mini-boss sprites (stdlib only).

A giant of mossy boulders with glowing cyan rune eyes and huge fists.
Every frame is the same 64x56 canvas with the body centred and the feet on the
bottom row, so frames line up without offsets (faces RIGHT; flip for left).

Usage (from the repo root):
    python tools/generate_golem_sprites.py
    python tools/generate_golem_sprites.py --preview preview.png

Output: assets/enemies/golem/<anim>/<anim>_NN.png
    idle   6 frames   slow breathing, runes pulse
    walk   8 frames   heavy steps (feet plant on frames 0 and 4)
    attack 8 frames   both fists raised overhead (0-2) -> slam in front (3-5) -> recover
    crouch 2 frames   gathering for the big jump
    air    2 frames   in the air, fists raised
    land   3 frames   fists pounding the ground on landing
"""

import argparse
import math
import os
import random

from pixelart import Canvas, preview_sheet, rgb, write_png

W, H = 64, 56
CX = 32                      # body centre
OUT = rgb(22, 18, 26)

FRONT = {"hi": rgb(156, 150, 138), "base": rgb(116, 110, 106), "sh": rgb(80, 76, 80), "dk": rgb(56, 52, 60)}
BACK = {"hi": rgb(116, 110, 106), "base": rgb(86, 82, 86), "sh": rgb(62, 58, 66), "dk": rgb(44, 40, 50)}
MOSS = (rgb(70, 112, 58), rgb(110, 152, 72))
GLOW = (rgb(76, 170, 210), rgb(140, 236, 255), rgb(236, 255, 255))   # dim, glow, core


# ---------------------------------------------------------------- drawing helpers
def stone(cv, cx, cy, rx, ry, pal, seed, moss=False):
    """Shaded boulder (light from the upper left) with speckles and optional moss on top."""
    rnd = random.Random(seed)

    def color(x, y, nx, ny):
        v = -nx * 0.45 - ny * 0.85
        if moss and ny < -0.55 and rnd.random() < 0.75:
            return MOSS[1] if v > 0.75 else MOSS[0]
        if nx * nx + ny * ny > 0.78 and v < -0.1:
            return pal["dk"]
        c = pal["hi"] if v > 0.5 else pal["sh"] if v < -0.3 else pal["base"]
        if rnd.random() < 0.07:
            c = pal["sh"] if c != pal["sh"] else pal["dk"]
        return c
    cv.ellipse(cx, cy, rx, ry, color)


def paste(dst, src):
    for y in range(src.h):
        for x in range(src.w):
            c = src.px[y][x]
            if c is not None:
                dst.px[y][x] = c


def part(draw):
    """Draw one body part on its own canvas and outline it, so overlapping
    parts stay readable."""
    cv = Canvas(W, H)
    draw(cv)
    cv.outline(OUT)
    return cv


def arm(cv, shoulder, fist, pal, seed):
    sx, sy = shoulder
    fx, fy = fist
    for i, t in enumerate((0.2, 0.45, 0.7)):          # chunky rock segments along the arm
        stone(cv, sx + (fx - sx) * t, sy + (fy - sy) * t, 3.2, 3.2, pal, f"{seed}-{i}")
    stone(cv, fx, fy, 5.2, 4.8, pal, f"{seed}-fist")    # the fist
    # knuckle line
    for dx in (-2, 0, 2):
        cv.set(fx + dx, fy - 1, pal["sh"])


def leg(cv, x, lift, crouch, pal, seed):
    ry = 7 - crouch * 0.4
    stone(cv, x, 55 - 3 - ry - lift, 5, ry, pal, f"{seed}-leg")
    stone(cv, x + 1, 53.5 - lift, 6, 2.5, pal, f"{seed}-foot")


# ---------------------------------------------------------------- the golem
def golem(pose):
    """pose: bob, crouch, legs ((dx, lift) back, front), fists (back, front), glow 0..1"""
    bob = pose.get("bob", 0)
    crouch = pose.get("crouch", 0)
    (bdx, blift), (fdx, flift) = pose.get("legs", ((0, 0), (0, 0)))
    back_fist, front_fist = pose["fists"]
    glow = pose.get("glow", 0.5)
    lean = pose.get("lean", 0)                      # + = torso pushed forward
    y0 = bob + crouch

    torso_c = (CX + lean, 33 + y0)
    back_sh = (CX - 11 + lean, 25 + y0)
    front_sh = (CX + 10 + lean, 25 + y0)
    head_c = (CX + 4 + lean * 1.3, 17 + y0)

    layers = [
        part(lambda cv: arm(cv, back_sh, back_fist, BACK, "barm")),
        part(lambda cv: leg(cv, CX - 7 + bdx, blift, crouch, BACK, "bleg")),
        part(lambda cv: stone(cv, *back_sh, 6, 5, BACK, "bsh", moss=True)),
        part(lambda cv: stone(cv, *torso_c, 15, 13, FRONT, "torso", moss=True)),
        part(lambda cv: leg(cv, CX + 6 + fdx, flift, crouch, FRONT, "fleg")),
        part(lambda cv: stone(cv, *head_c, 7, 6, FRONT, "head", moss=True)),
        part(lambda cv: stone(cv, *front_sh, 6.5, 5.5, FRONT, "fsh", moss=True)),
        part(lambda cv: arm(cv, front_sh, front_fist, FRONT, "farm")),
    ]
    cv = Canvas(W, H)
    for i, layer in enumerate(layers):
        paste(cv, layer)
        if i == 3:
            runes(cv, torso_c, glow)
        if i == 5:
            face(cv, head_c, glow)
    return cv


def runes(cv, c, glow):
    """Glowing cracks across the chest."""
    x, y = round(c[0]) + 2, round(c[1]) - 3
    col = GLOW[2] if glow > 0.8 else GLOW[1] if glow > 0.4 else GLOW[0]
    for dx, dy in ((0, 0), (1, 1), (2, 1), (3, 2), (1, -1), (0, 2), (-1, 3), (4, 3), (2, 4), (3, 5)):
        cv.set(x + dx, y + dy, col)
    if glow > 0.6:                                   # faint halo
        for dx, dy in ((-1, 0), (4, 2), (1, 5), (-2, 4)):
            cv.set(x + dx, y + dy, GLOW[0])


def face(cv, c, glow):
    x, y = round(c[0]), round(c[1])
    for dx in range(-1, 6):                          # heavy brow
        cv.set(x + dx, y - 2, FRONT["dk"])
    core = GLOW[2] if glow > 0.5 else GLOW[1]
    cv.set(x + 3, y - 1, core)
    cv.set(x + 4, y - 1, core)
    cv.set(x + 2, y - 1, GLOW[0])
    cv.set(x + 5, y - 1, GLOW[1] if glow > 0.7 else GLOW[0])
    for dx in range(0, 5):                           # jaw line
        cv.set(x + dx, y + 3, FRONT["dk"])


# ---------------------------------------------------------------- animations
IDLE_FISTS = ((CX - 15, 41), (CX + 15, 41))


def fists(back, front, dy=0):
    return ((back[0], back[1] + dy), (front[0], front[1] + dy))


def idle_frames():
    frames = []
    for i, b in enumerate((0, 0, 1, 1, 1, 0)):
        glow = 0.4 + 0.4 * math.sin(i / 6 * 2 * math.pi) ** 2
        frames.append(golem({"bob": b, "fists": fists(*IDLE_FISTS, b), "glow": glow,
                             "legs": ((0, 0), (0, 0))}))
    return frames


def walk_frames(n=8):
    frames = []
    for i in range(n):
        p = i / n * 2 * math.pi
        s = math.sin(p)
        front_lift = round(max(0.0, 3 * s))           # front foot up on frames 1-3, plants on 4
        back_lift = round(max(0.0, -3 * s))           # back foot up on 5-7, plants on 0
        bob = 1 if i in (0, 4) else 0                 # weight drops as a foot lands
        swing = round(3 * s)
        frames.append(golem({
            "bob": bob,
            "legs": ((-round(2 * s), back_lift), (round(2 * s), front_lift)),
            "fists": ((CX - 15 + swing, 41 + bob), (CX + 15 - swing, 41 + bob)),
            "glow": 0.5,
        }))
    return frames


def attack_frames():
    poses = [
        {"fists": ((CX - 8, 30), (CX + 12, 30)), "glow": 0.6},
        {"bob": -1, "fists": ((CX - 4, 8), (CX + 6, 7)), "glow": 0.8, "lean": -1},
        {"bob": -2, "fists": ((CX - 5, 6), (CX + 5, 5)), "glow": 1.0, "lean": -2},
        {"crouch": 3, "fists": ((CX + 18, 47), (CX + 24, 47)), "glow": 1.0, "lean": 3},
        {"crouch": 4, "fists": ((CX + 18, 49), (CX + 24, 49)), "glow": 1.0, "lean": 3},
        {"crouch": 4, "fists": ((CX + 18, 49), (CX + 24, 49)), "glow": 0.8, "lean": 3},
        {"crouch": 2, "fists": ((CX + 6, 44), (CX + 18, 44)), "glow": 0.6, "lean": 1},
        {"crouch": 1, "fists": ((CX - 12, 42), (CX + 16, 42)), "glow": 0.5},
    ]
    return [golem(p) for p in poses]


def crouch_frames():
    return [golem({"crouch": c, "fists": ((CX - 16, 45 + c // 2), (CX + 16, 45 + c // 2)), "glow": g})
            for c, g in ((3, 0.7), (5, 1.0))]


def air_frames():
    return [golem({"bob": -3, "legs": ((-1, 4), (1, 5)), "glow": 1.0,
                   "fists": ((CX - 13, 10 + d), (CX + 13, 9 + d))})
            for d in (0, 1)]


def land_frames():
    return [golem({"crouch": c, "fists": ((CX - 19, 50), (CX + 19, 50)), "glow": g})
            for c, g in ((6, 1.0), (4, 0.8), (2, 0.6))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "enemies", "golem"))
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=4)
    args = ap.parse_args()

    anims = {
        "idle": idle_frames(),
        "walk": walk_frames(),
        "attack": attack_frames(),
        "crouch": crouch_frames(),
        "air": air_frames(),
        "land": land_frames(),
    }
    for name, frames in anims.items():
        for i, cv in enumerate(frames):
            write_png(os.path.join(args.out, name, f"{name}_{i:02d}.png"), cv.rgba_rows(), cv.w, cv.h)
        print(f"{name}: {len(frames)} frames ({W}x{H})")
    if args.preview:
        preview_sheet(args.preview, list(anims.values()), scale=args.scale)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
