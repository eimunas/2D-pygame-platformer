"""Generate the skeleton enemy sprites (the ancient caves): a bare-bones warrior
built with the player's body/animation code - skull with an ember glowing in its
eye socket, ribcage, thin limbs - always holding an ancient STONE sword.

Usage (from the repo root):
    python tools/generate_skeleton_sprites.py
    python tools/generate_skeleton_sprites.py --preview preview.png

Output (faces RIGHT, flip in game for left; all 32x24, body bottom-centred
like the other enemies' attack frames):
    assets/enemies/skeleton/idle/idle_00..05.png        sword held low
    assets/enemies/skeleton/walk/walk_00..15.png
    assets/enemies/skeleton/run/run_00..15.png          charging, sword raised
    assets/enemies/skeleton/attack/attack_00..05.png    horizontal cut (hits on 2-3)
    assets/enemies/skeleton/collapse/collapse_00..06.png  falls apart into a bone pile
    assets/enemies/skeleton/rise/rise_00..06.png        the pile pulls itself back together
"""

import argparse
import math
import os
import random

import generate_player_sprites as base
from pixelart import Canvas, preview_sheet, write_png

BONE = (226, 218, 196, 255)
SKELETON_PALETTE = dict(
    base.PALETTE,
    suit=BONE,                      # skull, ribs
    suit_hi=(246, 240, 222, 255),   # front arm, skull highlight
    suit_sh=(164, 154, 136, 255),   # spine, back limbs, jaw
    leg=BONE,
    leg_sh=(164, 154, 136, 255),
    wrap=(196, 188, 168, 255),      # ankles
    red_dk=(196, 188, 168, 255),    # pelvis
    skin=(246, 240, 222, 255),      # hand bones
    eye=(24, 18, 26, 255),          # eye socket / nose hole
    ember=(255, 132, 64, 255),      # the glow in the socket
    outline=(26, 20, 28, 255),
    hilt=(84, 62, 44, 255),         # old leather grip
    guard=(70, 68, 74, 255),        # chunky stone guard
)
STONE = (118, 114, 110, 255)
STONE_HI = (164, 160, 150, 255)
STONE_SH = (78, 74, 76, 255)
SWORD_LEN = 9


def stone_sword(cv, hx, hy, angle_deg, length=SWORD_LEN):
    """Replaces the katana: a thick, blunt slab of carved stone (2 px wide)."""
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx                                   # perpendicular (the blade's thickness)
    t = -2.0
    while t <= length:
        x, y = hx + dx * t, hy + dy * t
        if t < 0:
            cv.set(x, y, SKELETON_PALETTE["hilt"])
        elif t < 1.5:
            cv.set(x, y, SKELETON_PALETTE["guard"])
            cv.set(x + px, y + py, SKELETON_PALETTE["guard"])
            cv.set(x - px, y - py, SKELETON_PALETTE["guard"])
        else:
            tip = t > length - 1.5
            cv.set(x, y, STONE_HI if not tip else STONE)
            if not tip:
                cv.set(x + px, y + py, STONE_SH if int(t * 2) % 5 else STONE)   # notches
        t += 0.5


def held(pose, angle, phase=0.0):
    return base.attack_frame(pose, angle, phase=phase, blade_length=SWORD_LEN)


def idle_frames():
    frames = []
    for i, b in enumerate((0, 0, 0, 1, 1, 1)):
        frames.append(held({"bob": b, "lean": 0, "back_foot": (-1, 0), "front_foot": (1, 0),
                            "back_hand": (0, 2), "front_hand": (2, 1)}, 32 + 3 * (i % 3)))
    return frames


def walk_frames():
    poses = base.gait_poses(16, amp=2, lift=1, bend=1, arm_amp=2, lean=0,
                            tail_len=1, tail_amp=0.0, run=False)
    return [held(dict(p, front_hand=(2, 1)), 28) for p in poses]


def run_frames():
    poses = base.gait_poses(16, amp=3.5, lift=2, bend=2, arm_amp=2, lean=1,
                            tail_len=1, tail_amp=0.0, run=True)
    return [held(dict(p, front_hand=(2, -1), back_hand=(1, 0)), -55) for p in poses]


def attack_frames():
    return base.attack_frames("attack1")               # wide horizontal cut


# ---------------------------------------------------------------- falling apart
def pile_height(x, cx):
    return max(0.0, 3.2 - abs(x - cx) / 2.2)


def collapse_frames(n=7):
    """The standing skeleton falls into a heap: every pixel drops (the top ones
    furthest), spreads sideways a little and settles on a small mound; the sword
    clatters down beside it and the skull ends up on top."""
    standing = idle_frames()[0]
    w, h = standing.w, standing.h
    floor = h - 1
    cx = w / 2
    rnd = random.Random("bones")
    pixels = [(x, y, standing.px[y][x], rnd.uniform(0.7, 1.3), rnd.uniform(-1, 1))
              for y in range(h) for x in range(w)
              if standing.px[y][x] is not None and standing.px[y][x] != SKELETON_PALETTE["outline"]]
    frames = []
    for i in range(n):
        t = (i / (n - 1)) ** 1.4
        cv = Canvas(w, h)
        for x, y, c, speed, spread in pixels:
            tt = min(1.0, t * speed)
            nx = x + (x - cx) * 0.45 * tt + spread * 2 * tt
            target = floor - pile_height(nx, cx)
            ny = y + (max(y, target) - y) * tt
            cv.set(nx, min(ny, floor), c)
        if i >= n - 2:                                   # the skull rolls onto the top
            sx, sy = round(cx + 1), floor - 5
            cv.rect(sx - 1, sy, sx + 2, sy + 2, BONE)
            cv.set(sx, sy, SKELETON_PALETTE["suit_hi"])
            cv.set(sx + 1, sy + 1, SKELETON_PALETTE["eye"])
            cv.set(sx + 2, sy + 1, SKELETON_PALETTE["ember"] if i == n - 1 else SKELETON_PALETTE["eye"])
            for k in range(-6, 3):                       # the stone sword, lying flat
                cv.set(cx + k - 2, floor, STONE if k > -5 else SKELETON_PALETTE["hilt"])
        cv.outline(SKELETON_PALETTE["outline"])
        frames.append(cv)
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "enemies", "skeleton"))
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=6)
    args = ap.parse_args()

    base.STYLE = "skeleton"
    base.PALETTE = SKELETON_PALETTE
    base.draw_katana = stone_sword                     # every held sword is the stone one

    collapse = collapse_frames()
    anims = {
        "idle": idle_frames(),
        "walk": walk_frames(),
        "run": run_frames(),
        "attack": attack_frames(),
        "collapse": collapse,
        "rise": list(reversed(collapse)),
    }
    for name, frames in anims.items():
        for i, cv in enumerate(frames):
            write_png(os.path.join(args.out, name, f"{name}_{i:02d}.png"), cv.rgba_rows(), cv.w, cv.h)
        print(f"{name}: {len(frames)} frames ({frames[0].w}x{frames[0].h})")

    if args.preview:
        preview_sheet(args.preview, list(anims.values()), scale=args.scale)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
