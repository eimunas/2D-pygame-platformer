"""Generate 16x16 pixel-art ninja player sprites.

Uses only the Python standard library (no pygame/Pillow needed).

Usage (from the repo root):
    python tools/generate_player_sprites.py              # writes assets/player/...
    python tools/generate_player_sprites.py --preview p.png   # also writes a scaled preview sheet

Output:
    assets/player/idle/idle_00.png .. idle_05.png   (6 frames)
    assets/player/walk/walk_00.png .. walk_15.png   (16 frames)
    assets/player/run/run_00.png   .. run_15.png    (16 frames)
    assets/player/jump/jump_00.png .. jump_03.png   (4 frames, rising)
    assets/player/fall/fall_00.png .. fall_03.png   (4 frames, falling)
    assets/player/flip/flip_00.png .. flip_07.png   (8 frames, double-jump somersault)
    assets/player/attack1..3/attackN_00.png .. _05.png  (6 frames each, 32x24:
        horizontal cut, rising cut, heavy overhead cut)
    assets/player/dash/dash_00.png .. dash_03.png   (4 frames, 32x24, dash attack)
    assets/player/death/death_00.png .. death_08.png (9 frames, 32x16: wounded,
        kneels, falls face-down)
    assets/player/bow/bow_00.png .. bow_05.png     (6 frames, 32x24: draw and shoot the
        bow bought from the trader; the arrow leaves on frame 4)

The character faces RIGHT. Flip horizontally in-game for left.
"""

import argparse
import math
import os
import struct
import zlib

from pixelart import Canvas as SizedCanvas, preview_sheet

SIZE = 16

# ---------------------------------------------------------------- palette
PALETTE = {
    "outline": (14, 12, 22, 255),
    "suit": (46, 53, 87, 255),        # indigo ninja garb
    "suit_hi": (70, 82, 128, 255),    # front arm / highlights
    "suit_sh": (30, 34, 58, 255),     # back limbs
    "skin": (232, 180, 138, 255),
    "eye": (20, 16, 24, 255),
    "red": (196, 44, 40, 255),        # headband + tails
    "red_dk": (128, 28, 30, 255),     # sash / second tail
    "wrap": (150, 156, 176, 255),     # shin wraps
    "hilt": (92, 58, 34, 255),        # katana handle
    "guard": (217, 164, 65, 255),     # tsuba (gold)
    "sheath": (52, 36, 30, 255),
    "leg": (46, 53, 87, 255),         # front leg (same as suit for the ninja)
    "leg_sh": (30, 34, 58, 255),      # back leg + feet
}

# Which character draw_ninja() draws: "ninja" (player), "samurai", "archer",
# "shinobi" (enemies) or "trader" (NPC). The generators in tools/ switch this and PALETTE.
STYLE = "ninja"


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
        self.w = self.h = SIZE
        self.px = [[None] * SIZE for _ in range(SIZE)]

    def set(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < SIZE and 0 <= y < SIZE:
            self.px[y][x] = color

    def rect(self, x0, y0, x1, y1, color):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, color)

    def line(self, x0, y0, x1, y1, color, width=1):
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            for w in range(width):
                self.set(x0 + w, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def outline(self, color):
        """Add a 1px outline around every filled pixel (4-neighbourhood)."""
        add = []
        for y in range(SIZE):
            for x in range(SIZE):
                if self.px[y][x] is not None:
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < SIZE and 0 <= ny < SIZE and self.px[ny][nx] is not None:
                        add.append((x, y))
                        break
        for x, y in add:
            self.px[y][x] = color

    def rgba_rows(self, scale=1):
        rows = []
        for y in range(SIZE):
            row = bytearray()
            for x in range(SIZE):
                c = self.px[y][x] or (0, 0, 0, 0)
                row.extend(bytes(c) * scale)
            for _ in range(scale):
                rows.append(bytes(row))
        return rows


# ---------------------------------------------------------------- PNG writer
def write_png(path, rows, width, height):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + r for r in rows)  # filter type 0 per row
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------- the ninja
def draw_leg(cv, hip_x, hip_y, foot_x, foot_y, bend, color):
    knee_x = (hip_x + foot_x) / 2 + bend
    knee_y = (hip_y + foot_y) / 2
    cv.line(hip_x, hip_y, knee_x, knee_y, color, width=2)
    cv.line(knee_x, knee_y, foot_x, foot_y, color, width=2)
    # shin wrap (one band just above the foot)
    cv.set(foot_x, foot_y - 1, PALETTE["wrap"])
    cv.set(foot_x + 1, foot_y - 1, PALETTE["wrap"])
    # foot (2 px + toe pointing right)
    cv.set(foot_x, foot_y, PALETTE["leg_sh"])
    cv.set(foot_x + 1, foot_y, PALETTE["leg_sh"])
    cv.set(foot_x + 2, foot_y, PALETTE["leg_sh"])


