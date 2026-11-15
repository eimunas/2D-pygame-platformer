"""Tile grid with automatic edge selection (4-bit autotiling) and one-way
platforms.

You only say *what* goes in a cell; the tilemap picks the right image:

    tilemap = Tilemap(game, cols=30, rows=9)
    tilemap.set_tile(3, 7, "grass")
    tilemap.fill_rect(0, 8, 30, 1, "dirt")
    tilemap.set_tile(10, 7, "bridge")       # one-way platform
    tilemap.remove_tile(3, 7)
    tilemap.draw(screen)

Tile types:
    grass, dirt          solid blocks, autotiled by their 4 neighbours
    bridge               one-way platform: stand on it, jump up through it

Mask bits (set = that side is exposed / neighbour is empty):
    N = 1, E = 2, S = 4, W = 8
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pygame

from src import settings

if TYPE_CHECKING:
    from src.game import Game

N, E, S, W = 1, 2, 4, 8
NEIGHBOURS = ((0, -1, N), (1, 0, E), (0, 1, S), (-1, 0, W))

SOLID = {"grass", "dirt"}                  # block movement from every side
PLATFORMS = {"bridge"}                     # only solid when landing from above


def load_scaled(path, scale):
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.scale_by(img, scale)


class Tileset:
    """All 16 autotile images (with variants) for one tile kind, e.g. 'grass'."""

    def __init__(self, kind, scale):
        folder = os.path.join(settings.ASSETS_DIR, "tiles", kind)
        self.kind = kind
        self.images = {mask: [] for mask in range(16)}
        for name in sorted(os.listdir(folder)):
            if not name.lower().endswith(".png"):
                continue
            _, mask, _variant = os.path.splitext(name)[0].rsplit("_", 2)  # grass_05_1
            self.images[int(mask)].append(load_scaled(os.path.join(folder, name), scale))
        missing = [m for m, imgs in self.images.items() if not imgs]
        if missing:
            raise FileNotFoundError(f"Tileset '{kind}' is missing masks {missing} in {folder}")

    def get(self, mask, col, row):
        variants = self.images[mask]
        # deterministic "random" variant per cell, so the map doesn't flicker
        return variants[(col * 73856093 ^ row * 19349663) % len(variants)]


class Tilemap:
    KINDS = ("grass", "dirt", "bridge")

    def __init__(self, game: Game, cols, rows, tile_size=settings.TILE_SIZE, edges_solid=True):
        """edges_solid: treat cells outside the map as solid, so the ground
        continues past the map border instead of showing an edge there."""
        self.game = game
        self.cols, self.rows = cols, rows
        self.tile_size = tile_size
        self.edges_solid = edges_solid
        self.grid = [[None] * cols for _ in range(rows)]
        self._image_cache = {}

        scale = settings.SCALE
        tiles_dir = os.path.join(settings.ASSETS_DIR, "tiles")
        self.tilesets = {kind: Tileset(kind, scale) for kind in ("grass", "dirt")}
        # bridge images are 2 tiles tall: rails above, deck at the tile's top
        self.bridge_images = {
            piece: load_scaled(os.path.join(tiles_dir, "bridge", f"bridge_{piece}.png"), scale)
            for piece in ("left", "mid", "right", "single")
        }
        self.platform_thickness = 4 * scale       # deck height used for collisions

    # ------------------------------------------------------------ size
    @property
    def width(self):
        return self.cols * self.tile_size

    @property
    def height(self):
        return self.rows * self.tile_size

    def in_bounds(self, col, row):
        return 0 <= col < self.cols and 0 <= row < self.rows

    # ------------------------------------------------------------ editing
    def get_tile(self, col, row):
        return self.grid[row][col] if self.in_bounds(col, row) else None

    def set_tile(self, col, row, kind):
        if not self.in_bounds(col, row):
            raise IndexError(f"Tile ({col}, {row}) is outside the {self.cols}x{self.rows} map")
        if kind is not None and kind not in self.KINDS:
            raise ValueError(f"Unknown tile kind '{kind}', expected one of {self.KINDS}")
        self.grid[row][col] = kind
        # this cell and its neighbours may need different edge images now
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                self._image_cache.pop((col + dc, row + dr), None)

    def remove_tile(self, col, row):
        self.set_tile(col, row, None)

    def fill_rect(self, col, row, w, h, kind):
        for r in range(row, row + h):
            for c in range(col, col + w):
                self.set_tile(c, r, kind)

    # ------------------------------------------------------------ queries
    def is_solid(self, col, row):
        """Blocks movement from all sides (grass/dirt). Bridges don't count,
        so ground next to a bridge still shows its edge."""
        if not self.in_bounds(col, row):
            return self.edges_solid
        return self.grid[row][col] in SOLID

    def get_mask(self, col, row):
        mask = 0
        for dc, dr, bit in NEIGHBOURS:
            if not self.is_solid(col + dc, row + dr):
                mask |= bit
        return mask

    def grid_to_world(self, col, row):
        """Top-left pixel of a cell."""
        return col * self.tile_size, row * self.tile_size

    def world_to_grid(self, x, y):
        return int(x // self.tile_size), int(y // self.tile_size)

    def tile_rect(self, col, row):
        x, y = self.grid_to_world(col, row)
        return pygame.Rect(x, y, self.tile_size, self.tile_size)

    def _cells_overlapping(self, rect):
        c0, r0 = self.world_to_grid(rect.left, rect.top)
        c1, r1 = self.world_to_grid(rect.right - 1, rect.bottom - 1)
        for r in range(max(r0, 0), min(r1, self.rows - 1) + 1):
            for c in range(max(c0, 0), min(c1, self.cols - 1) + 1):
                yield c, r

    def solid_rects_near(self, rect):
        """Rects of solid tiles overlapping `rect` (walls, floors, ceilings)."""
        return [self.tile_rect(c, r) for c, r in self._cells_overlapping(rect)
                if self.grid[r][c] in SOLID]

    def platform_rects_near(self, rect):
        """Deck rects of one-way platforms overlapping `rect`."""
        out = []
        for c, r in self._cells_overlapping(rect):
            if self.grid[r][c] in PLATFORMS:
                deck = self.tile_rect(c, r)
                deck.height = self.platform_thickness
                out.append(deck)
        return out

    # ------------------------------------------------------------ drawing
    def get_image(self, col, row):
        """(image, y_offset) for a cell."""
        key = (col, row)
        cached = self._image_cache.get(key)
        if cached is None:
            kind = self.grid[row][col]
            if kind == "bridge":
                left = self.get_tile(col - 1, row) == "bridge"
                right = self.get_tile(col + 1, row) == "bridge"
                piece = "mid" if left and right else "right" if left else "left" if right else "single"
                cached = (self.bridge_images[piece], -self.tile_size)
            else:
                cached = (self.tilesets[kind].get(self.get_mask(col, row), col, row), 0)
            self._image_cache[key] = cached
        return cached

    def draw(self, surface, offset=(0, 0)):
        """Draw only the tiles visible on `surface`. offset = camera position."""
        ox, oy = offset
        ts = self.tile_size
        c0 = max(0, int(ox // ts))
        r0 = max(0, int(oy // ts))
        c1 = min(self.cols, int((ox + surface.get_width()) // ts) + 1)
        # +1 row: bridge images reach one tile above their cell
        r1 = min(self.rows, int((oy + surface.get_height()) // ts) + 2)
        for row in range(r0, r1):
            for col in range(c0, c1):
                if self.grid[row][col] is not None:
                    img, dy = self.get_image(col, row)
                    surface.blit(img, (col * ts - ox, row * ts - oy + dy))
