"""Generate the trader NPC, the coin and the shop item icons.

Usage (from the repo root):
    python tools/generate_trader_sprites.py
    python tools/generate_trader_sprites.py --preview preview.png

Output:
    assets/npcs/trader/idle/idle_00..05.png   16x16, faces RIGHT (flipped in game to face you):
                                              wandering merchant - straw hat, grey beard,
                                              brown travelling clothes, wooden pack on his back
    assets/items/coin/coin_00..07.png         16x16 spinning gold mon coin (square hole)
    assets/items/bow.png                      16x16 shop icon
    assets/items/bomb.png                     16x16 shop icon (ceramic horoku bomb, lit fuse)
    assets/items/katana.png                   16x16 weapon icon (the ninja's own sword)
"""

import argparse
import math
import os

import generate_player_sprites as base
from pixelart import Canvas, preview_sheet, write_png

OUTLINE = (14, 12, 22, 255)

TRADER_PALETTE = dict(
    base.PALETTE,
    suit=(124, 84, 52, 255),        # brown travelling kimono
    suit_hi=(156, 110, 70, 255),
    suit_sh=(92, 60, 38, 255),
    leg=(70, 64, 58, 255),          # dark grey trousers
    leg_sh=(50, 46, 42, 255),
    red_dk=(62, 96, 84, 255),       # green-blue sash
    wrap=(196, 186, 160, 255),      # cloth leggings
    skin=(226, 176, 132, 255),
    eye=(36, 26, 22, 255),
    hair=(150, 150, 156, 255),
    beard=(204, 204, 208, 255),
    hat=(206, 172, 104, 255),
    hat_hi=(232, 204, 140, 255),
    hat_sh=(154, 120, 66, 255),
    pack=(150, 104, 58, 255),       # wooden backpack
    pack_sh=(104, 70, 40, 255),
    bundle=(66, 102, 150, 255),     # blue cloth bundle on top
    bundle_hi=(104, 142, 190, 255),
)

GOLD = (232, 186, 82, 255)
GOLD_HI = (255, 234, 150, 255)
GOLD_SH = (178, 124, 42, 255)


# ---------------------------------------------------------------- coin
def coin_frame(angle):
    """Gold mon coin (round, square hole) seen at `angle` degrees of its spin."""
    cv = Canvas(16, 16)
    cx, cy, r = 7.5, 7.5, 4.6
    squash = abs(math.cos(math.radians(angle)))
    rx = max(0.5, r * squash)
    if squash < 0.25:                                   # edge-on: a thin bar
        cv.rect(7, 3, 8, 12, GOLD_SH)
        cv.rect(7, 4, 7, 11, GOLD)
    else:
        def color(x, y, nx, ny):
            if abs(x - cx) < 1.2 * squash and abs(y - cy) < 1.2 and squash > 0.6:
                return None                             # square hole
            if nx * nx + ny * ny > 0.62:
                return GOLD_SH if nx > 0.2 or ny > 0.2 else GOLD     # rim
            return GOLD_HI if (nx < -0.2 and ny < -0.1) else GOLD
        cv.ellipse(cx, cy, rx, r, color)
    cv.outline(OUTLINE)
    if squash > 0.9:                                    # sparkle on the full face
        cv.set(4, 4, (255, 255, 255, 255))
    return cv


def coin_frames(n=8):
    return [coin_frame(360 * i / n) for i in range(n)]


# ---------------------------------------------------------------- icons
def bow_icon():
    cv = Canvas(16, 16)
    wood, wood_hi = (120, 76, 42, 255), (164, 112, 66, 255)
    string = (232, 226, 210, 255)
    # recurve limb from bottom-left to top-right, bending away from the string
    pts = []
    for i in range(13):
        t = i / 12
        bulge = 1.9 * math.sin(math.pi * t)                 # gentle arc away from the string
        x = 3 + 10 * t - bulge
        y = 13 - 10 * t - bulge
        pts.append((round(x), round(y)))
    for a, b in zip(pts, pts[1:]):
        cv.line(*a, *b, wood)
    cv.set(*pts[6], wood_hi)
    cv.set(*pts[5], wood_hi)
    cv.rect(pts[6][0] - 1, pts[6][1], pts[6][0], pts[6][1] + 1, (196, 44, 40, 255))   # red grip wrap
    cv.line(*pts[0], *pts[-1], string)
    cv.outline(OUTLINE)
    return cv


def katana_icon():
    """Diagonal katana: steel blade with a pale edge, gold tsuba, wrapped hilt."""
    cv = Canvas(16, 16)
    steel, edge = (196, 204, 220, 255), (240, 244, 252, 255)
    cv.line(5, 10, 14, 1, steel)                        # blade
    cv.line(6, 10, 14, 2, edge)
    cv.rect(4, 10, 6, 10, (217, 164, 65, 255))          # tsuba (guard)
    cv.rect(5, 9, 5, 11, (217, 164, 65, 255))
    cv.line(1, 14, 4, 11, (60, 40, 30, 255))            # hilt
    cv.set(2, 13, (196, 44, 40, 255))                   # red wrap
    cv.set(3, 12, (196, 44, 40, 255))
    cv.outline(OUTLINE)
    return cv


def bomb_icon():
    cv = Canvas(16, 16)
    body, body_hi, body_sh = (70, 74, 92, 255), (120, 126, 148, 255), (44, 46, 60, 255)

    def color(x, y, nx, ny):
        if nx < -0.2 and ny < -0.2 and nx * nx + ny * ny < 0.55:
            return body_hi
        if nx + ny > 0.8:
            return body_sh
        return body
    cv.ellipse(7, 9.5, 4.6, 4.6, color)
    cv.rect(6, 4, 8, 4, (150, 112, 70, 255))            # rope collar
    cv.line(9, 3, 11, 1, (196, 160, 110, 255))          # fuse
    cv.outline(OUTLINE)
    cv.set(12, 0, (255, 232, 120, 255))                 # spark
    cv.set(13, 1, (255, 150, 60, 255))
    cv.set(12, 2, (255, 150, 60, 255))
    cv.set(11, 0, (255, 150, 60, 255))
    return cv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="assets")
    ap.add_argument("--preview")
    ap.add_argument("--scale", type=int, default=6)
    args = ap.parse_args()

    base.STYLE = "trader"
    base.PALETTE = TRADER_PALETTE
    trader = base.idle_frames(6)
    coins = coin_frames(8)
    icons = {"bow": bow_icon(), "bomb": bomb_icon(), "katana": katana_icon()}

    for i, cv in enumerate(trader):
        write_png(os.path.join(args.assets, "npcs", "trader", "idle", f"idle_{i:02d}.png"),
                  cv.rgba_rows(), cv.w, cv.h)
    for i, cv in enumerate(coins):
        cv.save(os.path.join(args.assets, "items", "coin", f"coin_{i:02d}.png"))
    for name, cv in icons.items():
        cv.save(os.path.join(args.assets, "items", f"{name}.png"))
    print(f"trader idle: {len(trader)} frames | coin: {len(coins)} frames | icons: {', '.join(icons)}")

    if args.preview:
        preview_sheet(args.preview, [trader, coins, list(icons.values())], scale=args.scale)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
