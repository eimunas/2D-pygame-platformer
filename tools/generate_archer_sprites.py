"""Generate the samurai archer enemy sprites + his arrow.

Same body/animation code as the ninja and samurai, with an archer look:
straw jingasa hat, plum armour, charcoal hakama, quiver and bow on the back.

Usage (from the repo root):
    python tools/generate_archer_sprites.py
    python tools/generate_archer_sprites.py --preview preview.png

Output (faces RIGHT, flip in game for left):
    assets/enemies/archer/idle/idle_00..05.png     16x16, bow on the back
    assets/enemies/archer/walk/walk_00..15.png     16x16, bow on the back
    assets/enemies/archer/shoot/shoot_00..05.png   32x24: raise, nock, draw, full draw,
                                                   RELEASE (frame 4), recover
    assets/enemies/archer/arrow.png                16x16, pointing right, centred
"""

import argparse
import math
import os

import generate_player_sprites as base
from pixelart import Canvas, preview_sheet, write_png

ARCHER_PALETTE = dict(
    base.PALETTE,
    suit=(112, 52, 92, 255),        # plum lacquered armour
    suit_hi=(152, 80, 122, 255),
    suit_sh=(78, 34, 64, 255),
    leg=(62, 58, 64, 255),          # charcoal hakama
    leg_sh=(44, 42, 48, 255),
    skin=(228, 178, 134, 255),
    red_dk=(176, 138, 64, 255),     # ochre obi
    wrap=(132, 104, 70, 255),       # leather shin guards
    hat=(206, 172, 104, 255),       # straw jingasa
    hat_hi=(232, 204, 140, 255),
    hat_sh=(154, 120, 66, 255),
    quiver=(98, 62, 40, 255),
    bow=(92, 56, 34, 255),
    fletch=(240, 236, 224, 255),
    fletch_red=(196, 44, 40, 255),
)
BOW_HI = (140, 92, 56, 255)
STRING = (232, 226, 210, 255)
SHAFT = (176, 132, 84, 255)
HEAD = (150, 156, 170, 255)

W, H = base.ATTACK_W, base.ATTACK_H
OX, OY = base.BODY_OX, base.BODY_OY


def draw_bow(cv, gx, gy, pull, arrow):
    """Bow gripped at (gx, gy): a 17px tall arc bending forward (+x).
    pull = how far the string is drawn back (0 = resting)."""
    half, bend = 8, 3
    pts = []
    for i in range(-half, half + 1):
        t = i / half
        x = gx + round(bend * (1 - t * t))
        y = gy + i
        pts.append((x, y))
        cv.set(x, y, ARCHER_PALETTE["bow"] if abs(i) > 1 else BOW_HI)
    top, bottom = pts[0], pts[-1]
    nock = (gx - pull, gy)
    cv.line(*top, *nock, STRING)
    cv.line(*nock, *bottom, STRING)
    if arrow:
        cv.line(nock[0], gy, gx + bend + 3, gy, SHAFT)
        cv.set(gx + bend + 3, gy, HEAD)
        cv.set(gx + bend + 4, gy, HEAD)
        cv.set(nock[0], gy - 1, ARCHER_PALETTE["fletch"])
        cv.set(nock[0] + 1, gy - 1, ARCHER_PALETTE["fletch_red"])
    return nock


# (body pose overrides, bow hand (x,y rel. to front shoulder), string pull, arrow nocked)
SHOOT_STEPS = [
    ({"bob": 0}, (2, 1), 0, False),      # raise the bow
    ({"bob": 0}, (3, 0), 1, True),       # nock an arrow
    ({"bob": 1}, (3, 0), 4, True),       # draw
    ({"bob": 1}, (3, 0), 6, True),       # full draw (aim)
    ({"bob": 1}, (3, 0), 0, False),      # RELEASE - the game spawns the arrow here
    ({"bob": 0}, (2, 1), 0, False),      # recover
]
RELEASE_FRAME = 4


