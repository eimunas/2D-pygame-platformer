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

# other static props: name -> (image inside assets/decorations, layer)
#   "back"  = drawn behind the player, "front" = drawn in front of the player
PROPS = {
    "lantern": ("props/lantern.png", "back"),
    "torii": ("props/torii.png", "back"),
    "cave_entrance": ("props/cave_entrance.png", "back"),
    "bush": ("plants/bush.png", "front"),
    "bush_small": ("plants/bush_small.png", "front"),
}


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


class Prop(Decoration):
    """Any static prop listed in PROPS (lantern, torii, bushes, ...)."""

    def __init__(self, game: Game, kind, pos):
        if kind not in PROPS:
            raise ValueError(f"Unknown prop '{kind}', expected one of {tuple(PROPS)}")
        path, layer = PROPS[kind]
        img = load_image(os.path.join(DECOR_DIR, path), settings.SCALE)
        group = game.background_decor if layer == "back" else game.foreground_decor
        super().__init__(game, [img], pos, group)


class ExitGate(Prop):
    """The level's exit: a torii gate. Walking through its opening finishes the level."""

    def __init__(self, game: Game, pos):
        super().__init__(game, "torii", pos)
        # trigger = the opening between the pillars, at ground level
        self.trigger = pygame.Rect(0, 0, 8 * settings.SCALE, 10 * settings.SCALE)
        self.trigger.midbottom = self.rect.midbottom
        game.exit_gate = self


class CaveEntrance(Prop):
    """The ancient caves: a level exit like the torii gate - walking into the dark
    mouth finishes the level (but only once its guardian is defeated, see
    BossArena.exit_open)."""

    def __init__(self, game: Game, pos):
        super().__init__(game, "cave_entrance", pos)
        self.trigger = pygame.Rect(0, 0, 10 * settings.SCALE, 14 * settings.SCALE)
        self.trigger.midbottom = self.rect.midbottom
        game.exit_gate = self


class Tree(Decoration):
    """Drawn BEHIND the player, gently swaying."""

    def __init__(self, game: Game, kind, pos, fps=settings.TREE_ANIM_FPS):
        if kind not in TREE_KINDS:
            raise ValueError(f"Unknown tree '{kind}', expected one of {TREE_KINDS}")
        frames = load_frames(os.path.join(DECOR_DIR, "trees", kind), settings.SCALE)
        super().__init__(game, frames, pos, game.background_decor, fps)
