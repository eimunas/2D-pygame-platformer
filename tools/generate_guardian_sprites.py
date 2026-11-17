"""Generate the guardian enemy sprites (stdlib only): a tall samurai in dark
lacquered iron armour (horned kabuto, a face mask with a red glint), a long
yari spear and a big crimson tower shield with a gold crest.

Every animation is drawn three times - shield intact, shield cracked, and with
the shield gone (broken off) - so the game can show the shield wearing down.

Usage (from the repo root):
    python tools/generate_guardian_sprites.py
    python tools/generate_guardian_sprites.py --preview preview.png

Output (faces RIGHT, flip in game for left; all 40x28, feet on the bottom row,
body centred):
    assets/enemies/guardian/<anim>/...           shield intact
    assets/enemies/guardian/cracked/<anim>/...   shield cracked (under half)
    assets/enemies/guardian/broken/<anim>/...    no shield
    anims: idle (4), walk (8), attack (6: lower spear, draw back, thrust x3, pull back)
"""

import argparse
import math
import os

from pixelart import Canvas, preview_sheet, rgb, write_png

W, H = 40, 28
CX = 20                                                                # body centre column
OUT = rgb(14, 12, 18)
ARMOR = (rgb(88, 90, 110), rgb(58, 60, 78), rgb(36, 36, 50))           # light, mid, dark iron
GOLD = (rgb(196, 160, 78), rgb(128, 98, 50))
LACE = rgb(122, 34, 46)
HAKAMA = (rgb(42, 36, 50), rgb(28, 24, 34))
MASK = rgb(30, 22, 28)
EYE = rgb(255, 72, 56)
STEEL = (rgb(220, 224, 234), rgb(150, 156, 172))
SHAFT = (rgb(104, 70, 44), rgb(72, 48, 30))
TASSEL = rgb(170, 40, 44)
SHIELD = (rgb(116, 44, 46), rgb(86, 30, 36), rgb(60, 22, 30))          # crimson lacquer
CRACK = rgb(24, 14, 20)


