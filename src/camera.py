"""Smooth-follow camera.

The camera stores the world position of the screen's top-left corner.
Everything in the world is drawn shifted by -camera.offset:

    screen.blit(sprite.image, camera.apply(sprite.rect))
    tilemap.draw(screen, camera.offset)
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from src import settings

if TYPE_CHECKING:
    from src.game import Game


class Camera:
    def __init__(
        self,
        game: Game,
        target,
        smoothing=settings.CAMERA_SMOOTHING,
        look_ahead=settings.CAMERA_LOOK_AHEAD,
        offset=settings.CAMERA_OFFSET,
    ):
        """
        target     - any sprite with a `rect` (optionally `facing_right`)
        smoothing  - how fast the camera catches up; higher = snappier, 0 = no movement
        look_ahead - pixels the camera leads in the direction the target faces
        offset     - fixed (x, y) shift of the target from screen centre;
                     negative y shows more of what's above the player
        """
        self.game = game
        self.target = target
        self.smoothing = smoothing
        self.look_ahead = look_ahead
        self.fixed_offset = pygame.Vector2(offset)
        self.view_w, self.view_h = game.screen.get_size()
        self.pos = pygame.Vector2()

        # screen shake (added on top of pos when drawing; never moves pos itself)
        self.shake_strength = 0.0
        self.shake_duration = 0.0
        self.shake_time = 0.0
        self.shake_offset = pygame.Vector2()

        self.snap()

    # ------------------------------------------------------------ position
    def desired_position(self):
        t = self.target
        facing = 1 if getattr(t, "facing_right", True) else -1
        x = t.rect.centerx + facing * self.look_ahead + self.fixed_offset.x - self.view_w / 2
        y = t.rect.centery + self.fixed_offset.y - self.view_h / 2
        return self.clamp(pygame.Vector2(x, y))

    def clamp(self, pos):
        """Keep the view inside the tilemap."""
        tm = self.game.tilemap
        pos.x = max(0, min(pos.x, max(0, tm.width - self.view_w)))
        pos.y = max(0, min(pos.y, max(0, tm.height - self.view_h)))
        return pos

    def snap(self):
        """Jump straight to the target (use on level start / respawn)."""
        self.pos = self.desired_position()

    def update(self):
        # frame-rate independent exponential smoothing:
        # the camera closes the same fraction of the gap per second at any FPS
        t = 1 - math.exp(-self.smoothing * self.game.dt)
        self.pos += (self.desired_position() - self.pos) * t
        self.update_shake()

    # ------------------------------------------------------------ shake
    def shake(self, strength, duration):
        """Shake the view by up to `strength` pixels, fading out over `duration` s.
        A weaker shake never cuts a stronger one short."""
        current = self.shake_strength * (self.shake_time / self.shake_duration) if self.shake_time > 0 else 0
        if strength >= current:
            self.shake_strength = strength
            self.shake_duration = self.shake_time = duration

    def update_shake(self):
        if self.shake_time <= 0:
            self.shake_offset.update(0, 0)
            return
        self.shake_time = max(0.0, self.shake_time - self.game.dt)
        k = self.shake_time / self.shake_duration          # 1 -> 0, fades out
        amount = self.shake_strength * k
        self.shake_offset.update(random.uniform(-amount, amount), random.uniform(-amount, amount))

    @property
    def render_pos(self):
        """Where the view is drawn from this frame: follow position + shake."""
        return self.clamp(self.pos + self.shake_offset)

    # ------------------------------------------------------------ conversions
    @property
    def offset(self):
        """Integer offset, so pixel art stays crisp (no sub-pixel shimmer)."""
        p = self.render_pos
        return round(p.x), round(p.y)

    @property
    def view_rect(self):
        """The visible part of the world, in world coordinates."""
        return pygame.Rect(self.offset, (self.view_w, self.view_h))

    def apply(self, rect):
        """World rect -> screen rect."""
        ox, oy = self.offset
        return rect.move(-ox, -oy)

    def screen_to_world(self, x, y):
        ox, oy = self.offset
        return x + ox, y + oy
