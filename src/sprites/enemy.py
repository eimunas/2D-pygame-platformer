"""Samurai enemy.

Behaviour (a small state machine, see `self.mode`):

    patrol_walk  -> walks; turns at walls and ledges; after a while -> patrol_idle
    patrol_idle  -> stands still; then maybe turns around -> patrol_walk
        (both patrol modes look for the ninja: in range, IN FRONT, and not
         hidden behind terrain)
    alert        -> spotted! screen shakes, short pause, faces the ninja -> chase
    chase        -> runs at the ninja with the katana raised; hops up steps and
                    drops down small ones (<= SAMURAI_MAX_STEP_DOWN tiles), stops
                    at deep drops/gaps; gives up if the ninja gets far away
    attack       -> heavy overhead cut; the ninja takes damage if the blade
                    connects on the active frames
    recover      -> short cooldown, then chase again
    hurt         -> hit by the ninja: flashes, knocked back, attack cancelled,
                    then turns to face him and chases (from any mode)
"""

from __future__ import annotations

import math
import os
import random
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames
from src.sprites.effects import DeathFade
from src.sprites.physics_entity import PhysicsEntity

if TYPE_CHECKING:
    from src.game import Game

SAMURAI_DIR = os.path.join(settings.ASSETS_DIR, "enemies", "samurai")
MODE_ANIM = {
    "patrol_walk": "walk", "patrol_idle": "idle", "alert": "idle",
    "chase": "run", "attack": "attack", "recover": "idle", "hurt": "idle",
}


