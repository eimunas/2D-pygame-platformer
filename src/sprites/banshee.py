"""Banshee: a gaunt grey-skinned woman with long, messy black hair who walks
slowly towards the ninja and attacks by SCREAMING at him.

Modes (patrol + hurt work like the samurai's, see enemy.py):
    patrol_walk / patrol_idle -> shuffles about slowly, looking for him
    alert   -> spotted: a short, silent pause -> chase
    chase   -> walks slowly towards him (she's much slower than you)...
    watch   -> ...and stands still once she's BANSHEE_KEEP_DISTANCE away (or at
               a ledge). In either mode, when her scream is ready and he's in
               range (and in sight) -> windup
    windup  -> arms rise, eyes flare: the warning - dash or get out of range!
    scream  -> a sound wave flies at him (ScreamWave). If it hits: damage, he's
               pushed back, and STUNNED for BANSHEE_STUN_TIME (no running,
               jumping, dashing or attacking - see Player.stun)
    recover -> short pause, then chase again

Dashing through the wave avoids it (the ninja is invulnerable while dashing).
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.effects import DeathFade
from src.sprites.enemy import Enemy

if TYPE_CHECKING:
    from src.game import Game

BANSHEE_DIR = os.path.join(settings.ASSETS_DIR, "enemies", "banshee")


WAVE_COLOR = (170, 255, 226)


class Banshee(Enemy):
    ASSET_DIR = BANSHEE_DIR
    ANIM_FPS = settings.BANSHEE_ANIM_FPS
    PLAY_ONCE = ("windup",)
    MODE_ANIM = {"patrol_walk": "walk", "patrol_idle": "idle", "alert": "idle", "chase": "walk",
                 "watch": "idle", "windup": "windup", "scream": "scream", "recover": "idle",
                 "hurt": "idle"}
    HITBOX = settings.BANSHEE_HITBOX
    MAX_HEALTH = settings.BANSHEE_MAX_HEALTH
    SIGHT_RANGE = settings.BANSHEE_SIGHT_RANGE
    SIGHT_HEIGHT = settings.BANSHEE_SIGHT_HEIGHT
    SPOT_SOUND = None
    ALERT_TIME = 0.3
    DAMAGE = settings.BANSHEE_DAMAGE

    def __init__(self, game: Game, pos):
        super().__init__(game, pos)
        self.scream_cooldown = 0.8

    # ------------------------------------------------------------ brain
    def think(self, dt):
        self.mode_timer -= dt
        self.scream_cooldown = max(0.0, self.scream_cooldown - dt)
        mode = self.mode
        dx, dy = self.player_offset()

        if mode in ("patrol_walk", "patrol_idle"):
            self.think_patrol()
        elif mode == "alert":
            if self.mode_timer <= 0:
                self.set_mode("chase")
        elif mode in ("chase", "watch"):
            self.face_player()
            far = abs(dx) > settings.BANSHEE_LOSE_RANGE or abs(dy) > 4 * settings.TILE_SIZE
            self.lose_timer = self.lose_timer + dt if far else 0.0
            if self.lose_timer > settings.SAMURAI_LOSE_TIME:
                self.start_patrol_idle()
            elif (self.scream_cooldown <= 0 and abs(dx) <= settings.BANSHEE_SCREAM_RANGE * 0.85
                  and abs(dy) < 2 * settings.TILE_SIZE and not self.game.player.dead
                  and self.line_of_sight()):
                self.set_mode("windup", settings.BANSHEE_WINDUP_TIME)
                self.animations["windup"].reset()
            else:                              # walk closer, or stand and stare
                close = abs(dx) <= settings.BANSHEE_KEEP_DISTANCE
                self.mode = "watch" if close or self.dangerous_drop_ahead() else "chase"
        elif mode == "windup":
            self.face_player()
            if self.mode_timer <= 0:
                self.scream()
        elif mode == "scream":
            if self.mode_timer <= 0:
                self.set_mode("recover", settings.BANSHEE_RECOVER_TIME)
        elif mode in ("recover", "hurt"):
            if self.mode_timer <= 0:
                self.face_player()
                self.lose_timer = 0.0
                self.set_mode("chase")

    def move_intent(self):
        if self.mode == "hurt":
            return None                        # slide from the knockback
        facing = 1 if self.facing_right else -1
        if self.mode == "patrol_walk":
            return facing * settings.BANSHEE_PATROL_SPEED
        if self.mode == "chase" and not self.dangerous_drop_ahead():
            return facing * settings.BANSHEE_WALK_SPEED
        return 0

    def scream(self):
        self.set_mode("scream", settings.BANSHEE_SCREAM_TIME)
        self.animations["scream"].reset()
        self.scream_cooldown = settings.BANSHEE_SCREAM_COOLDOWN
        facing = 1 if self.facing_right else -1
        mouth = pygame.Vector2(self.hitbox.centerx + facing * 4 * settings.SCALE,
                               self.hitbox.top + 4 * settings.SCALE)
        aim = pygame.Vector2(self.game.player.hitbox.center) - mouth
        if aim.length_squared() == 0 or (aim.x > 0) != (facing > 0):
            aim = pygame.Vector2(facing, 0)
        aim = aim.normalize()
        aim.y = max(-0.57, min(0.57, aim.y))  # a mostly horizontal blast (<= ~35 degrees)
        ScreamWave(self.game, mouth, aim.normalize())
        self.game.audio.play(settings.BANSHEE_SCREAM_SOUND)
        self.game.camera.shake(2, 0.3)

    # ------------------------------------------------------------ combat
    def die(self):
        self.game.audio.play(settings.BANSHEE_DEATH_SOUND)
        DeathFade(self.game, self.image, self.rect.topleft, lifetime=0.8)
        self.game.camera.shake(*settings.ENEMY_DEATH_SHAKE)
        self.kill()


class ScreamWave(pygame.sprite.Sprite):
    """The banshee's scream: rings of sound that grow as they fly. Stops at rock,
    fades out at BANSHEE_SCREAM_RANGE. Hitting the ninja: damage + push + stun."""

    def __init__(self, game: Game, pos, direction):
        super().__init__(game.all_sprites, game.projectiles)
        self.game = game
        self.pos = pygame.Vector2(pos)
        self.dir = pygame.Vector2(direction)
        self.travelled = 0.0
        self.angle = math.degrees(math.atan2(-self.dir.y, self.dir.x))
        self.redraw()

    @property
    def progress(self):
        return min(1.0, self.travelled / settings.BANSHEE_SCREAM_RANGE)

    @property
    def radius(self):
        return 22 + 30 * self.progress                 # px, grows as it spreads

    def redraw(self):
        r = self.radius / settings.SCALE              # draw at art resolution, scale up
        size = int(r * 2) + 4
        art = pygame.Surface((size, size), pygame.SRCALPHA)
        c = size / 2
        fade = 1 - max(0.0, (self.progress - 0.6) / 0.4)
        glow = pygame.Rect(0, 0, r * 2, r * 2)
        glow.center = (c, c)
        pygame.draw.ellipse(art, (*WAVE_COLOR, round(40 * fade)), glow)      # faint haze
        for k, frac in enumerate((1.0, 0.75, 0.5)):
            rr = max(1, r * frac)
            box = pygame.Rect(0, 0, rr * 2, rr * 2)
            box.center = (c, c)
            alpha = round((255 - k * 45) * fade)
            pygame.draw.arc(art, (*WAVE_COLOR, alpha), box, -1.0, 1.0, 1)
        art = pygame.transform.rotate(art, self.angle)
        self.image = pygame.transform.scale_by(art, settings.SCALE)
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))

    def update(self):
        dt = self.game.dt
        step = settings.BANSHEE_SCREAM_SPEED * dt
        self.pos += self.dir * step
        self.travelled += step
        tm = self.game.tilemap
        if self.travelled >= settings.BANSHEE_SCREAM_RANGE or tm.is_solid(*tm.world_to_grid(*self.pos)):
            self.kill()
            return
        self.redraw()

        player = self.game.player
        r = self.radius
        front = pygame.Rect(0, 0, max(8, r * 0.8), r * 2)
        front.center = (round(self.pos.x + self.dir.x * r * 0.6), round(self.pos.y + self.dir.y * r * 0.6))
        if not player.dead and front.colliderect(player.hitbox):
            source_x = self.pos.x - math.copysign(100, self.dir.x or 1)
            if player.take_damage(settings.BANSHEE_DAMAGE, source_x):
                push = math.copysign(settings.BANSHEE_PUSH[0], self.dir.x or 1)
                player.vel.update(push, -settings.BANSHEE_PUSH[1])
                player.stun(settings.BANSHEE_STUN_TIME)
                self.kill()
            # ignored (dashing / still blinking from a hit): the wave passes through


class StunMark(pygame.sprite.Sprite):
    """Pale wisps circling above the stunned ninja's head (until the stun ends)."""

    def __init__(self, game: Game, player):
        super().__init__(game.all_sprites, game.effects_front)
        self.game = game
        self.player = player
        self.time = 0.0
        self.update()

    def update(self):
        p = self.player
        if p.stun_timer <= 0 or p.dead or not p.alive():
            self.kill()
            return
        self.time += self.game.dt
        w, h = 9, 4                                    # art px
        art = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        for k in range(3):
            a = self.time * 7 + k * 2 * math.pi / 3
            x = (w / 2) + math.cos(a) * w / 2
            y = (h / 2) + math.sin(a) * h / 2
            front = math.sin(a) > 0
            color = (*WAVE_COLOR, 255 if front else 140)
            art.set_at((round(x), round(y)), color)
            art.set_at((round(x) + 1, round(y)), color)
        self.image = pygame.transform.scale_by(art, settings.SCALE)
        self.rect = self.image.get_rect(midbottom=(p.hitbox.centerx, p.hitbox.top - 2))
