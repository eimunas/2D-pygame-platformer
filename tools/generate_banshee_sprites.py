"""Generate the banshee enemy sprites (stdlib only): a gaunt woman with grey skin,
long messy black hair (a few strands hanging over her face) and a tattered grey
dress down to her bare feet. She walks slowly and screams.

Usage (from the repo root):
    python tools/generate_banshee_sprites.py
    python tools/generate_banshee_sprites.py --preview preview.png

Output (faces RIGHT, flip in game for left; all 24x24, feet on the bottom row,
body centred like the other characters):
    assets/enemies/banshee/idle/idle_00..05.png      standing hunched, hair stirring
    assets/enemies/banshee/walk/walk_00..07.png      slow shuffle
    assets/enemies/banshee/windup/windup_00..02.png  arms rise, eyes flare (the warning)
    assets/enemies/banshee/scream/scream_00..03.png  mouth wide, head back, hair blown back
"""

import argparse
import math
import os
import random

from pixelart import Canvas, preview_sheet, rgb, write_png

W, H = 24, 24
OUT = rgb(16, 12, 20)
SKIN = (rgb(196, 202, 204), rgb(162, 168, 174), rgb(118, 124, 134))   # light, mid, shadow
HAIR = (rgb(22, 18, 26), rgb(44, 38, 50), rgb(66, 58, 72))            # black, dark, sheen
DRESS = (rgb(98, 94, 102), rgb(76, 72, 84), rgb(56, 52, 64))         # dirty, faded
MOUTH = rgb(20, 10, 16)
EYE = (rgb(214, 226, 222), rgb(190, 255, 236), rgb(255, 255, 255))   # pale, glowing, flare
SOCKET = rgb(46, 40, 54)


def lerp(a, b, t):
    return a + (b - a) * t


def woman(phase, feet=(0, 0, 0, 0), bob=0, lean=0, arms=(0.0, 0.0), arms_mode="down",
          mouth=0, glow=0.0, hair_blow=0.0, head_back=0):
    """feet: (back dx, back lift, front dx, front lift); lean: + hunched forward;
    arms: swing for 'down', or how far raised for 'up'; arms_mode: down/up/back;
    mouth: 0..3; glow: eyes 0..1; hair_blow: 0 hanging .. 1 streaming back;
    head_back: head tilts back (screaming)."""
    cv = Canvas(W, H)
    rnd = random.Random("hair")                       # same messy strands every frame
    hx, hy = 13 + lean - head_back, 5 + bob           # head centre
    sx, sy = 12 + lean, 9 + bob                       # shoulders centre

    def arm(shoulder, hand, color):
        for i in range(7):
            t = i / 6
            cv.set(lerp(shoulder[0], hand[0], t), lerp(shoulder[1], hand[1], t), color)
        cv.set(hand[0], hand[1] + 1, color)            # long fingers

    back_sh, front_sh = (sx - 2, sy + 1), (sx + 2, sy + 1)
    if arms_mode == "down":
        back_hand = (sx - 3 - arms[0], sy + 7)
        front_hand = (sx + 3 + arms[1], sy + 7)
    elif arms_mode == "up":
        back_hand = (sx - 3 - 2 * arms[0], sy + 6 - 9 * arms[0])
        front_hand = (sx + 3 + 2 * arms[1], sy + 6 - 9 * arms[1])
    else:                                             # flung back
        back_hand = (sx - 8, sy + 2)
        front_hand = (sx - 6, sy + 4)

    # back arm (behind everything)
    arm(back_sh, back_hand, SKIN[2])

    # --- long hair behind her back: messy strands from the crown down past the shoulders
    for k in range(7):
        x0 = hx - 2 + k * 0.45
        y0 = hy - 3 + (k % 3) * 0.4
        length = 9 + rnd.randrange(0, 5) + 2 * hair_blow
        jitter = [rnd.uniform(-0.8, 0.8) for _ in range(16)]
        for i in range(int(length)):
            t = i / length
            if hair_blow:
                x = x0 - i * lerp(0.5, 1.05, hair_blow)
                y = y0 + i * lerp(0.9, 0.2, hair_blow) + math.sin(phase + i * 0.7 + k) * 1.2 * t + (k - 3) * 1.3 * hair_blow
                if i > 2 and (i + k) % 3 == 0:
                    continue                           # gaps: separate wild strands
            else:
                x = x0 - 2.2 - i * 0.18 + jitter[i] * t + math.sin(phase + k + i * 0.4) * 0.6 * t
                y = y0 + i
            cv.set(x, y, HAIR[0] if k % 3 else HAIR[1])
        if not hair_blow and rnd.random() < 0.6:     # a flyaway hair sticking out
            cv.set(x0 - 3 - rnd.randrange(0, 2), y0 + rnd.randrange(3, 8), HAIR[1])

    # --- tattered dress: narrow shoulders -> wider, ragged hem above the feet
    for y in range(sy, 21):
        t = (y - sy) / (21 - sy)
        half = 1.3 + 2.0 * t + math.sin(phase + y * 0.8) * 0.3 * t
        cx = sx - 0.6 * t * lean
        for x in range(int(round(cx - half)), int(round(cx + half)) + 1):
            rel = (x - (cx - half)) / (2 * half + 0.01)
            c = DRESS[2] if rel < 0.25 else DRESS[0] if rel > 0.6 else DRESS[1]
            cv.set(x, y, c)
    for x in range(int(sx - 4), int(sx + 5)):         # ragged hem: uneven strips
        if math.sin(x * 2.3 + phase) > -0.2:
            cv.set(x, 21, DRESS[2])
            if math.sin(x * 4.1) > 0.4:
                cv.set(x, 22, DRESS[2])

    # --- bare grey feet poking out under the hem
    bdx, blift, fdx, flift = feet
    for fx, lift, col in ((sx - 1 + bdx, blift, SKIN[2]), (sx + 1 + fdx, flift, SKIN[1])):
        cv.set(fx, 23 - lift, col)
        cv.set(fx + 1, 23 - lift, col)

    # --- head: a gaunt grey face (5 px wide), hair cap over the top and back
    for y in range(hy - 2, hy + 4):
        for x in range(hx, hx + 4):
            cv.set(x, y, SKIN[0] if x > hx + 1 else SKIN[1])
    cv.set(hx + 3, hy + 3, None)                       # pointed chin
    cv.set(hx + 1, hy + 2, SKIN[2])                    # hollow cheek
    cv.rect(hx - 2, hy - 3, hx + 3, hy - 3, HAIR[0])   # crown
    cv.rect(hx - 2, hy - 2, hx - 1, hy + 3, HAIR[0])   # back of the head
    cv.set(hx + 1, hy - 3, HAIR[2])                    # a little sheen
    eye = EYE[2] if glow > 0.7 else EYE[1] if glow > 0.3 else EYE[0]
    cv.rect(hx + 1, hy - 1, hx + 2, hy - 1, SOCKET)   # dark, sunken eye socket...
    cv.set(hx + 2, hy - 1, eye)                        # ...with a pale eye staring out
    cv.set(hx + 2, hy, SKIN[2])                        # shadow under the eye
    if mouth:
        for y in range(hy + 1, min(hy + 1 + mouth, hy + 4)):
            cv.set(hx + 2, y, MOUTH)
            if mouth > 1:
                cv.set(hx + 3, y, MOUTH)
    else:
        cv.set(hx + 2, hy + 2, SKIN[2])                # thin, grim mouth
        cv.set(hx + 3, hy + 2, SKIN[2])

    # --- strands hanging down over the face (not when it's blown back)
    if hair_blow < 0.5:
        for i in range(5):                             # hair falling over her temple...
            cv.set(hx, hy - 2 + i, HAIR[0])
        for i in range(8):                             # ...and a loose strand down in front
            cv.set(hx + 4 + (i > 5), hy - 2 + i, HAIR[1] if i % 2 else HAIR[0])

    # front arm
    arm(front_sh, front_hand, SKIN[1])

    cv.outline(OUT)
    return cv


