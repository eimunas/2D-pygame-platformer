"""The ninja's bomb (a horoku): thrown in an arc, bounces, and explodes when it
touches an enemy or when its fuse runs out. The blast hurts EVERY enemy inside
BOMB_RADIUS (and the ninja too, if he's standing in it - light it and run!).

    Bomb(game, start_pos, velocity)
    Explosion(game, center)          # just the visual (Bomb.explode makes one)

A dashing shinobi is too fast for the blast too (see Enemy.invulnerable).
"""

from __future__ import annotations

import math
import os
import random
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import load_image
from src.sprites.effects import Effect
from src.sprites.physics_entity import PhysicsEntity

if TYPE_CHECKING:
    from src.game import Game

BOMB_IMAGE = os.path.join(settings.ASSETS_DIR, "items", "bomb.png")


def rect_distance(point, rect):
    """Distance from a point to the closest point of a rect (0 if inside)."""
    px, py = point
    dx = max(rect.left - px, 0, px - rect.right)
    dy = max(rect.top - py, 0, py - rect.bottom)
    return math.hypot(dx, dy)


class Bomb(PhysicsEntity):
    def __init__(self, game: Game, pos, vel):
        size = settings.BOMB_HITBOX
        super().__init__(game, pos, (size, size), groups=(game.projectiles,))
        self.vel.update(vel)
        self.step_height = 0                   # a bomb doesn't walk up ledges
        self.fuse = settings.BOMB_FUSE
        self.base_image = load_image(BOMB_IMAGE, settings.BOMB_IMAGE_SCALE)
        self.flash_image = pygame.mask.from_surface(self.base_image).to_surface(
            setcolor=(255, 236, 200), unsetcolor=(0, 0, 0, 0))
        self.image = self.base_image
        self.align_image()

    def update(self):
        dt = self.game.dt
        self.fuse -= dt
        falling_speed = self.vel.y
        self.physics_update()
        if not self.alive():                   # fell into a pit: fizzles out
            return

        # bounce off the ground and walls, roll to a stop
        if self.collisions["bottom"] and falling_speed > settings.BOMB_MIN_BOUNCE:
            self.vel.y = -falling_speed * settings.BOMB_BOUNCE
        if self.collisions["left"] or self.collisions["right"]:
            self.vel.x = 0                     # (move_x already stopped it)
        if self.on_ground:
            self.vel.x *= math.exp(-settings.BOMB_GROUND_FRICTION * dt)

        if self.fuse <= 0 or self.touching_enemy():
            self.explode()
            return

        # blink faster and faster as the fuse burns down
        blink = 4 if self.fuse > 0.6 else 12
        self.image = self.flash_image if int(self.fuse * blink) % 2 == 0 and self.fuse < 1.0 else self.base_image
        self.align_image()

    def touching_enemy(self):
        return any(self.hitbox.colliderect(e.hitbox) for e in self.game.enemies)

    def explode(self):
        center = self.hitbox.center
        radius = settings.BOMB_RADIUS
        for enemy in list(self.game.enemies):          # list(): enemies may die here
            if not enemy.invulnerable and rect_distance(center, enemy.hitbox) <= radius:
                enemy.take_damage(settings.BOMB_DAMAGE, center[0])
        player = self.game.player
        if settings.BOMB_PLAYER_DAMAGE and rect_distance(center, player.hitbox) <= radius:
            player.take_damage(settings.BOMB_PLAYER_DAMAGE, center[0])
        Explosion(self.game, center)
        self.game.camera.shake(*settings.BOMB_SHAKE)
        self.game.audio.play("explosion")
        self.kill()


class Explosion(Effect):
    """A pixel-art blast: white flash -> orange fireball -> grey smoke puffs.
    Drawn small (1 px = 1 art pixel) and scaled up, so it matches the sprites."""

    PALETTE = [(255, 250, 226), (255, 214, 102), (246, 140, 52), (196, 72, 40), (92, 80, 86)]

    def __init__(self, game: Game, center, lifetime=settings.BOMB_EXPLOSION_TIME):
        super().__init__(game, game.effects_front, lifetime)
        self.center = center
        self.art_radius = settings.BOMB_RADIUS / settings.SCALE
        self.size = int(self.art_radius * 2) + 4
        rnd = random.Random()
        # fireball = a lumpy cluster of blobs: (angle, distance, size) as fractions of the radius
        self.blobs = [(0.0, 0.0, 0.42)] + [
            (rnd.uniform(0, 2 * math.pi), rnd.uniform(0.15, 0.38), rnd.uniform(0.2, 0.32))
            for _ in range(7)]
        # smoke puffs drifting outwards
        self.puffs = [(rnd.uniform(0, 2 * math.pi), rnd.uniform(0.3, 0.7), rnd.uniform(0.18, 0.3))
                      for _ in range(9)]
        self.animate()

    def update(self):
        self.age += self.game.dt
        if self.age >= self.lifetime:
            self.kill()
            return
        self.animate()

    def blob_pos(self, c, ang, dist, scale, rise=0.0):
        r = self.art_radius
        return (round(c + math.cos(ang) * r * dist * scale),
                round(c + math.sin(ang) * r * dist * scale * 0.8 - rise))

    def animate(self):
        t = self.progress
        c = self.size / 2
        r = self.art_radius
        art = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        flash, yellow, orange, red, smoke = self.PALETTE

        # smoke: grows, drifts out and up, fades
        if t > 0.2:
            k = (t - 0.2) / 0.8
            alpha = round(210 * (1 - k))
            for ang, dist, size in self.puffs:
                pos = self.blob_pos(c, ang, dist, 0.7 + 0.6 * k, rise=k * 5)
                pygame.draw.circle(art, (*smoke, alpha), pos, max(1, round(r * size * (0.7 + 0.6 * k))))

        # fireball: pops up fast, then shrinks into the smoke (red rim, orange body, yellow core)
        grow = min(1.0, t / 0.08)
        fire = grow * max(0.0, 1 - max(0.0, t - 0.08) / 0.5)
        if fire > 0:
            for color, layer in ((red, 1.0), (orange, 0.72), (yellow, 0.42)):
                for ang, dist, size in self.blobs:
                    pos = self.blob_pos(c, ang, dist, grow)
                    pygame.draw.circle(art, color, pos, max(1, round(r * size * layer * fire)))
        if t < 0.07:                                   # first instant: hot white core
            pygame.draw.circle(art, flash, (round(c), round(c)), max(1, round(r * 0.3)))

        # thin shock ring racing out to the edge of the blast radius
        if t < 0.3:
            ring = round(r * (0.3 + 0.7 * t / 0.3))
            pygame.draw.circle(art, (*yellow, round(170 * (1 - t / 0.3))), (round(c), round(c)), ring, 1)

        self.image = pygame.transform.scale_by(art, settings.SCALE)
        self.rect = self.image.get_rect(center=self.center)