def draw_ninja(pose, outline=True):
    """pose keys:
    bob     - body vertical offset (0/1)
    lean    - upper body x offset (0/1)
    back_foot, front_foot - (x_offset, lift)
    back_bend, front_bend - knee forward bend
    back_hand, front_hand - (x, y) relative to shoulder
    tail    - list of (dx, dy) points for headband tail 1
    tail2   - list of (dx, dy) points for headband tail 2
    """
    P = PALETTE
    cv = Canvas()
    b = pose["bob"]
    ln = pose["lean"]

    hx0 = 6 + ln          # head left x
    head_y = 2 + b
    tx0 = 6 + ln          # torso left x
    torso_y = 7 + b
    hip_x, hip_y = 7, 11 + b
    shoulder_y = 8 + b

    samurai = STYLE == "samurai"
    archer = STYLE == "archer"
    shinobi = STYLE == "shinobi"           # enemy ninja: dagger at the hip, no katana
    trader = STYLE == "trader"             # NPC merchant: straw hat, big pack, no weapon
    armoured = samurai or archer

    # behind everything: ninja katana on the back, samurai katana at the hip,
    # archer bow + quiver on the back
    if samurai:
        cv.line(tx0 - 3, torso_y + 2, tx0 + 1, torso_y + 3, P["sheath"])
    elif archer:
        cv.line(tx0 - 3, torso_y - 3, tx0 + 3, torso_y + 4, P["bow"])        # slung bow stave
        cv.rect(tx0 - 1, torso_y - 1, tx0, torso_y + 3, P["quiver"])        # quiver
        cv.set(tx0 - 1, torso_y - 2, P["fletch"])                          # arrow feathers
        cv.set(tx0, torso_y - 3, P["fletch_red"])
    elif trader:
        # wooden backpack frame with a bundle on top
        cv.rect(tx0 - 3, torso_y - 4, tx0, torso_y + 3, P["pack"])
        cv.rect(tx0 - 3, torso_y - 4, tx0 - 3, torso_y + 3, P["pack_sh"])
        cv.rect(tx0 - 3, torso_y - 1, tx0, torso_y - 1, P["pack_sh"])       # shelf
        cv.rect(tx0 - 2, torso_y - 6, tx0, torso_y - 5, P["bundle"])        # cloth bundle
        cv.set(tx0 - 1, torso_y - 6, P["bundle_hi"])
    elif not shinobi:
        cv.line(tx0 - 1, torso_y, tx0 + 3, torso_y + 3, P["sheath"])

    # back arm
    bhx, bhy = pose["back_hand"]
    cv.line(tx0 + 1, shoulder_y, tx0 + 1 + bhx, shoulder_y + bhy, P["suit_sh"])

    # back leg
    fx, lift = pose["back_foot"]
    draw_leg(cv, hip_x, hip_y, hip_x + fx, 14 - lift, pose["back_bend"], P["leg_sh"])

    # torso
    cv.rect(tx0, torso_y, tx0 + 3, torso_y + 3, P["suit"])
    cv.rect(tx0, torso_y + 3, tx0 + 3, torso_y + 3, P["red_dk"])  # sash / obi
    if armoured:
        cv.rect(tx0, torso_y + 1, tx0 + 3, torso_y + 1, P["suit_sh"])  # armour lacing band
    if samurai:
        cv.rect(tx0 - 1, torso_y, tx0 - 1, torso_y + 1, P["suit"])     # sode (shoulder guards)
        cv.rect(tx0 + 4, torso_y, tx0 + 4, torso_y + 1, P["suit"])

    # front leg
    fx, lift = pose["front_foot"]
    draw_leg(cv, hip_x, hip_y, hip_x + fx, 14 - lift, pose["front_bend"], P["leg"])

    if samurai:
        # kabuto helmet, flared neck guard, gold crest, open face with moustache
        cv.rect(hx0, head_y, hx0 + 4, head_y + 1, P["iron"])
        cv.set(hx0 + 1, head_y, P["iron_hi"])
        cv.set(hx0 + 2, head_y, P["iron_hi"])
        cv.rect(hx0 - 1, head_y + 2, hx0, head_y + 3, P["iron"])      # shikoro (neck guard)
        cv.rect(hx0 + 1, head_y + 2, hx0 + 4, head_y + 4, P["skin"])  # face
        cv.set(hx0 + 3, head_y + 2, P["eye"])
        cv.set(hx0 + 2, head_y + 2, P["eye"])                          # stern brow
        cv.rect(hx0 + 3, head_y + 4, hx0 + 4, head_y + 4, P["eye"])   # moustache
        cv.set(hx0 + 1, head_y + 4, P["iron"])                         # chin strap
        cv.set(hx0 + 3, head_y - 1, P["guard"])                        # maedate (crest)
        cv.set(hx0 + 2, head_y - 2, P["guard"])
        cv.set(hx0 + 4, head_y - 2, P["guard"])
    elif trader:
        # straw hat, friendly face with a grey beard
        cv.rect(hx0, head_y + 1, hx0 + 4, head_y + 4, P["skin"])      # face
        cv.rect(hx0, head_y + 1, hx0, head_y + 3, P["hair"])          # hair at the back
        cv.set(hx0 + 3, head_y + 2, P["eye"])
        cv.rect(hx0 + 2, head_y + 4, hx0 + 4, head_y + 4, P["beard"]) # beard
        cv.set(hx0 + 3, head_y + 5, P["beard"])
        cv.rect(hx0 + 1, head_y - 1, hx0 + 3, head_y - 1, P["hat"])   # hat
        cv.rect(hx0 - 1, head_y, hx0 + 5, head_y, P["hat"])
        cv.set(hx0 + 2, head_y - 1, P["hat_hi"])
        cv.rect(hx0 - 1, head_y + 1, hx0 + 5, head_y + 1, P["hat_sh"]) # brim shade over the eyes line
        cv.set(hx0 + 3, head_y + 2, P["eye"])
    elif archer:
        # jingasa: wide conical straw hat over an open face
        cv.rect(hx0, head_y + 1, hx0 + 4, head_y + 4, P["skin"])      # face
        cv.rect(hx0, head_y + 1, hx0, head_y + 4, P["eye"])           # hair at the back
        cv.set(hx0 + 3, head_y + 2, P["eye"])
        cv.set(hx0 + 4, head_y + 4, P["suit_sh"])                      # chin strap
        cv.rect(hx0 + 1, head_y - 1, hx0 + 3, head_y - 1, P["hat"])   # hat peak
        cv.rect(hx0 - 1, head_y, hx0 + 5, head_y, P["hat"])
        cv.rect(hx0 - 2, head_y + 1, hx0 + 6, head_y + 1, P["hat_sh"])  # wide brim
        cv.set(hx0 + 2, head_y - 1, P["hat_hi"])
    else:
        # head / hood
        cv.rect(hx0, head_y, hx0 + 4, head_y + 4, P["suit"])
        cv.set(hx0 + 1, head_y, P["suit_hi"])
        cv.set(hx0 + 2, head_y, P["suit_hi"])
        # headband
        cv.rect(hx0, head_y + 1, hx0 + 4, head_y + 1, P["red"])
        # eye slit
        cv.rect(hx0 + 2, head_y + 2, hx0 + 4, head_y + 2, P["skin"])
        cv.set(hx0 + 3, head_y + 2, P["eye"])

    # katana hilt (not when the sword is in his hand)
    if pose.get("sword_on_back", True):
        if samurai:                                   # worn at the hip, hilt forward
            cv.set(tx0 + 4, torso_y + 2, P["guard"])
            cv.set(tx0 + 5, torso_y + 1, P["hilt"])
            cv.set(tx0 + 6, torso_y, P["hilt"])
        elif archer or trader:                        # no katana
            pass
        elif shinobi:                                 # tanto tucked in the sash
            cv.set(tx0 + 4, torso_y + 3, P["sheath"])
            cv.set(tx0 + 4, torso_y + 2, P["hilt"])
            cv.set(tx0 + 5, torso_y + 1, P["hilt"])
        else:                                         # over the back shoulder
            cv.set(hx0 - 1, torso_y, P["guard"])
            cv.set(hx0 - 2, torso_y - 1, P["hilt"])
            cv.set(hx0 - 3, torso_y - 2, P["hilt"])

    # headband tails (ninjas only)
    if not armoured and not trader:
        tx, ty = hx0 - 1, head_y + 1
        for dx, dy in pose["tail2"]:
            cv.set(tx + dx, ty + dy, P["red_dk"])
        for dx, dy in pose["tail"]:
            cv.set(tx + dx, ty + dy, P["red"])

    # front arm (drawn last, over torso)
    fhx, fhy = pose["front_hand"]
    sx = tx0 + 2
    cv.line(sx, shoulder_y, sx + fhx, shoulder_y + fhy, P["suit_hi"])
    cv.set(sx + fhx, shoulder_y + fhy, P["skin"])

    if outline:
        cv.outline(P["outline"])
    return cv


