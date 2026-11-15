"""Shinobi: an enemy ninja. Patrols like the samurai, but once he spots you he's
fast, stabs with a dagger up close, and every few seconds dashes straight at you.

Modes (patrol + hurt behave like the samurai's, see enemy.py):
    patrol_walk / patrol_idle -> looks for the ninja
    alert   -> spotted: tiny pause (he reacts fast), silent -> chase
    chase   -> sprints at the ninja; stabs when close; when the dash is ready
               and the ninja is 1-5 tiles away on the same level -> windup;
               at the edge of a pit he LEAPS across if he can reach the other
               side (otherwise he waits at the edge like the samurai)
    attack  -> quick dagger stab (hurts on the active frames) -> recover
    windup  -> crouches, dagger drawn back: the warning - jump or dodge now!
    dash    -> shoots forward with purple afterimages; hurts the ninja on
               contact (once); stops at walls, deep drops, after a hit or
               after SHINOBI_DASH_TIME -> recover
    recover -> short pause (longer after a dash: your chance to strike) -> chase
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING

from src import settings
from src.sprites.effects import Afterimage
from src.sprites.enemy import Enemy

if TYPE_CHECKING:
    from src.game import Game

SHINOBI_DIR = os.path.join(settings.ASSETS_DIR, "enemies", "shinobi")


class Shinobi(Enemy):
    ASSET_DIR = SHINOBI_DIR
    ANIM_FPS = settings.SHINOBI_ANIM_FPS
    PLAY_ONCE = ("attack", "windup")
    MODE_ANIM = {
        "patrol_walk": "walk", "patrol_idle": "idle", "alert": "idle",
        "chase": "run", "attack": "attack", "recover": "idle", "hurt": "idle",
        "windup": "windup", "dash": "dash",
    }
    MAX_HEALTH = settings.SHINOBI_MAX_HEALTH
    SIGHT_RANGE = settings.SHINOBI_SIGHT_RANGE
    SIGHT_HEIGHT = settings.SHINOBI_SIGHT_HEIGHT
    SPOT_SOUND = None                          # a ninja doesn't shout
    ALERT_TIME = settings.SHINOBI_ALERT_TIME
    ATTACK_ACTIVE_FRAMES = settings.SHINOBI_ATTACK_ACTIVE_FRAMES
    BLADE_REACH = settings.SHINOBI_DAGGER_REACH
    DAMAGE = settings.SHINOBI_DAMAGE

    def __init__(self, game: Game, pos):
        super().__init__(game, pos)
        self.dash_cooldown = 0.0
        self.dash_hit = False                  # already hurt the ninja this dash
        self.ghost_timer = 0.0
        self.leaping = False                   # in the air, jumping over a pit

    # ------------------------------------------------------------ helpers
    def gap_to_player(self):
        dx, dy = self.player_offset()
        return abs(dx) - (self.hitbox.width + self.game.player.hitbox.width) / 2, dy

    def can_dash(self):
        gap, dy = self.gap_to_player()
        return (self.dash_cooldown <= 0 and self.on_ground
                and settings.SHINOBI_DASH_MIN_RANGE <= gap <= settings.SHINOBI_DASH_MAX_RANGE
                and abs(dy) < self.hitbox.height
                and not self.dangerous_drop_ahead()
                and self.line_of_sight())

    def landing_ahead(self):
        """If there's a pit right in front of him: the gap (px) to the first ground
        on the other side within SHINOBI_MAX_JUMP_TILES, and how much higher (px)
        it is; None if there's no such ground or he couldn't reach it."""
        tm, ts = self.game.tilemap, self.game.tilemap.tile_size
        facing = 1 if self.facing_right else -1
        front = self.hitbox.right if self.facing_right else self.hitbox.left
        _, feet_row = tm.world_to_grid(self.hitbox.centerx, self.hitbox.bottom + 1)
        col0, _ = tm.world_to_grid(front + facing * 2, self.hitbox.bottom + 1)
        for d in range(1, settings.SHINOBI_MAX_JUMP_TILES + 1):
            col = col0 + facing * d
            if not tm.in_bounds(col, feet_row):
                return None
            for row in range(feet_row - 1, feet_row + 3):          # 1 up .. 2 down
                surface = tm.is_solid(col, row) or tm.get_tile(col, row) == "bridge"
                if surface and not tm.is_solid(col, row - 1) and not tm.is_solid(col, row - 2):
                    edge = col * ts if facing > 0 else (col + 1) * ts
                    gap = abs(edge - front)
                    rise = (feet_row - row) * ts
                    return (gap, rise) if self.can_reach(gap, rise) else None
        return None

    def can_reach(self, gap, rise):
        """Ballistics: does a running jump carry him `gap` px forward (plus half
        his body, to land safely) onto ground `rise` px higher (negative = lower)?"""
        v, g = settings.SHINOBI_JUMP_SPEED, self.gravity
        if v * v < 2 * g * rise:
            return False                       # can't even jump that high
        airtime = (v + math.sqrt(v * v - 2 * g * rise)) / g
        return settings.SHINOBI_RUN_SPEED * airtime >= gap + self.hitbox.width / 2

    def try_leap(self):
        """At a pit's edge while chasing: jump over it if the ninja is across it."""
        if not self.on_ground or not self.dangerous_drop_ahead():
            return False
        landing = self.landing_ahead()
        dx, _ = self.player_offset()
        if landing is None or abs(dx) <= landing[0]:
            return False                       # unreachable, or the ninja isn't across
        self.vel.y = -settings.SHINOBI_JUMP_SPEED
        self.leaping = True
        return True

    # ------------------------------------------------------------ actions
    def spot_player(self):
        super().spot_player()
        self.dash_cooldown = max(self.dash_cooldown, settings.SHINOBI_FIRST_DASH_DELAY)

    def start_windup(self):
        self.face_player()
        self.set_mode("windup", settings.SHINOBI_WINDUP_TIME)
        self.animations["windup"].reset()

    def start_dash(self):
        self.set_mode("dash", settings.SHINOBI_DASH_TIME)
        self.dash_cooldown = settings.SHINOBI_DASH_COOLDOWN
        self.dash_hit = False
        self.ghost_timer = 0.0
        self.game.audio.play("dash_attack", volume=0.6)

    def end_dash(self):
        self.vel.x = 0
        self.set_mode("recover", settings.SHINOBI_DASH_RECOVER_TIME)

    # ------------------------------------------------------------ brain
    def think(self, dt):
        self.mode_timer -= dt
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        mode = self.mode

        if mode in ("patrol_walk", "patrol_idle"):
            self.think_patrol()

        elif mode == "alert":
            if self.mode_timer <= 0:
                self.set_mode("chase")

        elif mode == "chase":
            self.face_player()
            gap, dy = self.gap_to_player()
            if gap <= settings.SHINOBI_ATTACK_RANGE and abs(dy) < self.hitbox.height:
                self.start_attack()
            elif self.can_dash():
                self.start_windup()
            elif self.try_leap():
                pass
            else:
                dx, _ = self.player_offset()
                far = abs(dx) > settings.SAMURAI_LOSE_RANGE or abs(dy) > 3 * settings.TILE_SIZE
                self.lose_timer = self.lose_timer + dt if far else 0.0
                if self.lose_timer > settings.SAMURAI_LOSE_TIME:
                    self.start_patrol_idle()

        elif mode == "windup":
            if self.mode_timer <= 0:
                self.start_dash()

        elif mode == "dash":
            if self.mode_timer <= 0 or self.dangerous_drop_ahead():
                self.end_dash()

        elif mode == "attack":
            if self.animations["attack"].finished:
                self.set_mode("recover", settings.SHINOBI_ATTACK_COOLDOWN)

        elif mode == "recover":
            if self.mode_timer <= 0:
                self.face_player()
                self.set_mode("chase")

        elif mode == "hurt":                   # (also cancels a windup or dash)
            if self.mode_timer <= 0:
                self.face_player()
                self.lose_timer = 0.0
                self.set_mode("chase")

    def move_intent(self):
        if self.mode == "hurt":
            return None
        facing = 1 if self.facing_right else -1
        if self.mode == "patrol_walk":
            return facing * settings.SAMURAI_WALK_SPEED
        if self.mode == "chase" and (self.leaping or not self.dangerous_drop_ahead()):
            return facing * settings.SHINOBI_RUN_SPEED
        if self.mode == "dash":
            return facing * settings.SHINOBI_DASH_SPEED
        return 0

    # ------------------------------------------------------------ update
    def update(self):
        super().update()
        if self.leaping and (self.on_ground and self.vel.y >= 0 or self.mode != "chase"):
            self.leaping = False               # landed (or got hit mid-air)
        if not self.alive() or self.mode != "dash":
            return
        if self.collisions["left"] or self.collisions["right"]:
            self.end_dash()                    # ran into a wall
            return
        player = self.game.player
        if not self.dash_hit and self.hitbox.inflate(8, 0).colliderect(player.hitbox):
            if player.take_damage(settings.SHINOBI_DASH_DAMAGE, self.hitbox.centerx):
                self.dash_hit = True
                self.end_dash()                # stop right after the hit
                return
        self.ghost_timer -= self.game.dt
        if self.ghost_timer <= 0:
            Afterimage(self.game, self.image, self.rect.topleft, color=settings.SHINOBI_GHOST_COLOR)
            self.ghost_timer += settings.GHOST_INTERVAL
