"""Samurai archer: patrols like the swordsman, but spots the ninja from far away
(and from higher/lower ground), keeps his distance and shoots arcing arrows.

Modes (patrol + hurt behave like the swordsman's, see enemy.py):
    patrol_walk / patrol_idle -> looks for the ninja (in front, in line of sight)
    alert   -> spotted: small screen shake, NO spot sound, short pause -> aim
    aim     -> faces the ninja; shoots when the cooldown is over;
               backs away if the ninja is too close; gives up if he's far away
    shoot   -> draw + release; the arrow leaves on the release frame
    retreat -> walks away from the ninja for a moment (not off ledges) -> aim
    hurt    -> knocked back, then aim again
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from src import settings
from src.sprites.enemy import Enemy
from src.sprites.projectile import Arrow, ballistic_velocity

if TYPE_CHECKING:
    from src.game import Game

ARCHER_DIR = os.path.join(settings.ASSETS_DIR, "enemies", "archer")


class Archer(Enemy):
    ASSET_DIR = ARCHER_DIR
    ANIM_FPS = settings.ARCHER_ANIM_FPS
    PLAY_ONCE = ("shoot",)
    MODE_ANIM = {
        "patrol_walk": "walk", "patrol_idle": "idle", "alert": "idle",
        "aim": "idle", "shoot": "shoot", "retreat": "walk", "hurt": "idle",
    }
    MAX_HEALTH = settings.ARCHER_MAX_HEALTH
    SIGHT_RANGE = settings.ARCHER_SIGHT_RANGE
    SIGHT_HEIGHT = settings.ARCHER_SIGHT_HEIGHT
    SPOT_SOUND = None                        # the archer spots you silently

    def __init__(self, game: Game, pos):
        super().__init__(game, pos)
        self.arrow_fired = False

    # ------------------------------------------------------------ actions
    def start_shoot(self):
        self.face_player()
        self.set_mode("shoot")
        self.animations["shoot"].reset()
        self.arrow_fired = False

    def bow_position(self):
        facing = 1 if self.facing_right else -1
        return (self.hitbox.centerx + facing * 5 * settings.SCALE,
                self.hitbox.top + 6 * settings.SCALE)

    def fire_arrow(self):
        start = self.bow_position()
        target = self.game.player.hitbox.center
        Arrow(self.game, start, ballistic_velocity(start, target))
        self.arrow_fired = True
        self.game.audio.play("arrow")

    def try_retreat(self):
        """Turn away and back off - unless that would walk off a ledge."""
        self.facing_right = not self.facing_right
        if self.ledge_ahead():
            self.face_player()
            return False
        self.set_mode("retreat", settings.ARCHER_RETREAT_TIME)
        return True

    # ------------------------------------------------------------ brain
    def think(self, dt):
        self.mode_timer -= dt
        mode = self.mode
        dx, dy = self.player_offset()

        if mode in ("patrol_walk", "patrol_idle"):
            self.think_patrol()

        elif mode == "alert":
            if self.mode_timer <= 0:
                self.set_mode("aim", settings.ARCHER_FIRST_SHOT_DELAY)

        elif mode == "aim":
            self.face_player()
            far = abs(dx) > settings.ARCHER_LOSE_RANGE or abs(dy) > 1.5 * self.SIGHT_HEIGHT
            self.lose_timer = self.lose_timer + dt if far else 0.0
            if self.lose_timer > settings.SAMURAI_LOSE_TIME:
                self.start_patrol_idle()
            elif abs(dx) < settings.ARCHER_KEEP_DISTANCE and self.try_retreat():
                pass
            elif self.mode_timer <= 0 and not far:
                self.start_shoot()

        elif mode == "retreat":
            if (self.mode_timer <= 0 or abs(dx) >= 1.3 * settings.ARCHER_KEEP_DISTANCE
                    or self.ledge_ahead()):
                self.face_player()
                self.set_mode("aim", 0.25)

        elif mode == "shoot":
            shoot = self.animations["shoot"]      # (self.animation may still be "idle" this frame)
            if not self.arrow_fired and shoot.index >= settings.ARCHER_RELEASE_FRAME:
                self.fire_arrow()
            if shoot.finished:
                self.set_mode("aim", settings.ARCHER_SHOOT_COOLDOWN)

        elif mode == "hurt":
            if self.mode_timer <= 0:
                self.face_player()
                self.lose_timer = 0.0
                self.set_mode("aim", settings.ARCHER_SHOOT_COOLDOWN / 2)

    def move_intent(self):
        if self.mode == "hurt":
            return None                       # slide from the knockback
        facing = 1 if self.facing_right else -1
        if self.mode == "patrol_walk":
            return facing * settings.SAMURAI_WALK_SPEED
        if self.mode == "retreat":
            return facing * settings.SAMURAI_WALK_SPEED * 1.5
        return 0