def rotate(cv, degrees, cx, cy):
    """Nearest-neighbour rotation (clockwise on screen) around (cx, cy)."""
    out = Canvas()
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    for y in range(SIZE):
        for x in range(SIZE):
            dx, dy = x - cx, y - cy
            ix = round(cx + dx * c + dy * s)     # inverse-map each output pixel
            iy = round(cy - dx * s + dy * c)
            if 0 <= ix < SIZE and 0 <= iy < SIZE:
                out.px[y][x] = cv.px[iy][ix]
    return out


def tail_points(length, phase, amp):
    """Headband tail trailing to the left, waving."""
    pts = []
    for k in range(length):
        dy = round(amp * math.sin(phase + k * 1.1) * (k / max(1, length - 1)))
        pts.append((-k, dy))
    return pts


# ---------------------------------------------------------------- animations
def idle_frames(n=6):
    bobs = [0, 0, 0, 1, 1, 1]
    frames = []
    for i in range(n):
        p = 2 * math.pi * i / n
        frames.append(draw_ninja({
            "bob": bobs[i],
            "lean": 0,
            "back_foot": (-1, 0),
            "front_foot": (1, 0),
            "back_bend": 0,
            "front_bend": 0,
            "back_hand": (0, 2),
            "front_hand": (0, 2),
            "tail": [(dx, dy + 1) for dx, dy in tail_points(3, p, 1.0)],
            "tail2": [(dx, dy + 2) for dx, dy in tail_points(2, p + 1.5, 1.0)],
        }))
    return frames