# ---------------------------------------------------------------- animations
def idle_frames(n=6):
    return [woman(2 * math.pi * i / n, bob=(0, 0, 0, 1, 1, 1)[i], lean=1) for i in range(n)]


def walk_frames(n=8):
    frames = []
    for i in range(n):
        p = 2 * math.pi * i / n
        s = math.sin(p)
        feet = (round(-1.5 * s), 1 if s < -0.5 else 0, round(1.5 * s), 1 if s > 0.5 else 0)
        frames.append(woman(p, feet=feet, bob=1 if i in (0, 4) else 0, lean=1,
                            arms=(round(s), round(-s))))
    return frames


def windup_frames():
    return [woman(0.0, lean=2, arms=(0.3, 0.3), arms_mode="up", glow=0.4, bob=1),
            woman(0.7, lean=1, arms=(0.8, 0.8), arms_mode="up", glow=0.8, mouth=1),
            woman(1.4, lean=0, arms=(1.0, 1.0), arms_mode="up", glow=1.0, mouth=1)]


def scream_frames():
    return [woman(p, arms_mode="back", mouth=3, glow=1.0, hair_blow=1.0, head_back=1, bob=b, lean=-1)
            for p, b in ((0, 0), (1.6, -1), (3.2, 0), (4.8, -1))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "enemies", "banshee"))
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=6)
    args = ap.parse_args()
    anims = {"idle": idle_frames(), "walk": walk_frames(), "windup": windup_frames(), "scream": scream_frames()}
    for name, frames in anims.items():
        for i, cv in enumerate(frames):
            write_png(os.path.join(args.out, name, f"{name}_{i:02d}.png"), cv.rgba_rows(), cv.w, cv.h)
        print(f"{name}: {len(frames)} frames ({W}x{H})")
    if args.preview:
        preview_sheet(args.preview, list(anims.values()), scale=args.scale, bg=(70, 74, 88, 255))
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
