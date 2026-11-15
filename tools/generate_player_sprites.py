"""Generate 16x16 pixel-art ninja player sprites.

Uses only the Python standard library (no pygame/Pillow needed).

Usage (from the repo root):
    python tools/generate_player_sprites.py              # writes assets/player/...
    python tools/generate_player_sprites.py --preview p.png   # also writes a scaled preview sheet

Output:
    assets/player/idle/idle_00.png .. idle_05.png   (6 frames)
    assets/player/walk/walk_00.png .. walk_15.png   (16 frames)
    assets/player/run/run_00.png   .. run_15.png    (16 frames)

The character faces RIGHT. Flip horizontally in-game for left.
"""

import argparse
import math
import os
import struct
import zlib

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
}


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self):
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
    cv.set(foot_x, foot_y, PALETTE["suit_sh"])
    cv.set(foot_x + 1, foot_y, PALETTE["suit_sh"])
    cv.set(foot_x + 2, foot_y, PALETTE["suit_sh"])


def draw_ninja(pose):
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

    # katana sheath (behind everything)
    cv.line(tx0 - 1, torso_y, tx0 + 3, torso_y + 3, P["sheath"])

    # back arm
    bhx, bhy = pose["back_hand"]
    cv.line(tx0 + 1, shoulder_y, tx0 + 1 + bhx, shoulder_y + bhy, P["suit_sh"])

    # back leg
    fx, lift = pose["back_foot"]
    draw_leg(cv, hip_x, hip_y, hip_x + fx, 14 - lift, pose["back_bend"], P["suit_sh"])

    # torso
    cv.rect(tx0, torso_y, tx0 + 3, torso_y + 3, P["suit"])
    cv.rect(tx0, torso_y + 3, tx0 + 3, torso_y + 3, P["red_dk"])  # sash

    # front leg
    fx, lift = pose["front_foot"]
    draw_leg(cv, hip_x, hip_y, hip_x + fx, 14 - lift, pose["front_bend"], P["suit"])

    # head / hood
    cv.rect(hx0, head_y, hx0 + 4, head_y + 4, P["suit"])
    cv.set(hx0 + 1, head_y, P["suit_hi"])
    cv.set(hx0 + 2, head_y, P["suit_hi"])
    # headband
    cv.rect(hx0, head_y + 1, hx0 + 4, head_y + 1, P["red"])
    # eye slit
    cv.rect(hx0 + 2, head_y + 2, hx0 + 4, head_y + 2, P["skin"])
    cv.set(hx0 + 3, head_y + 2, P["eye"])

    # katana hilt over the back shoulder
    cv.set(hx0 - 1, torso_y, P["guard"])
    cv.set(hx0 - 2, torso_y - 1, P["hilt"])
    cv.set(hx0 - 3, torso_y - 2, P["hilt"])

    # headband tails
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

    cv.outline(P["outline"])
    return cv


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
    frames = []
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

        frames.append(draw_ninja({
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
        }))
    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("assets", "player"))
    ap.add_argument("--preview", help="write a scaled preview sheet to this path")
    ap.add_argument("--scale", type=int, default=8)
    args = ap.parse_args()

    anims = {
        "idle": idle_frames(6),
        "walk": gait_frames(16, amp=2, lift=1, bend=1, arm_amp=2, lean=0,
                            tail_len=3, tail_amp=1.0, run=False),
        "run": gait_frames(16, amp=3.5, lift=2, bend=2, arm_amp=2, lean=1,
                           tail_len=4, tail_amp=1.0, run=True),
    }

    for name, frames in anims.items():
        for i, cv in enumerate(frames):
            path = os.path.join(args.out, name, f"{name}_{i:02d}.png")
            write_png(path, cv.rgba_rows(), SIZE, SIZE)
        print(f"{name}: {len(frames)} frames -> {os.path.join(args.out, name)}")

    if args.preview:
        s = args.scale
        cell = SIZE * s + 4
        cols = 16
        sheet_w = cols * cell
        sheet_h = len(anims) * cell
        bg = bytes((200, 210, 200, 255))
        sheet = [bytearray(bg * sheet_w) for _ in range(sheet_h)]
        for r, frames in enumerate(anims.values()):
            for col, cv in enumerate(frames):
                rows = cv.rgba_rows(scale=s)
                for y, row in enumerate(rows):
                    for x in range(SIZE * s):
                        px = row[x * 4:x * 4 + 4]
                        if px[3]:
                            sy = r * cell + 2 + y
                            sx = (col * cell + 2 + x) * 4
                            sheet[sy][sx:sx + 4] = px
        write_png(args.preview, [bytes(r) for r in sheet], sheet_w, sheet_h)
        print(f"preview -> {args.preview}")


if __name__ == "__main__":
    main()
