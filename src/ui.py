"""Health bars.

    PlayerHealthBar  - segmented bar in the top-left corner (screen space), with a
                       "damage trail" showing recently lost health
    draw_enemy_bar() - small bar above an enemy's head (world space, uses the camera)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from src import settings

if TYPE_CHECKING:
    from src.game import Game


def draw_bar(surface, rect, value, maximum, trail=None, segments=False):
    """Pixel-style bar: dark frame, empty background, trail, fill with a highlight."""
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, settings.HEALTH_FRAME, rect)
    inner = rect.inflate(-4, -4) if rect.height > 8 else rect.inflate(-2, -2)
    pygame.draw.rect(surface, settings.HEALTH_EMPTY, inner)

    def part(amount):
        w = round(inner.width * max(0, min(amount, maximum)) / maximum)
        return pygame.Rect(inner.left, inner.top, w, inner.height)

    if trail is not None and trail > value:
        pygame.draw.rect(surface, settings.HEALTH_TRAIL, part(trail))
    fill = part(value)
    if fill.width:
        pygame.draw.rect(surface, settings.HEALTH_FILL, fill)
        hi = fill.copy()
        hi.height = max(1, inner.height // 3)
        pygame.draw.rect(surface, settings.HEALTH_FILL_HI, hi)
    if segments:
        for i in range(1, maximum):
            x = inner.left + round(inner.width * i / maximum)
            pygame.draw.line(surface, settings.HEALTH_FRAME, (x, inner.top), (x, inner.bottom - 1), 2)


class PlayerHealthBar:
    POS = (16, 16)
    SIZE = (220, 22)

    def __init__(self, game: Game):
        self.game = game
        self.trail = float(game.player.health)
        self.trail_delay = 0.0
        self.last_health = game.player.health

    def update(self, dt):
        health = self.game.player.health
        if health < self.last_health:              # just got hurt: hold the trail
            self.trail_delay = settings.HEALTH_TRAIL_DELAY
        elif health > self.last_health:            # healed / respawned
            self.trail = health
        self.last_health = health

        if self.trail_delay > 0:
            self.trail_delay -= dt
        else:
            self.trail = max(health, self.trail - settings.HEALTH_TRAIL_SPEED * dt)

    def draw(self, surface):
        p = self.game.player
        rect = pygame.Rect(self.POS, self.SIZE)
        draw_bar(surface, rect, p.health, p.max_health, trail=self.trail, segments=True)
        label = self.game.font.render(f"{p.health}/{p.max_health}", True, (250, 244, 232))
        shadow = self.game.font.render(f"{p.health}/{p.max_health}", True, settings.HEALTH_FRAME)
        x, y = rect.right + 10, rect.centery - label.get_height() // 2
        surface.blit(shadow, (x + 2, y + 2))
        surface.blit(label, (x, y))
        return rect


def draw_enemy_bar(surface, enemy, camera):
    """Small bar centred above the enemy's head."""
    w, h = settings.ENEMY_BAR_SIZE
    world = pygame.Rect(0, 0, w, h)
    world.midbottom = (enemy.hitbox.centerx, enemy.hitbox.top - 14)
    draw_bar(surface, camera.apply(world), enemy.health, enemy.max_health)