def guardian(phase=0.0, feet=(0, 0, 0, 0), bob=0, lean=0, spear="up", tip=0, shield="full"):
    """feet: (back dx, back lift, front dx, front lift); bob: + crouches down;
    lean: + forward; spear: 'up' (held upright behind him), 'low' (lowered,
    angled) or 'level' with its blade tip at column `tip`; shield: full/cracked/none."""
    cv = Canvas(W, H)
    x0 = CX + lean                      # torso shift
    top = bob                           # everything above the legs moves with the bob

    # ---- spear held upright behind him (drawn first: it's at his back)
    if spear == "up":
        sx = x0 - 6
        cv.line(sx, 3 + top, sx, 27, SHAFT[1])
        cv.rect(sx, 0 + top, sx, 2 + top, STEEL[0])          # blade
        cv.set(sx - 1, 2 + top, STEEL[1])
        cv.set(sx + 1, 2 + top, STEEL[1])
        cv.set(sx - 1, 4 + top, TASSEL)                      # red tassel under the blade
        cv.set(sx - 1, 5 + top, TASSEL)

    # ---- back shoulder guard (sode) + back arm holding the spear
    cv.rect(x0 - 4, 10 + top, x0 - 2, 14 + top, ARMOR[2])
    cv.set(x0 - 4, 14 + top, LACE)
    if spear == "up":
        back_hand = (x0 - 6, 15 + top)
    elif spear == "low":
        back_hand = (x0 - 1, 15 + top)
    else:
        back_hand = (tip - 17, 11 + top)

    # ---- legs: hakama trousers, iron shin guards, sandals
    bdx, blift, fdx, flift = feet
    for lx, lift, shade in ((CX - 3 + bdx, blift, 1), (CX + 1 + fdx, flift, 0)):
        bottom = 27 - lift
        cv.rect(lx, 20 + top, lx + 2, bottom - 4, HAKAMA[shade])
        cv.rect(lx, bottom - 3, lx + 2, bottom - 1, ARMOR[2 if shade else 1])   # shin guard
        cv.set(lx + 1, bottom - 2, GOLD[1])
        cv.rect(lx, bottom, lx + 3, bottom, HAKAMA[1])                          # sandal

    # ---- kusazuri: the plated skirt, two rows of lacing
    for y in range(16 + top, 21 + top):
        half = 3 + (y - 16 - top) * 0.5
        for x in range(int(x0 - half), int(x0 + half) + 1):
            c = ARMOR[2] if x < x0 - 1 else ARMOR[1]
            if (y - top) in (17, 19) and x % 2 == 0:
                c = LACE
            cv.set(x, y, c)

    # ---- do: the chest plate
    cv.rect(x0 - 3, 9 + top, x0 + 3, 15 + top, ARMOR[1])
    cv.rect(x0 - 3, 9 + top, x0 - 2, 15 + top, ARMOR[2])                 # shaded side
    cv.rect(x0 + 1, 10 + top, x0 + 2, 12 + top, ARMOR[0])                # light on the chest
    cv.rect(x0 - 3, 13 + top, x0 + 3, 13 + top, GOLD[1])                 # gold trim band
    cv.rect(x0 - 3, 15 + top, x0 + 3, 15 + top, LACE)                    # belt

    # ---- head: neck guard, horned kabuto, black face mask with a red eye
    hx = x0 + 1
    cv.rect(hx - 3, 6 + top, hx - 1, 9 + top, ARMOR[2])                  # shikoro (flared at the back)
    cv.set(hx - 4, 8 + top, ARMOR[2])
    cv.set(hx - 4, 9 + top, ARMOR[2])
    cv.rect(hx - 2, 3 + top, hx + 2, 5 + top, ARMOR[1])                  # helmet bowl
    cv.rect(hx - 1, 3 + top, hx + 1, 3 + top, ARMOR[0])
    cv.rect(hx - 3, 6 + top, hx + 3, 6 + top, ARMOR[2])                  # brim
    cv.rect(hx, 7 + top, hx + 2, 9 + top, MASK)                          # menpo
    cv.set(hx + 2, 7 + top, EYE)
    cv.set(hx + 1, 9 + top, ARMOR[1])                                    # mask's mouth guard
    for i, (dx, dy) in enumerate(((-2, 1), (-3, 0), (-3, -1), (3, 1), (4, 0), (4, -1), (0, 2))):
        cv.set(hx + dx, 2 + dy + top, GOLD[0] if i < 6 else GOLD[1])     # crescent crest (kuwagata)

    # ---- spear lowered for the thrust (in front of his body, over the shield)
    if spear == "low":
        cv.line(x0 - 4, 18 + top, x0 + 12, 9 + top, SHAFT[0])
        cv.line(x0 + 13, 8 + top, x0 + 15, 7 + top, STEEL[0])
        cv.set(x0 + 11, 11 + top, TASSEL)
    elif spear == "level":
        y = 10 + top                    # over the top of the shield
        cv.line(tip - 22, y, tip - 3, y, SHAFT[0])
        cv.set(tip - 22, y + 1, SHAFT[1])
        cv.rect(tip - 2, y, tip, y, STEEL[0])
        cv.set(tip - 2, y - 1, STEEL[1])
        cv.set(tip - 2, y + 1, STEEL[1])
        cv.set(tip - 4, y + 1, TASSEL)
        cv.set(tip - 5, y + 1, TASSEL)

    # back arm on top of the body when it reaches forward
    sh = (x0 - 2, 11 + top)
    cv.line(sh[0], sh[1], back_hand[0], back_hand[1], ARMOR[2], width=2)
    cv.rect(back_hand[0], back_hand[1], back_hand[0] + 1, back_hand[1], ARMOR[0])   # gauntlet

    # ---- the tower shield on his front arm
    if shield != "none":
        sx0 = x0 + 4 - (1 if spear == "level" and tip >= 36 else 0)
        sy0 = 10 + top + (1 if spear == "level" else 0)
        sx1, sy1 = sx0 + 4, sy0 + 12
        cv.rect(sx0, sy0, sx1, sy1, ARMOR[2])                            # iron rim
        cv.rect(sx0 + 1, sy0 + 1, sx1 - 1, sy1 - 1, SHIELD[1])
        cv.rect(sx0 + 1, sy0 + 1, sx0 + 1, sy1 - 1, SHIELD[2])
        cv.rect(sx1 - 1, sy0 + 1, sx1 - 1, sy0 + 4, SHIELD[0])
        my = sy0 + 5                                                     # gold mon (crest)
        cv.set(sx0 + 2, my - 1, GOLD[0])
        cv.set(sx0 + 1, my, GOLD[1])
        cv.set(sx0 + 3, my, GOLD[0])
        cv.set(sx0 + 2, my + 1, GOLD[0])
        cv.set(sx0 + 2, my, SHIELD[2])
        for k in (3, 9):                                                 # iron bands
            cv.rect(sx0 + 1, sy0 + k, sx1 - 1, sy0 + k, ARMOR[1])
        if shield == "cracked":
            for dx, dy in ((3, 0), (3, 1), (2, 2), (2, 3), (3, 4), (1, 6), (2, 7), (3, 8),
                           (3, 9), (2, 10), (1, 11)):
                cv.set(sx0 + dx, sy0 + dy, CRACK)
            cv.set(sx1, sy0 + 7, None)                                   # a chip out of the rim
            cv.set(sx1, sy0 + 8, None)
    else:
        # bare front arm, fist clenched
        cv.line(x0 + 2, 11 + top, x0 + 4, 15 + top, ARMOR[1], width=2)
        cv.rect(x0 + 4, 15 + top, x0 + 5, 16 + top, ARMOR[0])

    cv.outline(OUT)
    return cv


