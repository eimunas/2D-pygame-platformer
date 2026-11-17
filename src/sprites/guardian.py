"""Guardian: a tall samurai in dark iron armour with a yari spear and a tower shield.

Slow, heavy and tough. Patrols, spots, chases and attacks like the samurai (see
enemy.py), but:

  - he's slow (GUARDIAN_WALK/RUN_SPEED) and too heavy to leap over pits;
  - his spear thrust reaches much further than a katana and hits hard
    (GUARDIAN_DAMAGE) - get in close after he thrusts;
  - he has more health (GUARDIAN_MAX_HEALTH) AND a SHIELD (GUARDIAN_SHIELD_HP):
    katana hits wear the shield down first (it cracks at half, then breaks off),
    and only then hurt him. Shield hits don't make him stagger;
  - ARROWS can't hurt him while he has his shield - they glance off it. Once
    the shield is broken, arrows hurt him like anyone else;
  - a BOMB blast goes around the shield and hurts him directly.
"""

from __future__ import annotations

import os
import random
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames
from src.sprites.effects import DeathFade, FloatingText
from src.sprites.enemy import Enemy
from src.sprites.golem import RockChunk

if TYPE_CHECKING:
    from src.game import Game

GUARDIAN_DIR = os.path.join(settings.ASSETS_DIR, "enemies", "guardian")
SHIELD_SETS = {"full": GUARDIAN_DIR,
               "cracked": os.path.join(GUARDIAN_DIR, "cracked"),
               "broken": os.path.join(GUARDIAN_DIR, "broken")}


class Spark(RockChunk):
    """A hot spark off the shield."""
    COLORS = ((255, 246, 200), (255, 214, 110), (250, 170, 70))


class ShieldShard(RockChunk):
    """A piece of the broken shield: crimson lacquer, iron, a bit of gold."""
    COLORS = ((116, 44, 46), (86, 30, 36), (58, 60, 78), (196, 160, 78))