def gait_frames(n, amp, lift, bend, arm_amp, lean, tail_len, tail_amp, run):
    return [draw_ninja(pose) for pose in
            gait_poses(n, amp, lift, bend, arm_amp, lean, tail_len, tail_amp, run)]


def gait_poses(n, amp, lift, bend, arm_amp, lean, tail_len, tail_amp, run):
    """Pose dicts for a walk/run cycle (also reused for the samurai's sword run)."""
    poses = []
    for i in range(n):
        p = 2 * math.pi * i / n
        s = math.sin(p)
        c = math.cos(p)
        # front leg swings forward while cos > 0, back leg is opposite
        front_x = round(amp * s)
        back_x = round(-amp * s)
        front_lift = round(max(0.0, c) * lift)
        back_lift = round(max(0.0, -c) * lift)
        bob = 1 if abs(s) > 0.7 else 0

        if run:
            # pumping arms: forward hand comes up, back hand stays low
            fa = -arm_amp * s
            front_hand = (round(fa), 0 if fa > 0 else 2)
            back_hand = (round(-fa) - 1, 0 if -fa > 0 else 2)
        else:
            front_hand = (round(-arm_amp * s), 2)
            back_hand = (round(arm_amp * s) - 1, 2)

        poses.append({
            "bob": bob,
            "lean": lean,
            "back_foot": (back_x, back_lift),
            "front_foot": (front_x, front_lift),
            "back_bend": bend if back_lift else 0,
            "front_bend": bend if front_lift else 0,
            "back_hand": back_hand,
            "front_hand": front_hand,
            "tail": tail_points(tail_len, p * 2, tail_amp),
            "tail2": [(dx, dy + 1) for dx, dy in tail_points(tail_len - 1, p * 2 + 1.7, tail_amp)],
        })
    return poses