class Enemy(PhysicsEntity):
    # Subclasses (e.g. Archer) override these to change look and stats.
    ASSET_DIR = SAMURAI_DIR
    ANIM_FPS = settings.SAMURAI_ANIM_FPS
    PLAY_ONCE = ("attack",)                    # animations that don't loop
    MODE_ANIM = MODE_ANIM
    MAX_HEALTH = settings.SAMURAI_MAX_HEALTH
    SIGHT_RANGE = settings.SAMURAI_SIGHT_RANGE
    SIGHT_HEIGHT = settings.SAMURAI_SIGHT_HEIGHT
    SPOT_SOUND = "enemy_attack"                # None = silent when spotting the ninja
    ALERT_TIME = settings.SAMURAI_ALERT_TIME
    ATTACK_ACTIVE_FRAMES = settings.SAMURAI_ATTACK_ACTIVE_FRAMES
    BLADE_REACH = 12                           # art px from his centre the blade reaches
    DAMAGE = settings.SAMURAI_DAMAGE

    def __init__(self, game: Game, pos):
        super().__init__(game, pos, settings.SAMURAI_HITBOX, groups=(game.actors, game.enemies))
        self.animations = {
            name: Animation(load_frames(os.path.join(self.ASSET_DIR, name), settings.SCALE),
                            fps, loop=name not in self.PLAY_ONCE)
            for name, fps in self.ANIM_FPS.items()
        }
        self.anim_name = "idle"
        self.facing_right = random.choice((True, False))
        self.mode = "patrol_idle"
        self.mode_timer = random.uniform(*settings.SAMURAI_PATROL_IDLE_TIME)
        self.lose_timer = 0.0
        self.attack_landed = False

        self.max_health = self.MAX_HEALTH
        self.health = self.max_health
        self.flash_timer = 0.0
        self.last_hit_by = -1          # id of the player swing that last hit us

        self.image = self.animation.image
        self.align_image()

    @property
    def animation(self) -> Animation:
        return self.animations[self.anim_name]

    # ------------------------------------------------------------ senses
    def player_offset(self):
        p = self.game.player
        return (p.hitbox.centerx - self.hitbox.centerx,
                p.hitbox.centery - self.hitbox.centery)

    def can_see_player(self):
        """In range, roughly level, and not behind terrain.
        (With ENEMY_SPOT_ONLY_IN_FRONT he must also be facing the ninja.)
        Spotting turns him towards the ninja, so he then attacks from either side."""
        dx, dy = self.player_offset()
        if abs(dx) > self.SIGHT_RANGE or abs(dy) > self.SIGHT_HEIGHT:
            return False
        if settings.ENEMY_SPOT_ONLY_IN_FRONT and dx != 0 and (dx > 0) != self.facing_right:
            return False                      # the ninja is behind him
        return self.line_of_sight()

    def line_of_sight(self):
        """Clear view from his eyes to the ninja's head OR body (seeing his head
        over the edge of a ledge is enough)."""
        tm = self.game.tilemap
        eye = pygame.Vector2(self.hitbox.centerx, self.hitbox.top + 12)
        p = self.game.player.hitbox
        for target in (pygame.Vector2(p.centerx, p.top + 8), pygame.Vector2(p.center)):
            steps = max(1, int(eye.distance_to(target) // 16))
            if not any(tm.is_solid(*tm.world_to_grid(*eye.lerp(target, i / steps)))
                       for i in range(1, steps)):
                return True
        return False

    def drop_ahead(self):
        """How many tiles the ground drops just in front of him:
        0 = flat ground, 1-2 = a step down, None = deeper than that or no ground."""
        if not self.on_ground:
            return 0
        tm = self.game.tilemap
        x = self.hitbox.right + 2 if self.facing_right else self.hitbox.left - 2
        col, row = tm.world_to_grid(x, self.hitbox.bottom + 1)
        if not 0 <= col < tm.cols:
            return 0                          # map border is handled as a wall
        for depth in range(settings.SAMURAI_MAX_STEP_DOWN + 1):
            r = row + depth
            if r >= tm.rows:
                return None                   # falls out of the map
            if tm.is_solid(col, r) or tm.get_tile(col, r) == "bridge":
                return depth
        return None

    def ledge_ahead(self):
        """Patrol rule: any drop counts as a ledge (stay on your own ground)."""
        return self.drop_ahead() != 0

    def dangerous_drop_ahead(self):
        """Chase rule: small steps down are fine, deep drops/gaps are not."""
        return self.drop_ahead() is None

    def face_player(self):
        dx, _ = self.player_offset()
        if abs(dx) > 4:                       # avoid flip-flopping when right on top
            self.facing_right = dx > 0

    # ------------------------------------------------------------ modes
    def set_mode(self, mode, timer=0.0):
        self.mode = mode
        self.mode_timer = timer

    def start_patrol_walk(self):
        self.set_mode("patrol_walk", random.uniform(*settings.SAMURAI_PATROL_WALK_TIME))

    def start_patrol_idle(self):
        self.set_mode("patrol_idle", random.uniform(*settings.SAMURAI_PATROL_IDLE_TIME))

    def spot_player(self):
        self.face_player()
        self.set_mode("alert", self.ALERT_TIME)
        self.lose_timer = 0.0
        self.game.camera.shake(*settings.SAMURAI_SPOT_SHAKE)
        if self.SPOT_SOUND:
            self.game.audio.play(self.SPOT_SOUND)

    def start_attack(self):
        self.set_mode("attack")
        self.attack_landed = False
        self.animations["attack"].reset()
        self.game.audio.play("attack")

    def think_patrol(self):
        """Shared by all enemy types: walk/idle around, look for the ninja."""
        if self.can_see_player():
            self.spot_player()
        elif self.mode == "patrol_walk":
            if self.mode_timer <= 0:
                self.start_patrol_idle()
            elif self.ledge_ahead():
                self.facing_right = not self.facing_right
        elif self.mode_timer <= 0:
            if random.random() < 0.5:
                self.facing_right = not self.facing_right
            self.start_patrol_walk()

    def think(self, dt):
        self.mode_timer -= dt
        mode = self.mode

        if mode in ("patrol_walk", "patrol_idle"):
            self.think_patrol()

        elif mode == "alert":
            if self.mode_timer <= 0:
                self.set_mode("chase")

        elif mode == "chase":
            self.face_player()
            dx, dy = self.player_offset()
            gap = abs(dx) - (self.hitbox.width + self.game.player.hitbox.width) / 2
            if gap <= settings.SAMURAI_ATTACK_RANGE and abs(dy) < self.hitbox.height:
                self.start_attack()
            # lose interest if the ninja stays far away
            far = abs(dx) > settings.SAMURAI_LOSE_RANGE or abs(dy) > 3 * settings.TILE_SIZE
            self.lose_timer = self.lose_timer + dt if far else 0.0
            if self.lose_timer > settings.SAMURAI_LOSE_TIME:
                self.start_patrol_idle()

        elif mode == "attack":
            if self.animations["attack"].finished:
                self.set_mode("recover", settings.SAMURAI_ATTACK_COOLDOWN)

        elif mode == "recover":
            self.face_player()
            if self.mode_timer <= 0:
                self.set_mode("chase")

        elif mode == "hurt":
            if self.mode_timer <= 0:
                self.face_player()
                self.lose_timer = 0.0
                self.set_mode("chase")

    def move_intent(self):
        """Horizontal speed for the current mode (None = keep sliding from a knockback)."""
        if self.mode == "hurt":
            return None
        facing = 1 if self.facing_right else -1
        if self.mode == "patrol_walk":
            return facing * settings.SAMURAI_WALK_SPEED
        if self.mode == "chase" and not self.dangerous_drop_ahead():
            return facing * settings.SAMURAI_RUN_SPEED
        return 0

    # ------------------------------------------------------------ combat
    @property
    def attack_hitbox(self):
        if self.mode != "attack" or self.animation.index not in self.ATTACK_ACTIVE_FRAMES:
            return None
        rect = pygame.Rect(0, 0, self.BLADE_REACH * settings.SCALE, 16 * settings.SCALE)
        rect.bottom = self.hitbox.bottom
        if self.facing_right:
            rect.left = self.hitbox.centerx
        else:
            rect.right = self.hitbox.centerx
        return rect

    def take_damage(self, amount, source_x):
        self.health -= amount
        self.flash_timer = settings.HIT_FLASH_TIME
        self.game.audio.play("hit_hurt")
        if self.health <= 0:
            self.die()
            return
        away = 1 if self.hitbox.centerx >= source_x else -1
        kx, ky = settings.SAMURAI_KNOCKBACK
        self.vel.update(away * kx, -ky)
        self.set_mode("hurt", settings.SAMURAI_HURT_TIME)      # also cancels his attack
        self.game.camera.shake(*settings.ENEMY_HIT_SHAKE)

    def die(self):
        DeathFade(self.game, self.image, self.rect.topleft)
        self.game.camera.shake(*settings.ENEMY_DEATH_SHAKE)
        self.kill()

    def check_hit(self):
        hb = self.attack_hitbox
        if hb and not self.attack_landed and hb.colliderect(self.game.player.hitbox):
            if self.game.player.take_damage(self.DAMAGE, self.hitbox.centerx):
                self.attack_landed = True

    def cutscene_animate(self, dt):
        """During cutscenes: stand still and play the idle animation only."""
        if self.anim_name != "idle":
            self.anim_name = "idle"
            self.animation.reset()
        self.animation.update(dt)
        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        self.align_image()

    def stand_down_update(self):
        """After the ninja is defeated: no AI, slide to a stop, land, stand idle."""
        dt = self.game.dt
        self.flash_timer = 0.0
        self.vel.x *= math.exp(-8 * dt)
        self.physics_update()
        if self.alive():
            self.cutscene_animate(dt)

    # ------------------------------------------------------------ update
    def update(self):
        dt = self.game.dt
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.think(dt)
        speed = self.move_intent()
        if speed is None:
            self.vel.x *= math.exp(-6 * dt)    # knockback slows down
        else:
            self.vel.x = speed
        self.physics_update()
        if not self.alive():                   # fell out of the map
            return

        if self.collisions["left"] or self.collisions["right"]:
            if self.mode == "patrol_walk":
                self.facing_right = not self.facing_right
            elif self.mode == "chase" and self.on_ground:
                self.vel.y = -settings.SAMURAI_JUMP_SPEED     # hop up the step

        name = self.MODE_ANIM[self.mode]
        if name != self.anim_name:
            self.anim_name = name
            self.animation.reset()
        self.animation.update(dt)
        if self.mode == "attack":
            self.check_hit()

        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        if self.flash_timer > 0:               # white hit flash
            mask = pygame.mask.from_surface(self.image)
            self.image = mask.to_surface(setcolor=(255, 255, 255), unsetcolor=(0, 0, 0, 0))
        self.align_image()
