"""Short-lived visual effects. They remove themselves when finished.

    Afterimage(game, player.image, player.rect.topleft)      # ghost silhouette
    SlashStreak(game, x0, x1, y)                               # sword flash line
    DeathFade(game, enemy.image, enemy.rect.topleft)           # defeated enemy
    blood_spray(game, pos, direction)                          # droplets that splat
    BloodPool(game, center_x, ground_y)                        # spreading pool
    FloatingText(game, "+1 coin", midbottom)                   # rising label
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pygame

from src import settings

if TYPE_CHECKING:
    from src.game import Game


class Effect(pygame.sprite.Sprite):
    """Base: fades from `start_alpha` to 0 over `lifetime` seconds, then dies."""

    def __init__(self, game: Game, layer_group, lifetime, start_alpha=255):
        super().__init__(game.all_sprites, layer_group)
        self.game = game
        self.lifetime = lifetime
        self.start_alpha = start_alpha
        self.age = 0.0

    @property
    def progress(self):
        """0 at spawn -> 1 at the end of its life."""
        return min(1.0, self.age / self.lifetime)

    def update(self):
        self.age += self.game.dt
        if self.age >= self.lifetime:
            self.kill()
            return
        self.animate()
        self.image.set_alpha(round(self.start_alpha * (1 - self.progress)))

    def animate(self):
        """Override for effects that change shape over time."""


class Afterimage(Effect):
    """A flat-coloured silhouette of a sprite frame, left behind while dashing."""

    def __init__(self, game: Game, image, topleft,
                 color=settings.GHOST_COLOR, lifetime=settings.GHOST_LIFETIME,
                 start_alpha=settings.GHOST_ALPHA):
        super().__init__(game, game.effects_back, lifetime, start_alpha)
        mask = pygame.mask.from_surface(image)
        self.image = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0)).convert_alpha()
        self.rect = self.image.get_rect(topleft=topleft)


class DeathFade(Effect):
    """A defeated enemy: white silhouette that drifts up and fades out."""

    def __init__(self, game: Game, image, topleft, lifetime=0.45):
        super().__init__(game, game.effects_front, lifetime, start_alpha=230)
        mask = pygame.mask.from_surface(image)
        self.image = mask.to_surface(setcolor=(255, 250, 240), unsetcolor=(0, 0, 0, 0)).convert_alpha()
        self.rect = self.image.get_rect(topleft=topleft)
        self.y = float(self.rect.y)

    def animate(self):
        self.y -= 60 * self.game.dt
        self.rect.y = round(self.y)


class SlashStreak(Effect):
    """Bright horizontal line along a dash path: white core, gold glow; thins out."""

    CORE = (255, 255, 255)
    GLOW = (255, 214, 120)

    def __init__(self, game: Game, x0, x1, y, lifetime=settings.STREAK_LIFETIME):
        super().__init__(game, game.effects_front, lifetime)
        self.left = min(x0, x1)
        self.width = max(1, abs(x1 - x0))
        self.y = y
        self.px = settings.SCALE            # one art pixel on screen
        self.redraw(thickness=3)

    def redraw(self, thickness):
        h = thickness * self.px
        self.image = pygame.Surface((self.width, h), pygame.SRCALPHA)
        if thickness >= 3:
            self.image.fill(self.GLOW)
            pygame.draw.rect(self.image, self.CORE, (0, self.px, self.width, self.px))
        else:
            self.image.fill(self.CORE)
        # tapered ends: shave one art-pixel step off each end per row away from centre
        for row in range(thickness):
            cut = abs(row - (thickness - 1) / 2) * 3 * self.px
            if cut:
                y = row * self.px
                pygame.draw.rect(self.image, (0, 0, 0, 0), (0, y, cut, self.px))
                pygame.draw.rect(self.image, (0, 0, 0, 0), (self.width - cut, y, cut, self.px))
        self.rect = self.image.get_rect(midleft=(self.left, self.y))

    def animate(self):
        thickness = 3 if self.progress < 0.45 else 1     # glow fades first, core lingers
        if self.image.get_height() != thickness * self.px:
            self.redraw(thickness)


class BloodDrop(pygame.sprite.Sprite):
    """One droplet: flies with gravity, splats where it hits the ground,
    stays there a while and then fades."""

    def __init__(self, game: Game, pos, vel, lifetime=6.0):
        super().__init__(game.all_sprites, game.effects_front)
        self.game = game
        size = settings.SCALE
        color = random.choice((settings.BLOOD_COLOR, settings.BLOOD_COLOR, settings.BLOOD_COLOR_HI))
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        self.image.fill(color)
        self.color = color
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        self.landed = False
        self.age = 0.0
        self.lifetime = lifetime

    def update(self):
        dt = self.game.dt
        self.age += dt
        if self.age >= self.lifetime:
            self.kill()
            return
        if not self.landed:
            self.vel.y = min(self.vel.y + settings.GRAVITY * 0.7 * dt, 900)
            self.pos += self.vel * dt
            tm = self.game.tilemap
            col, row = tm.world_to_grid(self.pos.x, self.pos.y)
            if tm.is_solid(col, row):
                self.landed = True                        # splat flat on the tile top
                self.pos.y = row * tm.tile_size
                splat = pygame.Surface((settings.SCALE * 2, settings.SCALE), pygame.SRCALPHA)
                splat.fill(self.color)
                self.image = splat
            elif self.pos.y > tm.rows * tm.tile_size:
                self.kill()
                return
        if self.landed:
            self.rect = self.image.get_rect(midbottom=(round(self.pos.x), round(self.pos.y) + settings.SCALE))
        else:
            self.rect.center = (round(self.pos.x), round(self.pos.y))
        fade_from = self.lifetime * 0.75
        if self.age > fade_from:
            self.image.set_alpha(round(255 * (1 - (self.age - fade_from) / (self.lifetime - fade_from))))


def blood_spray(game: Game, pos, direction, count=None):
    """Burst of droplets from a wound; `direction` +1 / -1 = mostly to the right / left."""
    for _ in range(settings.BLOOD_SPRAY if count is None else count):
        vx = direction * random.uniform(60, 320) + random.uniform(-40, 40)
        vy = -random.uniform(120, 460)
        BloodDrop(game, pos, (vx, vy))


class BloodPool(pygame.sprite.Sprite):
    """A pool of blood spreading on the ground under a body (pixel-art steps)."""

    def __init__(self, game: Game, center_x, ground_y):
        super().__init__(game.all_sprites, game.effects_back)
        self.game = game
        self.center_x = center_x
        self.ground_y = ground_y
        self.age = 0.0
        self.width = -1
        self.redraw(1)

    def redraw(self, width):
        """width in art pixels; two rows: a full lower row and a shorter top row."""
        if width == self.width:
            return
        self.width = width
        px = settings.SCALE
        w = max(1, width)
        self.image = pygame.Surface((w * px, 2 * px), pygame.SRCALPHA)
        top = max(1, w - 4)
        self.image.fill(settings.BLOOD_COLOR, ((w - top) * px // 2, 0, top * px, px))
        self.image.fill(settings.BLOOD_COLOR, (0, px, w * px, px))
        if w >= 5:                                       # a glossy highlight
            self.image.fill(settings.BLOOD_COLOR_HI, ((w // 2 - 1) * px, 0, 2 * px, px))
        # bottom row overlaps the top of the ground tile a little, like it soaked in
        self.rect = self.image.get_rect(midbottom=(self.center_x, self.ground_y + px))

    def update(self):
        self.age += self.game.dt
        t = min(1.0, self.age / settings.BLOOD_POOL_TIME)
        ease = 1 - (1 - t) ** 2                          # spreads fast, then slows
        self.redraw(1 + round((settings.BLOOD_POOL_WIDTH - 1) * ease))


class FloatingText(Effect):
    """Small text that rises and fades, e.g. "+1 coin"."""

    def __init__(self, game: Game, text, midbottom, color=(250, 244, 232), lifetime=1.0):
        super().__init__(game, game.effects_front, lifetime)
        label = game.font.render(text, True, color)
        shadow = game.font.render(text, True, (14, 12, 22))
        self.image = pygame.Surface((label.get_width() + 2, label.get_height() + 2), pygame.SRCALPHA)
        self.image.blit(shadow, (2, 2))
        self.image.blit(label, (0, 0))
        self.rect = self.image.get_rect(midbottom=midbottom)
        self.y = float(self.rect.y)

    def animate(self):
        self.y -= 45 * self.game.dt
        self.rect.y = round(self.y)
