"""The player-controlled ninja."""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames
from src.sprites.effects import Afterimage, SlashStreak
from src.sprites.physics_entity import PhysicsEntity

if TYPE_CHECKING:  # only for type hints, avoids a circular import
    from src.game import Game

JUMP_KEYS = (pygame.K_w, pygame.K_SPACE)
ATTACK_BUTTON = 1   # left mouse button
DASH_BUTTON = 3     # right mouse button


class Player(PhysicsEntity):
    def __init__(self, game: Game, pos):
        super().__init__(game, pos, settings.PLAYER_HITBOX, groups=(game.actors,))

        player_dir = os.path.join(settings.ASSETS_DIR, "player")
        self.animations = {
            name: Animation(
                load_frames(os.path.join(player_dir, name), settings.SCALE),
                fps,
                loop=name not in settings.PLAYER_ANIM_ONCE,
            )
            for name, fps in settings.PLAYER_ANIM_FPS.items()
        }
        self.state = "idle"
        self.spawn_point = pygame.Vector2(pos)

        # input, read once per frame
        self.direction = 0
        self.running = False

        # forgiving jump timing
        self.coyote_timer = 0.0        # can still jump shortly after walking off a ledge
        self.jump_buffer_timer = 0.0   # a jump pressed just before landing still counts

        # double jump
        self.air_jumps_left = settings.AIR_JUMPS
        self.flipping = False          # playing the double-jump somersault

        # katana combo
        self.attacking = False
        self.combo_step = -1           # index into settings.PLAYER_ATTACKS
        self.attack_queued = False     # clicked during a swing -> chain the next one
        self.combo_timer = 0.0         # time left to continue the combo after a swing
        self.lunge_speed = 0.0         # forward push during a swing

        # dash attack
        self.dash_attacking = False    # whole move: dash + finishing cut
        self.dash_timer = 0.0          # > 0 while actually dashing
        self.dash_cooldown = 0.0
        self.air_dash_available = True # one dash per airtime
        self.dash_start_x = 0
        self.ghost_timer = 0.0

        self.image = self.animation.image
        self.align_image()

    @property
    def animation(self) -> Animation:
        return self.animations[self.state]

    # ------------------------------------------------------------ input
    def get_direction(self):
        keys = self.game.keys
        direction = 0
        if keys[pygame.K_a]:
            direction -= 1
        if keys[pygame.K_d]:
            direction += 1
        return direction

    def handle_input(self):
        keys = self.game.keys
        self.direction = self.get_direction()
        self.running = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        # turn first, so pressing a direction + dash/attack together goes that way
        if self.direction != 0 and not (self.attacking or self.dash_attacking):
            self.facing_right = self.direction > 0

        # dash attack
        if DASH_BUTTON in self.game.mouse_just_pressed and self.can_dash():
            self.start_dash()

        # katana combo
        if ATTACK_BUTTON in self.game.mouse_just_pressed and not self.dash_attacking:
            if not self.attacking:
                n = len(settings.PLAYER_ATTACKS)
                self.start_attack((self.combo_step + 1) % n if self.combo_timer > 0 else 0)
            elif self.animation.index >= settings.ATTACK_QUEUE_FROM_FRAME:
                self.attack_queued = True

        if self.dash_attacking:
            facing = 1 if self.facing_right else -1
            if self.dash_timer > 0:
                self.vel.x = facing * settings.DASH_SPEED
                self.vel.y = 0
            else:  # finishing cut: drift forward and slow down
                self.vel.x = facing * self.lunge_speed
                self.lunge_speed *= math.exp(-settings.ATTACK_LUNGE_DECAY * self.game.dt)
        elif self.attacking:
            # committed to the swing: no turning, lunge forward instead of walking
            facing = 1 if self.facing_right else -1
            self.vel.x = facing * self.lunge_speed
            self.lunge_speed *= math.exp(-settings.ATTACK_LUNGE_DECAY * self.game.dt)
        else:
            speed = settings.RUN_SPEED if self.running else settings.WALK_SPEED
            self.vel.x = self.direction * speed

        jump_pressed = any(k in self.game.just_pressed for k in JUMP_KEYS)
        if jump_pressed:
            self.jump_buffer_timer = settings.JUMP_BUFFER_TIME

        if self.jump_buffer_timer > 0 and self.coyote_timer > 0:
            self.jump()
        elif jump_pressed and self.air_jumps_left > 0:
            self.double_jump()

        # releasing jump early = shorter hop
        if any(k in self.game.just_released for k in JUMP_KEYS) and self.vel.y < 0:
            self.vel.y *= settings.JUMP_CUT

    # ------------------------------------------------------------ actions
    def jump(self):
        self.vel.y = -settings.JUMP_SPEED
        self.jump_buffer_timer = 0.0
        self.coyote_timer = 0.0
        self.cancel_attack()           # jumping always takes priority
        self.cancel_dash()

    def double_jump(self):
        self.cancel_attack()
        self.cancel_dash()
        self.vel.y = -settings.DOUBLE_JUMP_SPEED
        self.air_jumps_left -= 1
        self.jump_buffer_timer = 0.0   # don't jump again automatically on landing
        self.flipping = True
        self.state = "flip"
        self.animation.reset()         # restart even if already flipping

    def start_attack(self, step):
        attack = settings.PLAYER_ATTACKS[step]
        self.attacking = True
        self.attack_queued = False
        self.combo_step = step
        self.flipping = False
        self.state = attack["anim"]
        self.animation.reset()
        self.lunge_speed = attack["lunge"]
        self.game.camera.shake(*attack["shake"])

    def cancel_attack(self):
        if self.attacking:
            self.attacking = False
            self.attack_queued = False
            self.lunge_speed = 0.0
            self.combo_timer = 0.0

    def finish_attack(self):
        """Called when a swing's animation ends: chain the next one or stop."""
        if self.attack_queued:
            self.start_attack((self.combo_step + 1) % len(settings.PLAYER_ATTACKS))
        else:
            self.attacking = False
            self.lunge_speed = 0.0
            self.combo_timer = settings.COMBO_WINDOW

    # ------------------------------------------------------------ dash attack
    def can_dash(self):
        return (not self.dash_attacking and self.dash_cooldown <= 0
                and (self.on_ground or self.air_dash_available))

    def start_dash(self):
        self.cancel_attack()
        self.flipping = False
        if not self.on_ground:
            self.air_dash_available = False
        self.dash_attacking = True
        self.dash_timer = settings.DASH_TIME
        self.dash_cooldown = settings.DASH_COOLDOWN
        self.gravity_enabled = False          # dash in a straight line, even in the air
        self.vel.y = 0
        self.dash_start_x = self.hitbox.centerx
        self.ghost_timer = 0.0                # first afterimage right away
        self.state = "dash"
        self.animation.reset()
        self.game.camera.shake(*settings.DASH_SHAKE)

    def end_dash_movement(self, hit_wall=False):
        """Dash distance covered (or a wall reached): flash the cut along the path."""
        self.dash_timer = 0.0
        self.gravity_enabled = True
        self.lunge_speed = 0.0 if hit_wall else settings.DASH_RECOVERY_SPEED
        chest_y = self.hitbox.top + round(self.hitbox.height * 0.45)
        SlashStreak(self.game, self.dash_start_x, self.hitbox.centerx, chest_y)

    def cancel_dash(self):
        if self.dash_attacking:
            self.dash_attacking = False
            self.dash_timer = 0.0
            self.gravity_enabled = True
            self.lunge_speed = 0.0

    def spawn_afterimages(self, dt):
        if not (self.dash_attacking and self.dash_timer > 0):
            return
        self.ghost_timer -= dt
        if self.ghost_timer <= 0:
            Afterimage(self.game, self.image, self.rect.topleft)
            self.ghost_timer += settings.GHOST_INTERVAL

    # ------------------------------------------------------------ hit areas
    @property
    def attack_hitbox(self):
        """Area the blade covers right now, else None.
        Enemies can check `enemy.hitbox.colliderect(player.attack_hitbox)`."""
        if self.dash_attacking:
            # everything along the dash path, while dashing and on the finishing cut
            if self.dash_timer > 0 or self.animation.index == len(self.animation.frames) - 1:
                front = self.hitbox.right if self.facing_right else self.hitbox.left
                x0, x1 = sorted((self.dash_start_x, front))
                return pygame.Rect(x0, self.hitbox.top, max(1, x1 - x0), self.hitbox.height)
            return None
        if not self.attacking or self.animation.index not in settings.ATTACK_ACTIVE_FRAMES:
            return None
        w, h = 12 * settings.SCALE, 16 * settings.SCALE
        rect = pygame.Rect(0, 0, w, h)
        rect.bottom = self.hitbox.bottom
        if self.facing_right:
            rect.left = self.hitbox.centerx
        else:
            rect.right = self.hitbox.centerx
        return rect

    # ------------------------------------------------------------ animation
    def set_state(self, new_state):
        if new_state != self.state:
            self.state = new_state
            self.animation.reset()

    def choose_state(self):
        if self.dash_attacking:
            return "dash"
        if self.attacking:
            return self.state          # the current attack animation
        if self.flipping:
            if self.on_ground or self.animations["flip"].finished:
                self.flipping = False
            else:
                return "flip"
        if not self.on_ground:
            return "jump" if self.vel.y < 0 else "fall"
        if self.direction == 0:
            return "idle"
        return "run" if self.running else "walk"

    # ------------------------------------------------------------ update
    def update(self):
        dt = self.game.dt
        self.coyote_timer = settings.COYOTE_TIME if self.on_ground else max(0.0, self.coyote_timer - dt)
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)

        self.handle_input()
        self.physics_update()
        if self.on_ground:
            self.air_jumps_left = settings.AIR_JUMPS
            self.air_dash_available = True

        if self.dash_attacking and self.dash_timer > 0:
            self.dash_timer -= dt
            hit_wall = self.collisions["left"] or self.collisions["right"]
            if self.dash_timer <= 0 or hit_wall:
                self.end_dash_movement(hit_wall)

        self.set_state(self.choose_state())
        self.animation.update(dt)
        if self.attacking and self.animation.finished:
            self.finish_attack()
            self.set_state(self.choose_state())
        if self.dash_attacking and self.dash_timer <= 0 and self.animation.finished:
            self.dash_attacking = False
            self.lunge_speed = 0.0
            self.set_state(self.choose_state())
        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        self.align_image()
        self.spawn_afterimages(dt)

    def on_fell_out_of_map(self):
        """Respawn instead of disappearing."""
        self.pos.update(self.spawn_point)
        self.vel.update(0, 0)
        self.hitbox.midbottom = (round(self.pos.x), round(self.pos.y))
        self.flipping = False
        self.cancel_attack()
        self.cancel_dash()
        self.game.camera.snap()