def air_frames(kind, n=4):
    """kind = 'jump' (rising) or 'fall'. Small loop: headband tails flutter."""
    frames = []
    for i in range(n):
        p = 2 * math.pi * i / n
        wob = round(math.sin(p))
        if kind == "jump":
            pose = {
                "bob": 0, "lean": 1,
                "back_foot": (-2, 0), "back_bend": 0,          # trailing leg straight
                "front_foot": (2, 3), "front_bend": 2,         # knee driven up
                "back_hand": (-3, 1), "front_hand": (2, -2),   # arm reaching up
                # rising -> tails stream downward
                "tail": [(0, 0), (-1, 1), (-2, 2 + wob)],
                "tail2": [(0, 1), (-1, 2 + wob)],
            }
        else:
            pose = {
                "bob": 0, "lean": 0,
                "back_foot": (-2, 0), "back_bend": 1,          # legs dangling apart
                "front_foot": (2, 1), "front_bend": 1,
                "back_hand": (-2, -3), "front_hand": (1, -3),  # arms up for balance
                # falling -> tails flutter upward
                "tail": [(0, 0), (-1, -1), (-2, -1 + wob)],
                "tail2": [(0, 1), (-1, wob)],
            }
        frames.append(draw_ninja(pose))
    return frames


def flip_frames(n=8):
    """Somersault: a tucked ninja rotated a full turn (forward = clockwise)."""
    tuck = draw_ninja({
        "bob": 2, "lean": 0,
        "back_foot": (1, 3), "back_bend": 1,     # knees pulled to the chest
        "front_foot": (3, 3), "front_bend": 2,
        "back_hand": (1, 1), "front_hand": (2, 1),
        "tail": [(0, 0), (-1, 0), (-2, 1)],
        "tail2": [(0, 1), (-1, 2)],
    }, outline=False)
    filled = [(x, y) for y in range(SIZE) for x in range(SIZE) if tuck.px[y][x] is not None]
    cx = (min(x for x, _ in filled) + max(x for x, _ in filled)) / 2
    cy = (min(y for _, y in filled) + max(y for _, y in filled)) / 2
    frames = []
    for i in range(n):
        cv = rotate(tuck, 360 * i / n, cx, cy)
        cv.outline(PALETTE["outline"])
        frames.append(cv)
    return frames


# ---------------------------------------------------------------- attacks
# Attack frames are bigger (the katana and slash reach past the body).
# The 16x16 body is placed so its feet stay bottom-centred, matching the other
# animations when aligned by midbottom in game.
ATTACK_W, ATTACK_H = 32, 24
BODY_OX, BODY_OY = 8, 8
BLADE = (228, 234, 244, 255)
SLASH = [(255, 255, 255, 255), (255, 240, 196, 255), (255, 204, 104, 255)]  # edge -> inner


def draw_katana(cv, hx, hy, angle_deg, length=10):
    """Katana held at (hx, hy); angle 0 = forward, -90 = up, 90 = down.
    A short length (e.g. 4) makes a dagger: shorter handle, tiny guard."""
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    dagger = length < 6
    t = -1.0 if dagger else -2.0
    while t <= length:
        if t < 0:
            color = PALETTE["hilt"]
        elif t < (0.5 if dagger else 1.5):
            color = PALETTE["guard"]
        else:
            color = BLADE
        cv.set(hx + dx * t, hy + dy * t, color)
        t += 0.5


