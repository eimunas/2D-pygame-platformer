"""Short-lived visual effects. They remove themselves when finished.

    Afterimage(game, player.image, player.rect.topleft)      # ghost silhouette
    SlashStreak(game, x0, x1, y)                               # sword flash line
    DeathFade(game, enemy.image, enemy.rect.topleft)           # defeated enemy
"""

from __future__ import annotations

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