def shoot_frame(overrides, bow_hand, pull, arrow, phase, tails=False):
    """tails=True adds waving headband tails (used for the ninja's own bow frames)."""
    pose = {
        "lean": 0, "back_foot": (-2, 0), "front_foot": (2, 0),
        "back_bend": 0, "front_bend": 0,
        "front_hand": bow_hand, "back_hand": (0, 2),
        "tail": base.tail_points(3, phase, 1.0) if tails else [],
        "tail2": [(dx, dy + 1) for dx, dy in base.tail_points(2, phase + 1.7, 1.0)] if tails else [],
        "sword_on_back": True,
    }
    pose.update(overrides)
    sx = 6 + pose["lean"] + 2            # front shoulder (see draw_ninja)
    sy = 8 + pose["bob"]
    # string hand: at the nock point when drawing, flung back right after release
    nock_x = sx + bow_hand[0] - pull
    if pull:
        pose["back_hand"] = (nock_x - (6 + pose["lean"] + 1), bow_hand[1])
    elif overrides is SHOOT_STEPS[RELEASE_FRAME][0]:
        pose["back_hand"] = (-3, -1)
    body = base.draw_ninja(pose, outline=False)

    cv = Canvas(W, H)
    for y in range(base.SIZE):
        for x in range(base.SIZE):
            if body.px[y][x] is not None:
                cv.set(x + OX, y + OY, body.px[y][x])
    gx, gy = OX + sx + bow_hand[0], OY + sy + bow_hand[1]
    draw_bow(cv, gx, gy, pull, arrow)
    cv.set(gx, gy, ARCHER_PALETTE["skin"])           # bow hand over the grip
    cv.outline(ARCHER_PALETTE["outline"])
    if overrides is SHOOT_STEPS[RELEASE_FRAME][0]:   # string snap: two motion ticks
        cv.set(gx - 2, gy - 3, STRING)
        cv.set(gx - 2, gy + 3, STRING)
    return cv


def shoot_frames(tails=False):
    return [shoot_frame(o, hand, pull, arrow, 2 * math.pi * i / len(SHOOT_STEPS), tails)
            for i, (o, hand, pull, arrow) in enumerate(SHOOT_STEPS)]


def make_arrow():
    """16x16, arrow pointing right through the centre (so rotation pivots nicely)."""
    cv = Canvas(16, 16)
    y = 8
    cv.line(2, y, 12, y, SHAFT)
    cv.set(13, y, HEAD)
    cv.set(14, y, HEAD)
    cv.set(13, y - 1, HEAD)
    cv.set(13, y + 1, HEAD)
    for x in (2, 3, 4):                               # fletching
        cv.set(x, y - 1, ARCHER_PALETTE["fletch"])
        cv.set(x, y + 1, ARCHER_PALETTE["fletch_red"] if x == 3 else ARCHER_PALETTE["fletch"])
    cv.outline(ARCHER_PALETTE["outline"])
    return cv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "enemies", "archer"))
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=6)
    args = ap.parse_args()

    base.STYLE = "archer"
    base.PALETTE = ARCHER_PALETTE

    anims = {
        "idle": base.idle_frames(6),
        "walk": base.gait_frames(16, amp=2, lift=1, bend=1, arm_amp=2, lean=0,
                                 tail_len=3, tail_amp=1.0, run=False),
        "shoot": shoot_frames(),
    }
    for name, frames in anims.items():
        for i, cv in enumerate(frames):
            write_png(os.path.join(args.out, name, f"{name}_{i:02d}.png"), cv.rgba_rows(), cv.w, cv.h)
        print(f"{name}: {len(frames)} frames ({frames[0].w}x{frames[0].h})")
    arrow = make_arrow()
    arrow.save(os.path.join(args.out, "arrow.png"))
    print("arrow.png")

    if args.preview:
        preview_sheet(args.preview, list(anims.values()) + [[arrow]], scale=args.scale)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