def draw_slash(cv, cx, cy, radius, a0, a1, thick):
    """Crescent slash trail between angles a0..a1, tapered at both ends."""
    lo, hi = sorted((a0, a1))
    steps = max(2, int((hi - lo) / 2))
    for i in range(steps + 1):
        t = i / steps
        ang = math.radians(lo + (hi - lo) * t)
        n = max(1, round(thick * math.sin(math.pi * t) + 0.3))
        for k in range(n):
            r = radius - k
            cv.set(cx + r * math.cos(ang), cy + r * math.sin(ang), SLASH[min(k, 2)])


def attack_frame(pose, sword_angle, slash=None, phase=0.0, blade_length=10):
    pose = dict(pose, sword_on_back=False)
    pose.setdefault("back_foot", (-2, 0))
    pose.setdefault("front_foot", (2, 0))
    pose.setdefault("back_bend", 0)
    pose.setdefault("front_bend", 0)
    pose.setdefault("back_hand", (0, 2))
    pose.setdefault("tail", tail_points(3, phase, 1.0))
    pose.setdefault("tail2", [(dx, dy + 1) for dx, dy in tail_points(2, phase + 1.7, 1.0)])
    body = draw_ninja(pose, outline=False)

    cv = SizedCanvas(ATTACK_W, ATTACK_H)
    for y in range(SIZE):
        for x in range(SIZE):
            if body.px[y][x] is not None:
                cv.set(x + BODY_OX, y + BODY_OY, body.px[y][x])

    # front shoulder / hand, in attack-canvas coordinates (see draw_ninja)
    sx = BODY_OX + 6 + pose["lean"] + 2
    sy = BODY_OY + 8 + pose["bob"]
    fhx, fhy = pose["front_hand"]
    draw_katana(cv, sx + fhx, sy + fhy, sword_angle, blade_length)
    cv.set(sx + fhx, sy + fhy, PALETTE["skin"])     # hand gripping the hilt
    cv.outline(PALETTE["outline"])
    if slash:                                       # effect drawn on top, no outline
        draw_slash(cv, sx, sy, *slash)
    return cv


# Each step: (pose overrides, sword angle, slash (radius, from, to, thickness) or None)
ATTACKS = {
    # 1: horizontal forward cut, high -> mid
    "attack1": [
        ({"bob": 0, "lean": 0, "front_hand": (-1, -2)}, -150, None),
        ({"bob": 0, "lean": 0, "front_hand": (1, -2)}, -70, (11, -150, -70, 1)),
        ({"bob": 0, "lean": 1, "front_hand": (3, 0)}, 10, (11, -125, 20, 3)),
        ({"bob": 0, "lean": 1, "front_hand": (3, 1)}, 40, (11, -40, 40, 2)),
        ({"bob": 0, "lean": 1, "front_hand": (2, 1)}, 60, None),
        ({"bob": 0, "lean": 0, "front_hand": (1, 2)}, 80, None),
    ],
    # 2: rising cut, low -> high
    "attack2": [
        ({"bob": 1, "lean": 0, "front_hand": (-1, 2)}, 150, None),
        ({"bob": 1, "lean": 0, "front_hand": (1, 2)}, 100, (11, 100, 150, 1)),
        ({"bob": 0, "lean": 1, "front_hand": (3, -1)}, -40, (11, -70, 75, 3)),
        ({"bob": 0, "lean": 1, "front_hand": (2, -3)}, -80, (11, -95, -25, 2)),
        ({"bob": 0, "lean": 0, "front_hand": (1, -3)}, -100, None),
        ({"bob": 0, "lean": 0, "front_hand": (1, -1)}, -60, None),
    ],
    # 3: heavy overhead cut, straight down in front
    "attack3": [
        ({"bob": 0, "lean": 0, "front_hand": (0, -3), "back_foot": (-3, 0)}, -100, None),
        ({"bob": 0, "lean": 0, "front_hand": (-1, -3), "back_foot": (-3, 0)}, -125, None),
        ({"bob": 1, "lean": 1, "front_hand": (3, 1), "back_foot": (-3, 0), "front_foot": (3, 0)},
         45, (11, -105, 70, 3)),
        ({"bob": 1, "lean": 1, "front_hand": (3, 2), "back_foot": (-3, 0), "front_foot": (3, 0)},
         70, (11, 15, 85, 2)),
        ({"bob": 1, "lean": 1, "front_hand": (2, 2), "back_foot": (-3, 0), "front_foot": (3, 0)},
         75, None),
        ({"bob": 0, "lean": 0, "front_hand": (1, 2)}, 60, None),
    ],
}


