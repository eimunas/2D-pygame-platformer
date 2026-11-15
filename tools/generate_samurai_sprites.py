"""Generate the samurai enemy sprites, using the ninja's body/animation code
with a samurai look (kabuto helmet, red lacquered armour, hakama, hip katana).

Usage (from the repo root):
    python tools/generate_samurai_sprites.py
    python tools/generate_samurai_sprites.py --preview preview.png

Output (faces RIGHT, flip in game for left):
    assets/enemies/samurai/idle/idle_00..05.png      16x16, katana sheathed
    assets/enemies/samurai/walk/walk_00..15.png      16x16, katana sheathed
    assets/enemies/samurai/run/run_00..15.png        32x24, charging with katana raised
    assets/enemies/samurai/attack/attack_00..05.png  32x24, heavy overhead cut
"""

import argparse
import os

import generate_player_sprites as base
from pixelart import preview_sheet, write_png

SAMURAI_PALETTE = dict(
    base.PALETTE,
    suit=(156, 42, 38, 255),       # red lacquered armour
    suit_hi=(198, 72, 56, 255),
    suit_sh=(104, 28, 30, 255),
    leg=(58, 50, 64, 255),         # dark hakama
    leg_sh=(40, 34, 46, 255),
    skin=(226, 176, 132, 255),
    red_dk=(34, 36, 58, 255),      # obi (belt)
    wrap=(92, 92, 104, 255),       # iron shin guards
    sheath=(30, 24, 28, 255),
    hilt=(64, 42, 32, 255),
    iron=(54, 56, 68, 255),        # helmet
    iron_hi=(92, 96, 112, 255),
)

# sword held raised forward while charging
RUN_HAND, RUN_BACK_HAND, RUN_SWORD_ANGLE = (2, -1), (1, 0), -55


def run_with_katana_frames():
    poses = base.gait_poses(16, amp=3.5, lift=2, bend=2, arm_amp=2, lean=1,
                            tail_len=4, tail_amp=1.0, run=True)
    return [base.attack_frame(dict(p, front_hand=RUN_HAND, back_hand=RUN_BACK_HAND),
                              RUN_SWORD_ANGLE)
            for p in poses]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "enemies", "samurai"))
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=6)
    args = ap.parse_args()

    base.STYLE = "samurai"
    base.PALETTE = SAMURAI_PALETTE

    anims = {
        "idle": base.idle_frames(6),
        "walk": base.gait_frames(16, amp=2, lift=1, bend=1, arm_amp=2, lean=0,
                                 tail_len=3, tail_amp=1.0, run=False),
        "run": run_with_katana_frames(),
        "attack": base.attack_frames("attack3"),   # heavy overhead cut
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