class Guardian(Enemy):
    ASSET_DIR = GUARDIAN_DIR
    ANIM_FPS = settings.GUARDIAN_ANIM_FPS
    PLAY_ONCE = ("attack",)
    MODE_ANIM = dict(Enemy.MODE_ANIM, chase="walk")
    HITBOX = settings.GUARDIAN_HITBOX
    MAX_HEALTH = settings.GUARDIAN_MAX_HEALTH
    WALK_SPEED = settings.GUARDIAN_WALK_SPEED
    RUN_SPEED = settings.GUARDIAN_RUN_SPEED
    SIGHT_RANGE = settings.GUARDIAN_SIGHT_RANGE
    SIGHT_HEIGHT = settings.GUARDIAN_SIGHT_HEIGHT
    SPOT_SOUND = settings.GUARDIAN_SPOT_SOUND
    ALERT_TIME = settings.GUARDIAN_ALERT_TIME
    ATTACK_ACTIVE_FRAMES = settings.GUARDIAN_ATTACK_ACTIVE_FRAMES
    BLADE_REACH = settings.GUARDIAN_SPEAR_REACH
    DAMAGE = settings.GUARDIAN_DAMAGE
    ATTACK_RANGE = settings.GUARDIAN_ATTACK_RANGE
    ATTACK_COOLDOWN = settings.GUARDIAN_ATTACK_COOLDOWN
    KNOCKBACK = settings.GUARDIAN_KNOCKBACK
    HURT_TIME = settings.GUARDIAN_HURT_TIME

    def __init__(self, game: Game, pos):
        super().__init__(game, pos)
        # the same animations three times: shield intact / cracked / gone
        self.anim_sets = {"full": self.animations}
        for key in ("cracked", "broken"):
            self.anim_sets[key] = {
                name: Animation(load_frames(os.path.join(SHIELD_SETS[key], name), settings.SCALE),
                                fps, loop=name not in self.PLAY_ONCE)
                for name, fps in self.ANIM_FPS.items()
            }
        self.shield_max = settings.GUARDIAN_SHIELD_HP
        self.shield = self.shield_max

    # ------------------------------------------------------------ the shield
    @property
    def shield_state(self):
        if self.shield <= 0:
            return "broken"
        return "cracked" if self.shield <= self.shield_max / 2 else "full"

    def swap_shield_art(self):
        """Switch to the animation set that matches the shield, keeping the frame."""
        new = self.anim_sets[self.shield_state]
        if new is self.animations:
            return
        old = self.animation
        self.animations = new
        cur = self.animation
        cur.index, cur.timer, cur.finished = old.index, old.timer, old.finished

    def shield_point(self):
        """Roughly where the shield is (in front of him), in world px."""
        facing = 1 if self.facing_right else -1
        return (self.hitbox.centerx + facing * 6 * settings.SCALE, self.hitbox.centery - settings.SCALE)

    def sparks(self, count=6, toward_x=None):
        x, y = self.shield_point()
        away = 1 if toward_x is None or toward_x >= self.hitbox.centerx else -1
        for _ in range(count):
            Spark(self.game, (x, y), (away * random.uniform(80, 320), random.uniform(-420, -120)),
                  lifetime=random.uniform(0.25, 0.45))

    def break_shield(self):
        self.game.audio.play(settings.GUARDIAN_SHIELD_BREAK_SOUND)
        self.game.camera.shake(*settings.ENEMY_DEATH_SHAKE)
        x, y = self.shield_point()
        for _ in range(12):
            ShieldShard(self.game, (x + random.uniform(-8, 8), y + random.uniform(-24, 24)),
                        (random.uniform(-260, 260), random.uniform(-520, -160)))
        FloatingText(self.game, "Shield broken!", (self.hitbox.centerx, self.hitbox.top - 30),
                     color=(255, 214, 110))

    @property
    def blocks_arrows(self):
        return self.shield > 0

    def deflect_arrow(self, arrow):
        """While he has his shield, arrows glance off it with a clang."""
        DeathFade(self.game, arrow.image, arrow.rect.topleft, lifetime=0.25)
        self.sparks(4, toward_x=arrow.pos.x)
        self.game.audio.play(settings.GUARDIAN_BLOCK_SOUND)
        FloatingText(self.game, "Blocked", (self.hitbox.centerx, self.hitbox.top - 30),
                     color=(200, 210, 230), lifetime=0.7)

    # ------------------------------------------------------------ combat
    def take_damage(self, amount, source_x):
        """Blade hits (katana / dash): the shield soaks them up first."""
        if self.shield > 0:
            soaked = min(self.shield, amount)
            self.shield -= soaked
            amount -= soaked
            self.flash_timer = settings.HIT_FLASH_TIME
            self.sparks(toward_x=source_x)
            away = 1 if self.hitbox.centerx >= source_x else -1
            self.vel.x = away * settings.GUARDIAN_SHIELD_SHOVE      # barely moves him...
            if self.shield <= 0:
                self.break_shield()
            else:
                self.game.audio.play(settings.GUARDIAN_BLOCK_SOUND)
                self.game.camera.shake(*settings.ENEMY_HIT_SHAKE)
            self.swap_shield_art()
            if amount <= 0:
                return                                           # ...and doesn't stop his attack
        super().take_damage(amount, source_x)

    def on_blast(self, damage, source_x):
        """A bomb goes around the shield: full damage to him."""
        super().take_damage(damage, source_x)

    def try_leap(self, toward_player=True):
        return False                       # far too heavy to jump pits - he waits at the edge

    def die(self):
        self.game.audio.play(settings.GUARDIAN_SHIELD_BREAK_SOUND)
        DeathFade(self.game, self.image, self.rect.topleft, lifetime=0.7)
        self.game.camera.shake(*settings.ENEMY_DEATH_SHAKE)
        self.kill()