# 4: dash attack (iaido style): crouch, rush with the blade trailing behind,
#    then a flat finishing cut. Tails stream straight back while dashing.
_DASH_TAIL = [(0, 0), (-1, 0), (-2, 0), (-3, 1)]
_DASH_TAIL2 = [(0, 1), (-1, 1), (-2, 2)]
ATTACKS["dash"] = [
    ({"bob": 1, "lean": 1, "front_hand": (-1, 1), "back_foot": (-3, 0), "front_foot": (3, 0)},
     160, None),
    ({"bob": 1, "lean": 1, "front_hand": (-2, 1), "back_foot": (-4, 1), "front_foot": (3, 0),
      "back_bend": 1, "tail": _DASH_TAIL, "tail2": _DASH_TAIL2}, 175, None),
    ({"bob": 1, "lean": 1, "front_hand": (-2, 1), "back_foot": (-4, 2), "front_foot": (3, 0),
      "back_bend": 1, "tail": [(dx, dy - (dx < -1)) for dx, dy in _DASH_TAIL],
      "tail2": _DASH_TAIL2}, 175, None),
    ({"bob": 0, "lean": 1, "front_hand": (3, 0), "back_foot": (-2, 0), "front_foot": (2, 0)},
     5, (11, -30, 25, 2)),
]


def attack_frames(name):
    steps = ATTACKS[name]
    return [attack_frame(pose, angle, slash, phase=2 * math.pi * i / len(steps))
            for i, (pose, angle, slash) in enumerate(steps)]


# ---------------------------------------------------------------- death
# 32x16 frames (lying down he's wider than tall); the 16x16 body sits at x 8..23
# so his feet stay bottom-centred like every other animation.
DEATH_W, DEATH_OX = 32, 8
BLOOD = (150, 18, 24, 255)
BLOOD_HI = (206, 40, 40, 255)


def rotate_sized(cv, degrees, cx, cy):
    """Nearest-neighbour rotation (clockwise on screen) of a SizedCanvas."""
    out = SizedCanvas(cv.w, cv.h)
    t = math.radians(degrees)
    c, s = math.cos(t), math.sin(t)
    for y in range(cv.h):
        for x in range(cv.w):
            dx, dy = x - cx, y - cy
            ix = round(cx + dx * c + dy * s)
            iy = round(cy - dx * s + dy * c)
            if 0 <= ix < cv.w and 0 <= iy < cv.h:
                out.px[y][x] = cv.px[iy][ix]
    return out


def death_body(pose, wound=True, pad=0):
    """The ninja (no outline) on a 32x16 canvas, with a bleeding chest wound.
    `pad` adds empty rows above and below (room to rotate without clipping)."""
    body = draw_ninja(pose, outline=False)
    cv = SizedCanvas(DEATH_W, SIZE + 2 * pad)
    for y in range(SIZE):
        for x in range(SIZE):
            if body.px[y][x] is not None:
                cv.set(x + DEATH_OX, y + pad, body.px[y][x])
    if wound:
        tx, ty = DEATH_OX + 6 + pose["lean"], pad + 7 + pose["bob"]   # torso top-left
        cv.set(tx + 2, ty + 1, BLOOD_HI)
        cv.set(tx + 3, ty + 1, BLOOD)
        cv.set(tx + 2, ty + 2, BLOOD)
    return cv


