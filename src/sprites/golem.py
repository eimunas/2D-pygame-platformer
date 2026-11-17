"""Stone golem: the mini-boss guarding the ancient caves.

It's created by the boss cutscene (src/boss.py), which drops it from the sky
and switches its AI on (`active = True`) once the scene ends.

Modes:
    idle / walk -> lumbers towards the ninja (slowly; heavy footsteps shake the
                   screen a little); stays inside its arena (`bounds`)
    attack      -> raises both fists overhead (the warning), then slams them
                   into the ground in front of him: big damage on frames 3-4
    recover     -> short pause after a slam
    (every BOSS_LAUGH_INTERVAL s, at random, he laughs - in any mode)
    crouch      -> every GOLEM_JUMP_COOLDOWN s: gathers himself, a red marker
                   shows where he'll come down...
    air         -> ...leaps high and comes down on that spot
    land        -> landing: big screen shake; the ninja takes big damage if he's
                   under him or on the ground within the shockwave. The golem
                   then stands still for a moment - your chance to strike.

He doesn't flinch or get knocked back when hit. Defeating him calls
game.on_boss_defeated() (opens the cave).
"""

from __future__ import annotations

import math
import os
import random
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.effects import DeathFade, Effect
from src.sprites.enemy import Enemy

if TYPE_CHECKING:
    from src.game import Game

GOLEM_DIR = os.path.join(settings.ASSETS_DIR, "enemies", "golem")


