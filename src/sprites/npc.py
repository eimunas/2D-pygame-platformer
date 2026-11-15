"""Friendly characters.

    Trader(game, feet)   # wandering merchant: stands still, turns to face the
                         # ninja; when he's close, a key prompt shows and E opens the shop
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames

if TYPE_CHECKING:
    from src.game import Game

TRADER_DIR = os.path.join(settings.ASSETS_DIR, "npcs", "trader")


class Trader(pygame.sprite.Sprite):
    NAME = "Wandering Trader"

    def __init__(self, game: Game, feet):
        super().__init__(game.all_sprites, game.background_decor, game.npcs)
        self.game = game
        self.animation = Animation(load_frames(os.path.join(TRADER_DIR, "idle"), settings.SCALE), 5)
        self.feet = feet
        self.facing_right = False
        self.near = False                      # ninja close enough to talk
        self.image = self.animation.image
        self.rect = self.image.get_rect(midbottom=feet)

    def player_in_range(self):
        p = self.game.player
        rx, ry = settings.TRADER_TALK_RANGE
        return (not p.dead and abs(p.hitbox.centerx - self.rect.centerx) <= rx
                and abs(p.hitbox.bottom - self.rect.bottom) <= ry)

    def update(self):
        self.animation.update(self.game.dt)
        p = self.game.player
        if abs(p.hitbox.centerx - self.rect.centerx) > 6:
            self.facing_right = p.hitbox.centerx > self.rect.centerx
        self.near = self.player_in_range()
        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        self.rect = self.image.get_rect(midbottom=self.feet)
