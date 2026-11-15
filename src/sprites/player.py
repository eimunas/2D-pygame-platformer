"""The player-controlled ninja."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames

if TYPE_CHECKING:  # only for type hints, avoids a circular import
    from src.game import Game


class Player(pygame.sprite.Sprite):
    def __init__(self, game: Game, pos):
        super().__init__(game.all_sprites)
        self.game = game

        player_dir = os.path.join(settings.ASSETS_DIR, "player")
        self.animations = {
            name: Animation(load_frames(os.path.join(player_dir, name), settings.SCALE), fps)
            for name, fps in settings.PLAYER_ANIM_FPS.items()
        }
        self.state = "idle"
        self.facing_right = True

        # pos is the player's feet (midbottom), kept as floats for smooth movement
        self.pos = pygame.Vector2(pos)
        self.image = self.animations[self.state].image
        self.rect = self.image.get_rect(midbottom=self.pos)

    @property
    def animation(self) -> Animation:
        return self.animations[self.state]

    # ------------------------------------------------------------ input
    def get_direction(self):
        keys = self.game.keys
        direction = 0
        if keys[pygame.K_a]:
            direction -= 1
        if keys[pygame.K_d]:
            direction += 1
        return direction

    def set_state(self, new_state):
        if new_state != self.state:
            self.state = new_state
            self.animation.reset()

    # ------------------------------------------------------------ update
    def update(self):
        dt = self.game.dt
        keys = self.game.keys
        direction = self.get_direction()
        running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if direction == 0:
            self.set_state("idle")
        elif running:
            self.set_state("run")
        else:
            self.set_state("walk")

        if direction != 0:
            self.facing_right = direction > 0

        speed = settings.RUN_SPEED if self.state == "run" else settings.WALK_SPEED
        self.pos.x += direction * speed * dt

        half_w = self.rect.width / 2
        self.pos.x = max(half_w, min(settings.SCREEN_W - half_w, self.pos.x))

        self.animation.update(dt)
        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        self.rect = self.image.get_rect(midbottom=(round(self.pos.x), round(self.pos.y)))