# ---------------------------------------------------------------- animations
def idle_frames(shield):
    return [guardian(i, bob=(0, 0, 1, 1)[i], shield=shield) for i in range(4)]


def walk_frames(shield):
    frames = []
    for i in range(8):
        s = math.sin(2 * math.pi * i / 8)
        feet = (round(-2 * s), 1 if s < -0.6 else 0, round(2 * s), 1 if s > 0.6 else 0)
        frames.append(guardian(i, feet=feet, bob=1 if i in (0, 4) else 0, shield=shield))
    return frames


def attack_frames(shield):
    return [
        guardian(0, spear="low", bob=1, shield=shield),                              # lowers the yari
        guardian(1, spear="level", tip=28, lean=-1, feet=(0, 0, 1, 0), shield=shield),   # draws back
        guardian(2, spear="level", tip=35, lean=1, feet=(-1, 0, 3, 0), shield=shield),   # thrust!
        guardian(3, spear="level", tip=38, lean=2, feet=(-1, 0, 3, 0), shield=shield),
        guardian(4, spear="level", tip=38, lean=2, feet=(-1, 0, 3, 0), shield=shield),
        guardian(5, spear="level", tip=31, lean=0, feet=(0, 0, 1, 0), shield=shield),    # pulls back
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "enemies", "guardian"))
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=6)
    args = ap.parse_args()
    rows = []
    for shield, sub in (("full", ""), ("cracked", "cracked"), ("none", "broken")):
        anims = {"idle": idle_frames(shield), "walk": walk_frames(shield), "attack": attack_frames(shield)}
        for name, frames in anims.items():
            for i, cv in enumerate(frames):
                write_png(os.path.join(args.out, sub, name, f"{name}_{i:02d}.png"), cv.rgba_rows(), cv.w, cv.h)
            print(f"{sub or 'full'}/{name}: {len(frames)} frames ({W}x{H})")
            rows.append(frames)
    if args.preview:
        preview_sheet(args.preview, rows, scale=args.scale, bg=(70, 74, 88, 255))
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
