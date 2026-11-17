"""Skeleton: the undead warrior of the ancient caves.

Patrols, spots, chases, jumps pits and cuts with an ancient stone sword exactly
like the samurai (see enemy.py) - but he's frail (SKELETON_MAX_HEALTH) and he
doesn't stay dead:

    dead -> killed: he collapses into a bone pile (skeleton_die sound). Blades
            and arrows pass through the pile. After SKELETON_REVIVE_TIME the
            pile starts to rattle...
    rise -> ...and he pulls himself back together, at full health, and goes
            straight back to hunting the ninja.

A bomb blast is the only way to destroy him for good (standing or as a pile).
"""

from __future__ import annotations

import os
import random
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.effects import DeathFade
from src.sprites.enemy import Enemy
from src.sprites.golem import RockChunk

if TYPE_CHECKING:
    from src.game import Game

SKELETON_DIR = os.path.join(settings.ASSETS_DIR, "enemies", "skeleton")


class BoneChunk(RockChunk):
    COLORS = ((226, 218, 196), (176, 166, 146), (118, 114, 110))


class Skeleton(Enemy):
    ASSET_DIR = SKELETON_DIR
    ANIM_FPS = settings.SKELETON_ANIM_FPS
    PLAY_ONCE = ("attack", "collapse", "rise")
    MODE_ANIM = dict(Enemy.MODE_ANIM, dead="collapse", rise="rise")
    MAX_HEALTH = settings.SKELETON_MAX_HEALTH
    WALK_SPEED = settings.SKELETON_WALK_SPEED
    RUN_SPEED = settings.SKELETON_RUN_SPEED
    SIGHT_RANGE = settings.SKELETON_SIGHT_RANGE
    SPOT_SOUND = None                          # silent... until he falls apart
    ATTACK_ACTIVE_FRAMES = settings.SKELETON_ATTACK_ACTIVE_FRAMES
    BLADE_REACH = settings.SKELETON_SWORD_REACH
    DAMAGE = settings.SKELETON_DAMAGE

    def __init__(self, game: Game, pos):
        super().__init__(game, pos)
        self.revive_timer = 0.0

    # ------------------------------------------------------------ state
    @property
    def down(self):
        return self.mode in ("dead", "rise")

    @property
    def invulnerable(self):
        return self.down                       # blades and arrows pass through the bones

    @property
    def show_health_bar(self):
        return not self.down

    # ------------------------------------------------------------ dying & rising
    def die(self):
        """Killed: collapse into a bone pile instead of disappearing."""
        self.health = 0
        self.vel.x = 0
        self.leaping = False
        self.set_mode("dead", settings.SKELETON_REVIVE_TIME)
        self.animations["collapse"].reset()
        self.game.audio.play(settings.SKELETON_DEATH_SOUND)
        self.game.camera.shake(*settings.ENEMY_HIT_SHAKE)

    def rise(self):
        self.set_mode("rise")
        self.animations["rise"].reset()

    def on_blast(self, damage, source_x):
        """Hit by a bomb: a pile (or a skeleton the blast kills) is blown apart for good."""
        if self.down or self.health <= damage:
            self.shatter()
        else:
            self.take_damage(damage, source_x)

    def shatter(self):
        self.game.audio.play(settings.SKELETON_DEATH_SOUND)
        DeathFade(self.game, self.image, self.rect.topleft, lifetime=0.4)
        for _ in range(14):
            pos = (random.uniform(self.hitbox.left, self.hitbox.right),
                   random.uniform(self.hitbox.centery, self.hitbox.bottom))
            BoneChunk(self.game, pos, (random.uniform(-280, 280), random.uniform(-560, -160)))
        self.game.camera.shake(*settings.ENEMY_DEATH_SHAKE)
        self.kill()

    # ------------------------------------------------------------ brain
    def think(self, dt):
        if self.mode == "dead":
            self.mode_timer -= dt
            if self.mode_timer <= 0:
                self.rise()
        elif self.mode == "rise":
            if self.animations["rise"].finished:
                self.health = self.max_health
                self.flash_timer = 0.0
                self.face_player()
                self.lose_timer = 0.0
                self.set_mode("chase")         # back on his feet - and he remembers you
        else:
            super().think(dt)

    # ------------------------------------------------------------ update
    def update(self):
        super().update()
        if self.alive() and self.mode == "dead" and self.mode_timer < settings.SKELETON_RATTLE_TIME:
            # the bones rattle before he rises
            self.rect.x += random.choice((-1, 0, 1)) * settings.SCALE

    def stand_down_update(self):
        """The ninja is defeated: piles stay piles, the rest stand idle."""
        if self.down:
            self.physics_update()
            return
        super().stand_down_update()

    def cutscene_animate(self, dt):
        if self.down:
            return
        super().cutscene_animate(dt)