def death_frames():
    """Hit -> clutches the wound and staggers -> drops to his knees -> falls
    face-down, slowly. Played once; the last frame is held."""
    limp_tail = [(0, 1), (-1, 2), (-2, 3)]
    limp_tail2 = [(0, 2), (-1, 3)]
    stand = {"back_foot": (-1, 0), "front_foot": (1, 0), "back_bend": 0, "front_bend": 0,
             "tail": limp_tail, "tail2": limp_tail2}
    poses = [
        # staggers back, hand pressed to the wound
        dict(stand, bob=0, lean=-1, back_foot=(-2, 0), back_hand=(-1, 2), front_hand=(1, 0)),
        dict(stand, bob=1, lean=-1, back_foot=(-2, 0), back_hand=(-1, 3), front_hand=(0, 1)),
        # knees buckle
        dict(stand, bob=2, lean=0, back_foot=(-2, 0), front_foot=(2, 0), back_bend=2,
             front_bend=2, back_hand=(0, 3), front_hand=(1, 1)),
        # on his knees, head hanging, a hand reaching for the ground
        dict(stand, bob=3, lean=1, back_foot=(-3, 0), front_foot=(2, 0), back_bend=3,
             front_bend=3, back_hand=(0, 3), front_hand=(2, 3)),
    ]
    frames = []
    for pose in poses:
        cv = death_body(pose)
        cv.outline(PALETTE["outline"])
        frames.append(cv)

    # topple forward from the knees: rotate the kneeling body around his knees
    # first tipping forward from the knees, then (legs sliding back) flat on his face
    pad = SIZE
    kneel = death_body(poses[-1], pad=pad)
    flat = death_body(dict(stand, bob=0, lean=0, back_foot=(-1, 0), front_foot=(0, 0),
                           back_hand=(1, 2), front_hand=(2, 1)), pad=pad)
    steps = [(kneel, (DEATH_OX + 9, pad + SIZE - 1), a) for a in (18, 40)]
    steps += [(flat, (DEATH_OX + 6, pad + SIZE - 1), a) for a in (66, 84, 90)]
    for src, pivot, angle in steps:
        big = rotate_sized(src, angle, *pivot)
        # rest on the floor: crop to 32x16 with the lowest filled row on the bottom edge
        bottom = max(y for y in range(big.h) for x in range(big.w) if big.px[y][x] is not None)
        cv = SizedCanvas(DEATH_W, SIZE)
        for y in range(big.h):
            for x in range(big.w):
                if big.px[y][x] is not None:
                    cv.set(x, y - bottom + SIZE - 1, big.px[y][x])
        cv.outline(PALETTE["outline"])
        frames.append(cv)
    return frames


def bow_frames():
    """The ninja shooting a bow: the archer's draw-and-release frames with the
    ninja's body and palette (imported lazily - the archer tool imports this module)."""
    import generate_archer_sprites as archer
    return archer.shoot_frames(tails=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "player"))
    ap.add_argument("--preview", help="write a scaled preview sheet to this path")
    ap.add_argument("--scale", type=int, default=8)
    ap.add_argument("--only", nargs="*", help="only write these animations (e.g. --only death)")
    args = ap.parse_args()

    anims = {
        "idle": idle_frames(6),
        "walk": gait_frames(16, amp=2, lift=1, bend=1, arm_amp=2, lean=0,
                            tail_len=3, tail_amp=1.0, run=False),
        "run": gait_frames(16, amp=3.5, lift=2, bend=2, arm_amp=2, lean=1,
                           tail_len=4, tail_amp=1.0, run=True),
        "jump": air_frames("jump"),
        "fall": air_frames("fall"),
        "flip": flip_frames(8),
        "attack1": attack_frames("attack1"),
        "attack2": attack_frames("attack2"),
        "attack3": attack_frames("attack3"),
        "dash": attack_frames("dash"),
        "death": death_frames(),
        "bow": bow_frames(),
    }
    if args.only:
        anims = {k: v for k, v in anims.items() if k in args.only}

    for name, frames in anims.items():
        for i, cv in enumerate(frames):
            path = os.path.join(args.out, name, f"{name}_{i:02d}.png")
            write_png(path, cv.rgba_rows(), cv.w, cv.h)
        print(f"{name}: {len(frames)} frames ({frames[0].w}x{frames[0].h}) -> {os.path.join(args.out, name)}")

    if args.preview:
        preview_sheet(args.preview, list(anims.values()), scale=args.scale)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
