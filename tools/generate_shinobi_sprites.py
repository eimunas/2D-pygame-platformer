"""Generate the shinobi enemy sprites: an enemy ninja built with the player's
body/animation code - black garb, purple headband and sash, red eyes, and a
tanto (dagger) instead of a katana.

Usage (from the repo root):
    python tools/generate_shinobi_sprites.py
    python tools/generate_shinobi_sprites.py --preview preview.png

Output (faces RIGHT, flip in game for left):
    assets/enemies/shinobi/idle/idle_00..05.png      16x16, dagger tucked in the sash
    assets/enemies/shinobi/walk/walk_00..15.png      16x16
    assets/enemies/shinobi/run/run_00..15.png        32x24, sprinting low, dagger forward
    assets/enemies/shinobi/attack/attack_00..04.png  32x24, quick stab (hits on 2-3)
    assets/enemies/shinobi/windup/windup_00..02.png  32x24, crouch before the dash (telegraph)
    assets/enemies/shinobi/dash/dash_00..02.png      32x24, dashing, dagger thrust forward
"""

import argparse
import math
import os

import generate_player_sprites as base
from pixelart import preview_sheet, write_png

SHINOBI_PALETTE = dict(
    base.PALETTE,
    suit=(36, 34, 42, 255),        # near-black garb
    suit_hi=(62, 60, 74, 255),
    suit_sh=(24, 22, 30, 255),
    leg=(36, 34, 42, 255),
    leg_sh=(24, 22, 30, 255),
    red=(132, 64, 168, 255),       # purple headband + tails
    red_dk=(92, 40, 120, 255),     # sash
    wrap=(98, 96, 110, 255),
    eye=(226, 48, 48, 255),        # red eyes in the mask slit
    skin=(214, 168, 128, 255),
    hilt=(70, 44, 60, 255),
    guard=(160, 162, 176, 255),    # plain iron fitting
    sheath=(20, 18, 24, 255),
)
DAGGER = 4                                       # blade length in art pixels
STAB = [(255, 255, 255, 255), (214, 196, 240, 255), (168, 132, 220, 255)]
FAST_TAIL = [(0, 0), (-1, 0), (-2, 0), (-3, 1)]
FAST_TAIL2 = [(0, 1), (-1, 1), (-2, 2)]


def run_frames():
    """Low sprint with the dagger held forward in a reverse grip."""
    poses = base.gait_poses(16, amp=3.5, lift=2, bend=2, arm_amp=2, lean=1,
                            tail_len=4, tail_amp=1.0, run=True)
    return [base.attack_frame(dict(p, front_hand=(2, 1), back_hand=(-2, 1)), 30,
                              blade_length=DAGGER, phase=2 * math.pi * i / 16)
            for i, p in enumerate(poses)]


def stab_line(cv, x, y, length):
    """Short horizontal flash in front of the dagger tip."""
    for k in range(length):
        cv.set(x + k, y, STAB[min(2, k * 3 // max(1, length))])


# (pose overrides, dagger angle, stab flash length or 0)
ATTACK_STEPS = [
    ({"bob": 0, "lean": 0, "front_hand": (-1, 0)}, -20, 0),               # pull back
    ({"bob": 1, "lean": 1, "front_hand": (1, 1), "front_foot": (3, 0)}, 0, 0),
    ({"bob": 1, "lean": 1, "front_hand": (4, 1), "front_foot": (3, 0), "back_foot": (-3, 0)}, 0, 5),
    ({"bob": 1, "lean": 1, "front_hand": (4, 1), "front_foot": (3, 0), "back_foot": (-3, 0)}, 10, 3),
    ({"bob": 0, "lean": 0, "front_hand": (1, 2)}, 40, 0),                 # recover
]


def attack_frames():
    frames = []
    for i, (pose, angle, flash) in enumerate(ATTACK_STEPS):
        cv = base.attack_frame(pose, angle, blade_length=DAGGER, phase=2 * math.pi * i / len(ATTACK_STEPS))
        if flash:
            sx = base.BODY_OX + 6 + pose["lean"] + 2 + pose["front_hand"][0]
            sy = base.BODY_OY + 8 + pose["bob"] + pose["front_hand"][1]
            stab_line(cv, sx + DAGGER + 2, sy, flash)
        frames.append(cv)
    return frames


def windup_frames():
    """Crouch low, dagger drawn back - the 'he's about to dash' warning."""
    poses = [
        {"bob": 1, "lean": 0, "front_hand": (-1, 1), "back_foot": (-3, 0), "front_foot": (2, 0)},
        {"bob": 2, "lean": 1, "front_hand": (-2, 1), "back_foot": (-4, 0), "front_foot": (3, 0),
         "back_bend": 1, "front_bend": 1},
        {"bob": 2, "lean": 1, "front_hand": (-2, 0), "back_foot": (-4, 0), "front_foot": (3, 0),
         "back_bend": 1, "front_bend": 1},
    ]
    return [base.attack_frame(p, 200, blade_length=DAGGER, phase=i) for i, p in enumerate(poses)]


def dash_frames():
    """Body low and stretched, dagger thrust straight ahead, tails streaming back."""
    frames = []
    for i in range(3):
        pose = {"bob": 1, "lean": 1, "front_hand": (4, 0), "back_hand": (-3, 1),
                "back_foot": (-4, 1 + i % 2), "front_foot": (3, 0), "back_bend": 1,
                "tail": [(dx, dy - (i % 2) * (dx < -1)) for dx, dy in FAST_TAIL],
                "tail2": FAST_TAIL2}
        cv = base.attack_frame(pose, 0, blade_length=DAGGER)
        sx = base.BODY_OX + 6 + 1 + 2 + 4
        sy = base.BODY_OY + 8 + 1
        stab_line(cv, sx + DAGGER + 2, sy, 2 + i)
        frames.append(cv)
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "enemies", "shinobi"))
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=6)
    args = ap.parse_args()

    base.STYLE = "shinobi"
    base.PALETTE = SHINOBI_PALETTE

    anims = {
        "idle": base.idle_frames(6),
        "walk": base.gait_frames(16, amp=2, lift=1, bend=1, arm_amp=2, lean=0,
                                 tail_len=3, tail_amp=1.0, run=False),
        "run": run_frames(),
        "attack": attack_frames(),
        "windup": windup_frames(),
        "dash": dash_frames(),
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
