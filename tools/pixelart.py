"""Tiny stdlib-only pixel-art toolkit: a canvas with drawing helpers + PNG writer."""

import os
import struct
import zlib


def rgb(r, g, b, a=255):
    return (r, g, b, a)


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    # ------------------------------------------------------------ pixels
    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def set(self, x, y, color):
        x, y = int(round(x)), int(round(y))
        if self.inside(x, y):
            self.px[y][x] = color

    def get(self, x, y):
        return self.px[y][x] if self.inside(x, y) else None

    def copy(self):
        c = Canvas(self.w, self.h)
        c.px = [row[:] for row in self.px]
        return c

    # ------------------------------------------------------------ shapes
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

    def ellipse(self, cx, cy, rx, ry, color_fn):
        """Fill an ellipse. color_fn(x, y, nx, ny) -> color, where nx/ny in [-1, 1]."""
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                nx = (x - cx) / rx
                ny = (y - cy) / ry
                if nx * nx + ny * ny <= 1.0:
                    c = color_fn(x, y, nx, ny)
                    if c is not None:
                        self.set(x, y, c)

    # ------------------------------------------------------------ effects
    def outline(self, color):
        """1px outline around all filled pixels (4-neighbourhood)."""
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None:
                    continue
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if self.inside(nx, ny) and self.px[ny][nx] is not None:
                        add.append((x, y))
                        break
        for x, y in add:
            self.px[y][x] = color

    def shear_rows(self, offset_fn):
        """Return a copy where row y is shifted horizontally by offset_fn(y)."""
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            off = offset_fn(y)
            for x in range(self.w):
                c = self.px[y][x]
                if c is not None:
                    out.set(x + off, y, c)
        return out

    # ------------------------------------------------------------ export
    def rgba_rows(self, scale=1):
        rows = []
        for y in range(self.h):
            row = bytearray()
            for x in range(self.w):
                row.extend(bytes(self.px[y][x] or (0, 0, 0, 0)) * scale)
            for _ in range(scale):
                rows.append(bytes(row))
        return rows

    def save(self, path):
        write_png(path, self.rgba_rows(), self.w, self.h)


def write_png(path, rows, width, height):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + r for r in rows)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)


def preview_sheet(path, rows_of_canvases, scale=6, bg=(200, 210, 200, 255), pad=4):
    """Write a scaled sheet; each inner list is one row of canvases."""
    cell_w = max(c.w for row in rows_of_canvases for c in row) * scale + pad
    row_hs = [max(c.h for c in row) * scale + pad for row in rows_of_canvases]
    cols = max(len(row) for row in rows_of_canvases)
    W, H = cols * cell_w, sum(row_hs)
    sheet = [bytearray(bytes(bg) * W) for _ in range(H)]
    y0 = 0
    for row, rh in zip(rows_of_canvases, row_hs):
        for ci, cv in enumerate(row):
            x0 = ci * cell_w + pad // 2
            oy = y0 + rh - pad // 2 - cv.h * scale  # bottom-align
            for y, line in enumerate(cv.rgba_rows(scale)):
                for x in range(cv.w * scale):
                    p = line[x * 4:x * 4 + 4]
                    if p[3]:
                        sheet[oy + y][(x0 + x) * 4:(x0 + x) * 4 + 4] = p
        y0 += rh
    write_png(path, [bytes(r) for r in sheet], W, H)
