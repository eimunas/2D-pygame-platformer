"""Parallax background.

A layer scrolls slower than the world: factor 0 = fixed to the screen (very far
away), 1 = moves with the tiles. Several layers with different factors give
depth, e.g. sky 0.05, mountains 0.2, trees 0.5.

    background = ParallaxBackground(screen.get_size())
    background.add_layer("assets/background/sky.png", factor=(0, 0))       # farthest first
    background.add_layer("assets/background/forest_near.png", factor=(0.65, 0.6))
    background.draw(screen, camera.pos)
"""

import math

import pygame


class ParallaxLayer:
    def __init__(self, path, screen_size, factor=(0.25, 0.5), v_margin=32, mirror_tiles=False):
        """
        factor       - (x, y) scroll speed relative to the camera
        v_margin     - extra height (px) so the layer can move vertically
                       without showing an empty strip
        mirror_tiles - flip every other horizontal copy; use for images whose
                       left and right edges don't match up
        """
        sw, sh = screen_size
        img = pygame.image.load(path).convert_alpha()   # keeps transparency of PNG layers
        iw, ih = img.get_size()
        scale = max(sw / iw, (sh + v_margin) / ih)   # cover the screen, keep aspect ratio
        if abs(scale - round(scale)) < 1e-6:
            # whole-number scale: nearest-neighbour keeps pixel art crisp
            self.image = pygame.transform.scale_by(img, round(scale))
        else:
            # fractional scale: nearest-neighbour would make uneven pixels and
            # shimmering dither patterns, so smooth it instead
            size = (math.ceil(iw * scale), math.ceil(ih * scale))
            self.image = pygame.transform.smoothscale(img, size)
        self.flipped = pygame.transform.flip(self.image, True, False)
        self.factor = pygame.Vector2(factor)
        self.mirror_tiles = mirror_tiles
        self.screen_h = sh

    def draw(self, surface, camera_pos):
        w, h = self.image.get_size()
        ox = camera_pos[0] * self.factor.x
        oy = camera_pos[1] * self.factor.y
        # vertical: move, but never leave a gap at the top or bottom
        y = round(max(self.screen_h - h, min(0, -oy)))

        index = math.floor(ox / w)
        x = index * w - ox
        while x < surface.get_width():
            img = self.flipped if (self.mirror_tiles and index % 2) else self.image
            surface.blit(img, (round(x), y))
            index += 1
            x += w


class ParallaxBackground:
    def __init__(self, screen_size, fill=(120, 170, 210)):
        self.screen_size = screen_size
        self.fill = fill
        self.layers = []

    def add_layer(self, path, **kwargs):
        """Add layers from farthest to nearest."""
        layer = ParallaxLayer(path, self.screen_size, **kwargs)
        self.layers.append(layer)
        return layer

    def draw(self, surface, camera_pos):
        if not self.layers:
            surface.fill(self.fill)
        for layer in self.layers:
            layer.draw(surface, camera_pos)
