"""Base class for anything that moves, falls and collides with tiles
(Player, enemies, ...).

Subclasses decide HOW to move by setting `self.vel`, then call
`self.physics_update()` once per frame. This class does the rest:
gravity, moving, pushing the hitbox out of solid tiles, landing on one-way
platforms and stepping up small ledges.

    class Enemy(PhysicsEntity):
        def __init__(self, game, pos):
            super().__init__(game, pos, hitbox_size=(40, 48), groups=(game.actors,))
            self.image = ...
            self.align_image()

        def update(self):
            self.vel.x = 80 if self.facing_right else -80
            self.physics_update()
            if self.collisions["left"] or self.collisions["right"]:
                self.facing_right = not self.facing_right   # turn around at walls
            self.align_image()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from src import settings

if TYPE_CHECKING:
    from src.game import Game


class PhysicsEntity(pygame.sprite.Sprite):
    def __init__(
        self,
        game: Game,
        pos,
        hitbox_size,
        groups=(),
        gravity=settings.GRAVITY,
        max_fall_speed=settings.MAX_FALL_SPEED,
    ):
        """pos = feet position (midbottom of the hitbox) in world pixels."""
        super().__init__(game.all_sprites, *groups)
        self.game = game

        self.pos = pygame.Vector2(pos)          # float feet position (precise movement)
        self.vel = pygame.Vector2()             # pixels per second
        self.hitbox = pygame.Rect((0, 0), hitbox_size)
        self.hitbox.midbottom = (round(self.pos.x), round(self.pos.y))

        self.gravity = gravity
        self.gravity_enabled = True             # turn off for dashes, ladders, ...
        self.max_fall_speed = max_fall_speed
        self.step_height = settings.STEP_HEIGHT # ledges this small are walked up
        self.drop_through = False               # True = fall through one-way platforms
        self.facing_right = True
        self.on_ground = False
        self.collisions = {"left": False, "right": False, "top": False, "bottom": False}

        # subclasses replace image; rect is where the image is drawn
        self.image = pygame.Surface(hitbox_size, pygame.SRCALPHA)
        self.rect = self.hitbox.copy()

    # ------------------------------------------------------------ physics
    def physics_update(self):
        dt = self.game.dt
        if self.gravity_enabled:
            self.vel.y = min(self.vel.y + self.gravity * dt, self.max_fall_speed)

        was_on_ground = self.on_ground
        self.collisions = dict.fromkeys(self.collisions, False)
        # move one axis at a time, so we always know which side we hit
        self.move_x(self.vel.x * dt, was_on_ground)
        self.move_y(self.vel.y * dt)
        self.on_ground = self.collisions["bottom"]

        if self.hitbox.top > self.game.tilemap.height:
            self.on_fell_out_of_map()

    def set_bottom(self, y):
        self.hitbox.bottom = y
        self.pos.y = y

    def move_x(self, dx, was_on_ground=False):
        tm = self.game.tilemap
        self.pos.x += dx
        self.hitbox.centerx = round(self.pos.x)
        for tile in tm.solid_rects_near(self.hitbox):
            if not self.hitbox.colliderect(tile):
                continue
            # tiny ledge: step up instead of stopping
            rise = self.hitbox.bottom - tile.top
            if was_on_ground and 0 < rise <= self.step_height:
                stepped = self.hitbox.copy()
                stepped.bottom = tile.top
                if not any(stepped.colliderect(t) for t in tm.solid_rects_near(stepped)):
                    self.set_bottom(tile.top)
                    continue
            if dx > 0:
                self.hitbox.right = tile.left
                self.collisions["right"] = True
            elif dx < 0:
                self.hitbox.left = tile.right
                self.collisions["left"] = True

        # the map's left/right borders act as walls
        if self.hitbox.left < 0:
            self.hitbox.left = 0
            self.collisions["left"] = True
        elif self.hitbox.right > tm.width:
            self.hitbox.right = tm.width
            self.collisions["right"] = True

        if self.collisions["left"] or self.collisions["right"]:
            self.vel.x = 0
            self.pos.x = self.hitbox.centerx

    def move_y(self, dy):
        tm = self.game.tilemap
        old_bottom = self.hitbox.bottom
        self.pos.y += dy
        self.hitbox.bottom = round(self.pos.y)
        for tile in tm.solid_rects_near(self.hitbox):
            if not self.hitbox.colliderect(tile):
                continue
            if dy > 0:
                self.hitbox.bottom = tile.top
                self.collisions["bottom"] = True
            elif dy < 0:
                self.hitbox.top = tile.bottom
                self.collisions["top"] = True

        # one-way platforms: only land on them when coming down from above
        if dy > 0 and not self.drop_through:
            for deck in tm.platform_rects_near(self.hitbox):
                if self.hitbox.colliderect(deck) and old_bottom <= deck.top:
                    self.hitbox.bottom = deck.top
                    self.collisions["bottom"] = True

        if self.collisions["bottom"] or self.collisions["top"]:
            self.vel.y = 0
            self.pos.y = self.hitbox.bottom

    # ------------------------------------------------------------ hooks / helpers
    def on_fell_out_of_map(self):
        """Called when the entity falls below the map. Default: remove it."""
        self.kill()

    def align_image(self):
        """Place the (possibly larger) image so its feet match the hitbox."""
        self.rect = self.image.get_rect(midbottom=self.hitbox.midbottom)