class Golem(Enemy):
    ASSET_DIR = GOLEM_DIR
    ANIM_FPS = settings.GOLEM_ANIM_FPS
    PLAY_ONCE = ("attack", "crouch", "land")
    MODE_ANIM = {
        "idle": "idle", "walk": "walk", "attack": "attack", "recover": "idle",
        "crouch": "crouch", "air": "air", "land": "land",
    }
    HITBOX = settings.GOLEM_HITBOX
    MAX_HEALTH = settings.GOLEM_MAX_HEALTH
    ATTACK_ACTIVE_FRAMES = settings.GOLEM_ATTACK_ACTIVE_FRAMES
    DAMAGE = settings.GOLEM_FIST_DAMAGE
    BOSS = True                                # big health bar instead of the small one
    FOOTSTEP_FRAMES = (0, 4)                   # "walk" frames where a foot hits the ground

    def __init__(self, game: Game, pos):
        super().__init__(game, pos)
        self.facing_right = False
        self.mode, self.mode_timer = "idle", 0.0
        self.active = False                    # AI off until the cutscene ends
        self.home_x = pos[0]
        self.bounds = (pos[0] - settings.GOLEM_LEASH, pos[0] + settings.GOLEM_LEASH)
        self.jump_cooldown = settings.GOLEM_FIRST_JUMP_DELAY
        self.jump_vx = 0.0
        self.air_time = 0.0
        self.marker = None
        self.slam_done = False                 # this attack's fists already hit the ground
        self.step_frame = -1                   # last walk frame a footstep played on
        self.laugh_timer = random.uniform(*settings.BOSS_LAUGH_INTERVAL)
        game.boss = self

    # ------------------------------------------------------------ helpers
    def gap_to_player(self):
        dx, dy = self.player_offset()
        return abs(dx) - (self.hitbox.width + self.game.player.hitbox.width) / 2, dy

    def can_walk(self):
        facing = 1 if self.facing_right else -1
        next_x = self.hitbox.centerx + facing * self.hitbox.width / 2
        lo, hi = self.bounds
        return lo <= next_x <= hi and not self.dangerous_drop_ahead()

    def ground_under(self, x):
        """Top (px) of solid ground wide enough for him around x, near his own
        level - or None (a pit, or too high/low)."""
        tm, ts = self.game.tilemap, self.game.tilemap.tile_size
        _, feet_row = tm.world_to_grid(self.hitbox.centerx, self.hitbox.bottom - 1)
        half = self.hitbox.width // 2 - 4
        for row in range(feet_row - 2, feet_row + 4):
            cols = {tm.world_to_grid(x + dx, 0)[0] for dx in (-half, 0, half)}
            if all(tm.is_solid(c, row) and not tm.is_solid(c, row - 1) for c in cols):
                return row * ts
        return None

    def play_anim(self, name, dt):
        """Cutscene control: show an animation, no AI or physics."""
        if name != self.anim_name:
            self.anim_name = name
            self.animation.reset()
        self.animation.update(dt)
        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        self.align_image()

    # ------------------------------------------------------------ actions
    def start_attack(self):
        self.set_mode("attack")
        self.attack_landed = False
        self.slam_done = False
        self.animations["attack"].reset()

    def start_jump(self):
        """Crouch, then leap onto where the ninja is now. False if there's no safe
        ground to land on there."""
        lo, hi = self.bounds
        target_x = max(lo, min(hi, self.game.player.hitbox.centerx))
        ground = self.ground_under(target_x)
        if ground is None:
            self.jump_cooldown = 1.0           # try again in a moment
            return False
        v, g = settings.GOLEM_JUMP_SPEED, self.gravity
        rise = self.hitbox.bottom - ground
        if v * v < 2 * g * rise:
            self.jump_cooldown = 1.0
            return False
        airtime = (v + math.sqrt(v * v - 2 * g * rise)) / g
        cap = settings.GOLEM_JUMP_MAX_SPEED_X
        self.jump_vx = max(-cap, min(cap, (target_x - self.hitbox.centerx) / airtime))
        if abs(target_x - self.hitbox.centerx) > 4:
            self.facing_right = target_x > self.hitbox.centerx
        self.set_mode("crouch", settings.GOLEM_CROUCH_TIME)
        self.animations["crouch"].reset()
        land_x = self.hitbox.centerx + self.jump_vx * airtime
        self.marker = LandingMarker(self.game, self, (land_x, ground))
        return True

    def take_off(self):
        self.vel.y = -settings.GOLEM_JUMP_SPEED
        self.air_time = 0.0
        self.jump_cooldown = settings.GOLEM_JUMP_COOLDOWN
        self.set_mode("air")
        self.game.audio.play("jump", volume=0.5)

    def land(self):
        """Came down from the jump attack: shockwave + screen shake."""
        self.vel.x = 0
        self.set_mode("land", settings.GOLEM_LAND_RECOVER)
        self.animations["land"].reset()
        self.game.camera.shake(*settings.GOLEM_LAND_SHAKE)
        self.game.audio.play(settings.BOSS_CUTSCENE_LAND_SOUND, volume=0.8)
        dust_burst(self.game, self.hitbox.centerx, self.hitbox.bottom, self.hitbox.width)
        if self.marker:
            self.marker.kill()
            self.marker = None
        player = self.game.player
        wave = self.hitbox.inflate(2 * settings.GOLEM_SHOCKWAVE, 0)
        on_ground_level = player.hitbox.bottom >= self.hitbox.bottom - settings.TILE_SIZE // 2
        if player.hitbox.colliderect(self.hitbox) or (on_ground_level and player.hitbox.colliderect(wave)):
            player.take_damage(settings.GOLEM_LANDING_DAMAGE, self.hitbox.centerx)

    def slam(self):
        """Fists hit the ground (the attack's first active frame)."""
        self.slam_done = True
        self.game.camera.shake(*settings.GOLEM_SLAM_SHAKE)
        self.game.audio.play(settings.BOSS_FOOTSTEP_SOUND)
        hb = self.attack_hitbox
        if hb:
            dust_burst(self.game, hb.centerx, self.hitbox.bottom, hb.width // 2, chunks=3)

    def footstep(self):
        self.game.audio.play(settings.BOSS_FOOTSTEP_SOUND)
        self.game.camera.shake(*settings.GOLEM_STEP_SHAKE)

    # ------------------------------------------------------------ brain
    def think(self, dt):
        if not self.active:
            return
        self.mode_timer -= dt
        self.jump_cooldown = max(0.0, self.jump_cooldown - dt)
        mode = self.mode
        player = self.game.player

        self.laugh_timer -= dt
        if self.laugh_timer <= 0 and not player.dead:
            self.game.audio.play(settings.BOSS_LAUGH_SOUND)
            self.laugh_timer = random.uniform(*settings.BOSS_LAUGH_INTERVAL)

        if mode in ("idle", "walk"):
            self.face_player()
            gap, dy = self.gap_to_player()
            if self.jump_cooldown <= 0 and self.on_ground and not player.dead and self.start_jump():
                return
            if gap <= settings.GOLEM_ATTACK_RANGE and abs(dy) < self.hitbox.height:
                self.start_attack()
                return
            self.mode = "walk" if self.can_walk() else "idle"

        elif mode == "attack":
            anim = self.animations["attack"]
            if not self.slam_done and anim.index >= self.ATTACK_ACTIVE_FRAMES[0]:
                self.slam()
            if anim.finished:
                self.set_mode("recover", settings.GOLEM_ATTACK_COOLDOWN)

        elif mode == "recover":
            if self.mode_timer <= 0:
                self.set_mode("walk")

        elif mode == "crouch":
            if self.mode_timer <= 0:
                self.take_off()

        elif mode == "land":
            if self.mode_timer <= 0:
                self.set_mode("walk")

    def move_intent(self):
        facing = 1 if self.facing_right else -1
        if self.mode == "walk":
            return facing * settings.GOLEM_WALK_SPEED
        if self.mode == "air":
            return self.jump_vx
        return 0

    # ------------------------------------------------------------ combat
    @property
    def attack_hitbox(self):
        if self.mode != "attack" or self.animation.index not in self.ATTACK_ACTIVE_FRAMES:
            return None
        rect = pygame.Rect(0, 0, settings.GOLEM_FIST_REACH * settings.SCALE, 20 * settings.SCALE)
        rect.bottom = self.hitbox.bottom
        if self.facing_right:
            rect.left = self.hitbox.centerx
        else:
            rect.right = self.hitbox.centerx
        return rect

    def take_damage(self, amount, source_x):
        """No knockback, no flinching - he just flashes and keeps coming."""
        if not self.active:
            return
        self.health -= amount
        self.flash_timer = settings.HIT_FLASH_TIME
        self.game.audio.play("hit_hurt")
        if self.health <= 0:
            self.die()

    def die(self):
        DeathFade(self.game, self.image, self.rect.topleft, lifetime=1.2)
        for _ in range(26):                    # he crumbles into rubble
            x = random.uniform(self.hitbox.left, self.hitbox.right)
            y = random.uniform(self.hitbox.top, self.hitbox.bottom)
            RockChunk(self.game, (x, y), (random.uniform(-260, 260), random.uniform(-620, -120)))
        dust_burst(self.game, self.hitbox.centerx, self.hitbox.bottom, self.hitbox.width * 1.5)
        self.game.camera.shake(*settings.GOLEM_DEATH_SHAKE)
        self.game.audio.play(settings.BOSS_CUTSCENE_LAND_SOUND)
        if self.marker:
            self.marker.kill()
        self.kill()
        self.game.on_boss_defeated()

    # ------------------------------------------------------------ update
    def update(self):
        super().update()                       # think -> move -> physics -> animation
        if not self.alive():
            return
        if self.mode == "air":
            self.air_time += self.game.dt
            if self.on_ground and self.air_time > 0.1:
                self.land()
        if self.mode == "walk" and self.anim_name == "walk":
            index = self.animation.index
            if index in self.FOOTSTEP_FRAMES and index != self.step_frame:
                self.footstep()
            self.step_frame = index
        else:
            self.step_frame = -1


# ====================================================================== effects
class LandingMarker(pygame.sprite.Sprite):
    """A red shadow on the ground where the jumping golem will come down; it
    grows and darkens as he falls."""

    def __init__(self, game: Game, golem, ground_pos):
        super().__init__(game.all_sprites, game.effects_back)
        self.game = game
        self.golem = golem
        self.x, self.ground_y = ground_pos
        self.time = 0.0
        self.update()

    def update(self):
        golem = self.golem
        if not golem.alive() or golem.mode not in ("crouch", "air"):
            self.kill()
            return
        self.time += self.game.dt
        height = max(0.0, self.ground_y - golem.hitbox.bottom)
        closeness = 1 - min(1.0, height / (6 * settings.TILE_SIZE))      # 0 far above -> 1 landing
        w = round(golem.hitbox.width * (0.7 + 0.8 * closeness) + 2 * settings.GOLEM_SHOCKWAVE * closeness)
        h = max(8, w // 6)
        pulse = 0.75 + 0.25 * math.sin(self.time * 14)
        self.image = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(self.image, (140, 16, 24, round((90 + 100 * closeness) * pulse)), self.image.get_rect())
        pygame.draw.ellipse(self.image, (255, 90, 80, round(255 * pulse)), self.image.get_rect(), 3)
        self.rect = self.image.get_rect(center=(round(self.x), round(self.ground_y)))


class RockChunk(pygame.sprite.Sprite):
    """A bit of stone thrown up by an impact: flies, falls, fades."""

    COLORS = ((116, 110, 106), (80, 76, 80), (70, 112, 58))

    def __init__(self, game: Game, pos, vel, lifetime=1.1):
        super().__init__(game.all_sprites, game.effects_front)
        self.game = game
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.age, self.lifetime = 0.0, lifetime
        size = random.choice((1, 2, 2, 3)) * settings.SCALE
        self.base = pygame.Surface((size, size), pygame.SRCALPHA)
        self.base.fill(random.choice(self.COLORS))
        pygame.draw.rect(self.base, (22, 18, 26), self.base.get_rect(), 1 if size > 4 else 0)
        self.image = self.base
        self.rect = self.image.get_rect(center=self.pos)

    def update(self):
        dt = self.game.dt
        self.age += dt
        if self.age >= self.lifetime:
            self.kill()
            return
        self.vel.y += settings.GRAVITY * dt
        self.pos += self.vel * dt
        self.image = self.base.copy()
        self.image.set_alpha(round(255 * min(1.0, (self.lifetime - self.age) / 0.3)))
        self.rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))


