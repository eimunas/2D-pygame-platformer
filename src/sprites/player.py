"""The player-controlled ninja."""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import Animation, load_frames
from src.sprites.bomb import Bomb
from src.sprites.effects import Afterimage, BloodDrop, BloodPool, SlashStreak, blood_spray
from src.sprites.physics_entity import PhysicsEntity
from src.sprites.projectile import Arrow

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
        self.attack_id = 0             # +1 per swing/dash, so each one hits an enemy once

        # weapon: "katana" (LMB combo) or "bow" (LMB shoots) - switched with the mouse wheel
        self.weapon = game.equipped_weapon()
        self.shooting = False          # playing the bow animation
        self.arrow_fired = False
        self.bow_cooldown = 0.0
        self.throwing = False          # playing the bomb-throw swing (no blade damage)
        self.throw_cooldown = 0.0

        # dash attack
        self.dash_attacking = False    # whole move: dash + finishing cut
        self.dash_timer = 0.0          # > 0 while actually dashing
        self.dash_cooldown = 0.0
        self.air_dash_available = True # one dash per airtime
        self.dash_start_x = 0
        self.ghost_timer = 0.0

        # health
        self.max_health = settings.PLAYER_MAX_HEALTH
        self.health = self.max_health
        self.invuln_timer = 0.0        # > 0: can't be hurt (blinking)
        self.hurt_timer = 0.0          # > 0: knocked back, no control
        self.stun_timer = 0.0          # > 0: stunned (banshee scream): only slow walking

        # death (see die / update_dead)
        self.dead = False
        self.drip_timer = 0.0
        self.lying_time = 0.0          # seconds he's been lying on the ground
        self.blood_pool = None

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
        if self.hurt_timer > 0:       # knocked back: no control, keep the knockback
            self.direction = 0
            self.drop_through = False
            return
        keys = self.game.keys
        stunned = self.stun_timer > 0            # no running, jumping, dashing or attacking
        clicks = set() if stunned else self.game.mouse_just_pressed
        self.direction = self.get_direction()
        self.running = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and not stunned
        self.drop_through = keys[pygame.K_s]     # hold S to drop through bridges

        # turn first, so pressing a direction + dash/attack together goes that way
        if self.direction != 0 and not (self.attacking or self.dash_attacking):
            self.facing_right = self.direction > 0

        # dash attack
        if DASH_BUTTON in clicks and self.can_dash():
            self.start_dash()

        # bow: left click shoots
        if self.weapon == "bow":
            if ATTACK_BUTTON in clicks and self.can_shoot():
                self.start_shot()
        # bomb: left click throws it (one use)
        elif self.weapon == "bomb":
            if ATTACK_BUTTON in clicks and self.can_throw():
                self.throw_bomb()
        # katana combo
        elif ATTACK_BUTTON in clicks and not self.dash_attacking:
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
        elif self.shooting:
            self.vel.x = 0                 # plant your feet to shoot (you still fall)
        elif self.attacking:
            # committed to the swing: no turning, lunge forward instead of walking
            facing = 1 if self.facing_right else -1
            self.vel.x = facing * self.lunge_speed
            self.lunge_speed *= math.exp(-settings.ATTACK_LUNGE_DECAY * self.game.dt)
        else:
            speed = settings.RUN_SPEED if self.running else settings.WALK_SPEED
            if stunned:
                speed *= settings.STUN_WALK_FACTOR      # dazed: a slow stagger
            self.vel.x = self.direction * speed

        jump_pressed = not stunned and any(k in self.game.just_pressed for k in JUMP_KEYS)
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
        self.game.audio.play("jump")
        self.vel.y = -settings.JUMP_SPEED
        self.jump_buffer_timer = 0.0
        self.coyote_timer = 0.0
        self.cancel_attack()           # jumping always takes priority
        self.cancel_dash()
        self.cancel_shot()

    def double_jump(self):
        self.game.audio.play("jump")
        self.cancel_attack()
        self.cancel_dash()
        self.cancel_shot()
        self.vel.y = -settings.DOUBLE_JUMP_SPEED
        self.air_jumps_left -= 1
        self.jump_buffer_timer = 0.0   # don't jump again automatically on landing
        self.flipping = True
        self.state = "flip"
        self.animation.reset()         # restart even if already flipping

    def start_attack(self, step):
        attack = settings.PLAYER_ATTACKS[step]
        self.throwing = False              # a katana cut right after the last bomb's throw
        self.attacking = True
        self.attack_queued = False
        self.combo_step = step
        self.flipping = False
        self.state = attack["anim"]
        self.animation.reset()
        self.lunge_speed = attack["lunge"]
        self.attack_id += 1
        self.game.camera.shake(*attack["shake"])
        self.game.audio.play("attack")

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

    # ------------------------------------------------------------ bow
    def can_shoot(self):
        return not (self.shooting or self.dash_attacking) and self.bow_cooldown <= 0

    def start_shot(self):
        self.shooting = True
        self.arrow_fired = False
        self.flipping = False
        self.state = "bow"
        self.animation.reset()

    def fire_arrow(self):
        facing = 1 if self.facing_right else -1
        start = (self.hitbox.centerx + facing * 5 * settings.SCALE, self.hitbox.top + 6 * settings.SCALE)
        Arrow(self.game, start, (facing * settings.PLAYER_ARROW_SPEED, -settings.PLAYER_ARROW_LIFT),
              damage=settings.PLAYER_ARROW_DAMAGE, friendly=True, gravity=settings.PLAYER_ARROW_GRAVITY)
        self.arrow_fired = True
        self.game.audio.play("arrow")

    def cancel_shot(self):
        """Stop a bow shot or a bomb-throw swing (the bomb itself is already flying)."""
        self.shooting = False
        self.throwing = False

    # ------------------------------------------------------------ bomb
    def can_throw(self):
        return (not (self.shooting or self.dash_attacking or self.throwing)
                and self.throw_cooldown <= 0 and self.game.progress.item_count("bomb") > 0)

    def throw_bomb(self):
        facing = 1 if self.facing_right else -1
        fx, up = settings.BOMB_THROW_SPEED
        start = (self.hitbox.centerx + facing * 4 * settings.SCALE, self.hitbox.top + 5 * settings.SCALE)
        Bomb(self.game, start, (facing * fx + self.vel.x * 0.3, -up))
        self.game.audio.play("attack", volume=0.6)
        if self.game.progress.use_item("bomb") == 0:
            self.game.on_weapon_used_up()          # back to the katana (before the swing starts)
        self.throwing = True
        self.flipping = False
        self.state = "attack1"                     # the cut animation doubles as a throw
        self.animation.reset()
        self.throw_cooldown = settings.BOMB_THROW_COOLDOWN
    def set_weapon(self, weapon_id):
        """Switch weapons (from the weapon bar): stops whatever attack is going on."""
        if weapon_id != self.weapon:
            self.cancel_attack()
            self.cancel_shot()
            self.combo_timer = 0.0
            self.weapon = weapon_id

    # ------------------------------------------------------------ dash attack
    def can_dash(self):
        return (not self.dash_attacking and self.dash_cooldown <= 0
                and (self.on_ground or self.air_dash_available))

    def start_dash(self):
        self.cancel_attack()
        self.cancel_shot()
        self.flipping = False
        if not self.on_ground:
            self.air_dash_available = False
        self.dash_attacking = True
        self.dash_timer = settings.DASH_TIME
        self.dash_cooldown = settings.DASH_COOLDOWN
        self.gravity_enabled = False          # dash in a straight line, even in the air
        self.vel.y = 0
        self.dash_start_x = self.hitbox.centerx
        self.attack_id += 1
        self.ghost_timer = 0.0                # first afterimage right away
        self.state = "dash"
        self.animation.reset()
        self.game.camera.shake(*settings.DASH_SHAKE)
        self.game.audio.play("dash_attack")

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

    def stun(self, duration):
        """Dazed (the banshee's scream): for `duration` s he can only walk, slowly -
        no running, jumping, dashing or attacking. Wisps circle over his head."""
        if self.dead:
            return
        newly_stunned = self.stun_timer <= 0
        self.stun_timer = max(self.stun_timer, duration)
        if newly_stunned:
            from src.sprites.banshee import StunMark      # (avoids a circular import)
            StunMark(self.game, self)
        self.cancel_attack()
        self.cancel_dash()
        self.cancel_shot()
        self.jump_buffer_timer = 0.0

    # ------------------------------------------------------------ damage
    def take_damage(self, amount, source_x):
        """Hurt the player. Returns True if the hit counted.
        Ignored while invulnerable or in the middle of a dash."""
        if self.dead or self.invuln_timer > 0 or self.dash_timer > 0:
            return False
        self.health -= amount
        self.cancel_shot()
        # the killing blow gets its own, gorier sound
        self.game.audio.play(settings.DEATH_SOUND if self.health <= 0 else "hit_hurt")
        self.cancel_attack()
        self.cancel_dash()
        self.flipping = False
        self.invuln_timer = settings.PLAYER_INVULN_TIME
        self.hurt_timer = settings.PLAYER_HURT_TIME
        away = 1 if self.hitbox.centerx >= source_x else -1
        kx, ky = settings.PLAYER_KNOCKBACK
        self.vel.update(away * kx, -ky)
        self.game.camera.shake(*settings.HURT_SHAKE)
        if self.health <= 0:
            self.die(source_x)
        return True

    def die(self, source_x):
        """Killing blow: he turns to the attacker, staggers back bleeding and
        slowly collapses (update_dead). The game shows the defeat screen."""
        self.health = 0
        self.dead = True
        self.stun_timer = 0.0
        self.hurt_timer = 0.0
        self.invuln_timer = 0.0
        self.direction = 0
        self.drop_through = False
        self.facing_right = source_x > self.hitbox.centerx
        away = -1 if self.facing_right else 1
        self.vel.update(away * settings.DEATH_KNOCKBACK, min(self.vel.y, -180))
        self.state = "death"
        self.animation.reset()
        blood_spray(self.game, self.chest_pos(), away)
        self.game.camera.shake(*settings.DEATH_SHAKE)
        self.game.on_player_death()

    def chest_pos(self):
        """Where the wound is: his chest while standing, further forward once he lies down."""
        facing = 1 if self.facing_right else -1
        if self.dead and self.animation.index >= 6:
            return (self.hitbox.centerx + facing * 6 * settings.SCALE, self.hitbox.bottom - 2 * settings.SCALE)
        return (self.hitbox.centerx + facing * settings.SCALE, self.hitbox.top + round(self.hitbox.height * 0.45))

    @property
    def current_damage(self):
        if self.dash_attacking:
            return settings.DASH_DAMAGE
        return settings.PLAYER_ATTACKS[self.combo_step]["damage"]

    def hit_enemies(self):
        """Damage every enemy the blade touches - once per swing/dash."""
        hb = self.attack_hitbox
        if hb is None:
            return
        for enemy in list(self.game.enemies):        # list(): enemies may die here
            if enemy.invulnerable:
                continue                             # (not marked: can still be hit after)
            if enemy.last_hit_by != self.attack_id and hb.colliderect(enemy.hitbox):
                enemy.last_hit_by = self.attack_id
                enemy.take_damage(self.current_damage, self.hitbox.centerx)

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
        if self.shooting:
            return "bow"
        if self.throwing:
            return "attack1"
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
        if self.dead:
            self.update_dead()
            return
        dt = self.game.dt
        self.coyote_timer = settings.COYOTE_TIME if self.on_ground else max(0.0, self.coyote_timer - dt)
        self.jump_buffer_timer = max(0.0, self.jump_buffer_timer - dt)
        self.combo_timer = max(0.0, self.combo_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.bow_cooldown = max(0.0, self.bow_cooldown - dt)
        self.throw_cooldown = max(0.0, self.throw_cooldown - dt)
        self.invuln_timer = max(0.0, self.invuln_timer - dt)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)
        self.stun_timer = max(0.0, self.stun_timer - dt)

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
        if self.shooting:
            bow = self.animations["bow"]
            if not self.arrow_fired and bow.index >= settings.PLAYER_BOW_RELEASE_FRAME:
                self.fire_arrow()
            if bow.finished:
                self.shooting = False
                self.bow_cooldown = settings.PLAYER_BOW_COOLDOWN
                self.set_state(self.choose_state())
        if self.throwing and self.animations["attack1"].finished:
            self.throwing = False
            self.set_state(self.choose_state())
        self.hit_enemies()       # before the attack may end, so last frames still count
        if self.dash_attacking and self.dash_timer <= 0 and self.animation.finished:
            self.dash_attacking = False
            self.lunge_speed = 0.0
            self.set_state(self.choose_state())
        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        if self.invuln_timer > 0 and int(self.invuln_timer * 15) % 2 == 0:
            self.image = self.image.copy()                 # blink while invulnerable
            self.image.set_alpha(70)
        self.align_image()
        self.spawn_afterimages(dt)

    def update_dead(self):
        """No control: slide to a stop, collapse (only once he's on the ground),
        drip blood while falling, then a pool spreads under him."""
        dt = self.game.dt
        self.vel.x *= math.exp(-5 * dt)
        self.physics_update()
        if not self.dead:              # fell out of the map -> respawned
            return
        anim = self.animation
        if self.on_ground or anim.index < 3:           # don't fall flat in mid-air
            anim.update(dt)

        if not anim.finished:
            self.drip_timer -= dt
            if self.drip_timer <= 0:
                self.drip_timer = settings.BLOOD_DRIP_INTERVAL
                facing = 1 if self.facing_right else -1
                BloodDrop(self.game, self.chest_pos(), (facing * 30 + (self.vel.x * 0.5), -40))
        elif self.on_ground:
            self.lying_time += dt
            if self.blood_pool is None:
                self.blood_pool = BloodPool(self.game, self.chest_pos()[0], self.hitbox.bottom)

        self.image = anim.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        self.align_image()

    def cutscene_animate(self, state, dt):
        """Cutscene control: just play an animation - no input, no physics."""
        self.sync_hitbox()
        self.set_state(state)
        self.animation.update(dt)
        self.image = self.animation.image
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)
        self.align_image()

    def on_fell_out_of_map(self):
        """Respawn instead of disappearing (a body falling into a pit also skips
        straight to the defeat message)."""
        if self.dead:
            self.lying_time = settings.DEFEAT_MESSAGE_DELAY
            self.vel.update(0, 0)
            return
        self.respawn()

    def respawn(self):
        self.stun_timer = 0.0
        self.pos.update(self.spawn_point)
        self.vel.update(0, 0)
        self.hitbox.midbottom = (round(self.pos.x), round(self.pos.y))
        self.flipping = False
        self.cancel_attack()
        self.cancel_dash()
        self.cancel_shot()
        self.game.camera.snap()
