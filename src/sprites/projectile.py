"""Projectiles: arrows.

An arrow flies on a gravity arc, points along its flight direction and sticks
into ground and walls.
  - archer arrows (default) hurt the ninja (respecting his invulnerability /
    dash) and can be cut out of the air by his blade
  - friendly arrows (the ninja's bow) hurt the first enemy they hit
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import load_image
from src.sprites.effects import DeathFade

if TYPE_CHECKING:
    from src.game import Game

ARROW_IMAGE = os.path.join(settings.ASSETS_DIR, "enemies", "archer", "arrow.png")
TIP_DISTANCE = 6 * settings.SCALE          # centre of the image -> arrow head


def ballistic_velocity(start, target, speed_x=settings.ARROW_SPEED_X,
                       gravity=settings.ARROW_GRAVITY, min_time=settings.ARROW_MIN_FLIGHT):
    """Launch velocity so a projectile under `gravity` lands on `target`.
    The horizontal speed fixes the flight time; the vertical speed is solved from it,
    so long shots arc high and short shots stay flatter."""
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    t = max(abs(dx) / speed_x, min_time)
    return pygame.Vector2(dx / t, (dy - 0.5 * gravity * t * t) / t)


class Arrow(pygame.sprite.Sprite):
    _rotations = {}                          # angle (deg, step 6) -> rotated image

    def __init__(self, game: Game, pos, vel, damage=settings.ARROW_DAMAGE,
                 friendly=False, gravity=settings.ARROW_GRAVITY):
        super().__init__(game.all_sprites, game.projectiles)
        self.game = game
        self.friendly = friendly           # shot by the ninja -> hits enemies
        self.gravity = gravity
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.damage = damage
        self.stuck = False
        self.stuck_timer = 0.0
        self.angle = 0.0
        self.update_image()

    # ------------------------------------------------------------ visuals
    @classmethod
    def rotated(cls, angle):
        key = round(angle / 6) * 6 % 360
        if key not in cls._rotations:
            base = load_image(ARROW_IMAGE, settings.SCALE)
            # pygame rotates counter-clockwise; screen y points down -> negate
            cls._rotations[key] = pygame.transform.rotate(base, -key)
        return cls._rotations[key]

    def update_image(self):
        if not self.stuck and self.vel.length_squared() > 0:
            self.angle = math.degrees(math.atan2(self.vel.y, self.vel.x))
        self.image = self.rotated(self.angle)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    @property
    def tip(self):
        a = math.radians(self.angle)
        return (self.pos.x + math.cos(a) * TIP_DISTANCE, self.pos.y + math.sin(a) * TIP_DISTANCE)

    # ------------------------------------------------------------ update
    def update(self):
        dt = self.game.dt
        if self.stuck:
            self.stuck_timer -= dt
            if self.stuck_timer <= 0:
                self.kill()
            elif self.stuck_timer < 0.4:                     # fade out at the end
                self.image = self.image.copy()
                self.image.set_alpha(round(255 * self.stuck_timer / 0.4))
            return

        self.vel.y += self.gravity * dt
        self.pos += self.vel * dt
        self.update_image()

        tm = self.game.tilemap
        tx, ty = self.tip
        if not (-64 <= tx <= tm.width + 64) or ty > tm.height + 64:
            self.kill()                                      # left the map
            return
        if tm.is_solid(*tm.world_to_grid(tx, ty)):
            self.stuck = True                                # thunk - stuck in the ground
            self.stuck_timer = settings.ARROW_STUCK_TIME
            return

        if self.friendly:
            for enemy in self.game.enemies:
                if not enemy.invulnerable and enemy.hitbox.collidepoint(tx, ty):
                    if getattr(enemy, "blocks_arrows", False):   # e.g. the guardian's shield
                        enemy.deflect_arrow(self)
                        self.kill()
                        return
                    enemy.take_damage(self.damage, self.pos.x - math.copysign(100, self.vel.x))
                    self.kill()
                    return
            return

        player = self.game.player
        blade = player.attack_hitbox
        if blade and blade.collidepoint(tx, ty):            # cut out of the air
            DeathFade(self.game, self.image, self.rect.topleft, lifetime=0.2)
            self.kill()
            return
        if player.hitbox.collidepoint(tx, ty):
            source_x = self.pos.x - math.copysign(100, self.vel.x)   # knock him along the flight
            if player.take_damage(self.damage, source_x):
                self.kill()
            # ignored hit (invulnerable / dashing): the arrow flies on
