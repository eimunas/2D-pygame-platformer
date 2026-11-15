"""Non-interactive scenery: rocks (foreground) and animated trees (background)."""

from __future__ import annotations

import os
import random
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames, load_image

if TYPE_CHECKING:
    from src.game import Game

DECOR_DIR = os.path.join(settings.ASSETS_DIR, "decorations")
ROCK_KINDS = ("pebbles", "boulder", "cairn")
TREE_KINDS = ("sakura", "pine", "bamboo")


class Decoration(pygame.sprite.Sprite):
    """A static or looping-animated image placed by its midbottom (feet) point."""

    def __init__(self, game: Game, frames, pos, layer_group, fps=0):
        super().__init__(game.all_sprites, layer_group)
        self.game = game
        self.animation = None
        if len(frames) > 1 and fps > 0:
            # random start frame so identical trees don't sway in sync
            self.animation = Animation(frames, fps, start=random.randrange(len(frames)))
            self.image = self.animation.image
        else:
            self.image = frames[0]
        self.rect = self.image.get_rect(midbottom=pos)

    def update(self):
        if self.animation:
            self.animation.update(self.game.dt)
            self.image = self.animation.image


class Rock(Decoration):
    """Drawn in FRONT of the player."""

    def __init__(self, game: Game, kind, pos):
        if kind not in ROCK_KINDS:
            raise ValueError(f"Unknown rock '{kind}', expected one of {ROCK_KINDS}")
        img = load_image(os.path.join(DECOR_DIR, "rocks", f"{kind}.png"), settings.SCALE)
        super().__init__(game, [img], pos, game.foreground_decor)


class Tree(Decoration):
    """Drawn BEHIND the player, gently swaying."""

    def __init__(self, game: Game, kind, pos, fps=settings.TREE_ANIM_FPS):
        if kind not in TREE_KINDS:
            raise ValueError(f"Unknown tree '{kind}', expected one of {TREE_KINDS}")
        frames = load_frames(os.path.join(DECOR_DIR, "trees", kind), settings.SCALE)
        super().__init__(game, frames, pos, game.background_decor, fps)
