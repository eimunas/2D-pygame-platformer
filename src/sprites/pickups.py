"""Collectibles.

    Coin(game, center, coin_id)   # spins and bobs; touching it adds a coin to the
                                  # wallet (saved) - each coin_id can be found only once
"""

from __future__ import annotations

import math
import os
import random
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames
from src.sprites.effects import DeathFade, FloatingText

if TYPE_CHECKING:
    from src.game import Game

COIN_DIR = os.path.join(settings.ASSETS_DIR, "items", "coin")


class Coin(pygame.sprite.Sprite):
    def __init__(self, game: Game, center, coin_id):
        super().__init__(game.all_sprites, game.pickups)
        self.game = game
        self.coin_id = coin_id
        self.center = pygame.Vector2(center)
        self.animation = Animation(load_frames(COIN_DIR, settings.SCALE), settings.COIN_ANIM_FPS)
        self.phase = random.uniform(0, math.tau)       # coins don't all bob in sync
        self.image = self.animation.image
        self.rect = self.image.get_rect(center=center)
        # a smaller box than the image: you have to actually touch the coin
        self.hitbox = pygame.Rect(0, 0, 7 * settings.SCALE, 9 * settings.SCALE)

    def update(self):
        dt = self.game.dt
        self.phase += settings.COIN_BOB[1] * dt
        self.animation.update(dt)
        self.image = self.animation.image
        y = self.center.y + math.sin(self.phase) * settings.COIN_BOB[0]
        self.rect = self.image.get_rect(center=(round(self.center.x), round(y)))
        self.hitbox.center = self.rect.center

        player = self.game.player
        if not player.dead and self.hitbox.colliderect(player.hitbox):
            self.collect()

    def collect(self):
        self.game.progress.collect_coin(self.coin_id)
        self.game.audio.play("coin")                   # assets/audio/coin.* if you add one
        DeathFade(self.game, self.image, self.rect.topleft, lifetime=0.35)
        FloatingText(self.game, "+1 coin", self.rect.midtop, color=(255, 214, 110))
        self.kill()


def coin_spots(tilemap, spawn_x, exit_x=None):
    """Grid cells (col, row) where a coin can float: just above walkable ground
    (grass/dirt top or a bridge) with headroom, away from the start and the exit."""
    ts = tilemap.tile_size
    spawn_col = int(spawn_x // ts)
    exit_col = int(exit_x // ts) if exit_x is not None else None
    spots = []
    for col in range(tilemap.cols):
        if abs(col - spawn_col) < settings.COIN_SAFE_FROM_SPAWN:
            continue
        if exit_col is not None and abs(col - exit_col) < settings.COIN_SAFE_FROM_EXIT:
            continue
        for row in range(2, tilemap.rows):
            ground = tilemap.is_solid(col, row) or tilemap.get_tile(col, row) == "bridge"
            free = all(tilemap.get_tile(col, r) is None for r in (row - 1, row - 2))
            if ground and free:
                spots.append((col, row - 1))
    return spots