class DustPuff(Effect):
    """A soft grey cloud that swells and drifts sideways along the ground."""

    def __init__(self, game: Game, pos, drift, size, lifetime=0.8):
        super().__init__(game, game.effects_front, lifetime, start_alpha=170)
        self.pos = pygame.Vector2(pos)
        self.drift = drift
        self.size = size
        self.animate()

    def animate(self):
        t = self.progress
        self.pos.x += self.drift * self.game.dt * (1 - t)
        r = max(2, round(self.size * (0.5 + 0.8 * t) / settings.SCALE))
        art = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(art, (150, 146, 140), (r + 1, r + 1), r)
        pygame.draw.circle(art, (182, 178, 170), (r, r), max(1, r - 2))
        self.image = pygame.transform.scale_by(art, settings.SCALE)
        self.rect = self.image.get_rect(midbottom=(round(self.pos.x), round(self.pos.y + 4)))


def dust_burst(game: Game, x, ground_y, width, chunks=8):
    """Dust clouds rolling out to both sides + a few rock chunks: for impacts."""
    for side in (-1, 1):
        for k in range(3):
            DustPuff(game, (x + side * (width / 2) * (0.3 + 0.35 * k), ground_y),
                     side * random.uniform(120, 260), random.uniform(28, 44),
                     lifetime=random.uniform(0.6, 0.9))
    for _ in range(chunks):
        RockChunk(game, (x + random.uniform(-width / 2, width / 2), ground_y - 6),
                  (random.uniform(-300, 300), random.uniform(-520, -200)), lifetime=0.8)
