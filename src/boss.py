"""The mini-boss arena and its cutscene (stage "Golem's Gate").

Level characters (see src/level.py):
    S  rune seal: the arena's entrance        B  where the golem lands
    C  cave entrance: the level exit (opens once the golem is defeated)

BossArena.state:
    sealed -> the seal blocks the way while any other enemy is still alive
    open   -> all clear; walking BOSS_TRIGGER_DISTANCE past the seal starts
              the BossCutscene
    fight  -> the seal closes behind the ninja; the golem attacks; boss music
    done   -> golem defeated: seal gone, cave open, the stage music returns

BossCutscene: the camera glides to the arena, the golem falls out of the sky,
lands (screen shake + both cutscene sounds), the camera holds on him with his
name, then glides back and the fight starts. Enter skips it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.cutscene import SKIP_KEYS, smoothstep
from src.sprites.golem import Golem, dust_burst
from src.ui import draw_bar

if TYPE_CHECKING:
    from src.game import Game


class BossArena:
    def __init__(self, game: Game, seal_pos, boss_pos):
        self.game = game
        self.seal_x, self.ground_y = seal_pos
        self.boss_pos = pygame.Vector2(boss_pos)
        self.state = "sealed"
        self.time = 0.0
        self.seal_alpha = 1.0                  # fades out when the seal opens
        self.hint_timer = 0.0                  # "defeat every enemy first" message
        self.banner_timer = 0.0                # after the golem falls
        self.music_timer = None                # seconds until the stage music returns
        self.font = pygame.font.SysFont("consolas", 18, bold=True)
        self.name_font = pygame.font.SysFont("consolas", 22, bold=True)

    # ------------------------------------------------------------ flow
    def update(self, dt):
        self.time += dt
        self.hint_timer = max(0.0, self.hint_timer - dt)
        self.banner_timer = max(0.0, self.banner_timer - dt)
        game, player = self.game, self.game.player

        if self.state == "sealed":
            if not game.enemies:
                self.state = "open"
                game.audio.play("shinobi_spot", volume=0.6)        # a soft chime as it breaks
            elif player.hitbox.right > self.seal_x and player.hitbox.centerx < self.seal_x:
                self.push_player(right_edge=self.seal_x)
                self.hint_timer = 2.0
        elif self.state == "open":
            self.seal_alpha = max(0.0, self.seal_alpha - dt * 1.5)
            if player.hitbox.left > self.seal_x + settings.BOSS_TRIGGER_DISTANCE and not player.dead:
                self.start_fight()
        elif self.state == "fight":
            self.seal_alpha = min(1.0, self.seal_alpha + dt * 3)
            if player.hitbox.left < self.seal_x:
                self.push_player(left_edge=self.seal_x)
        elif self.state == "done":
            self.seal_alpha = max(0.0, self.seal_alpha - dt * 1.5)
            if self.music_timer is not None:
                self.music_timer -= dt
                if self.music_timer <= 0:
                    game.audio.play_music(settings.LEVEL_MUSIC, loop=True, fade_ms=settings.MUSIC_FADE_IN_MS)
                    self.music_timer = None

    def push_player(self, left_edge=None, right_edge=None):
        p = self.game.player
        if right_edge is not None:
            p.hitbox.right = right_edge
        else:
            p.hitbox.left = left_edge
        p.pos.x = p.hitbox.centerx
        p.vel.x = 0
        if p.dash_timer > 0:
            p.end_dash_movement(hit_wall=True)

    def start_fight(self):
        """Walked into the arena: spawn the golem high above and run the cutscene."""
        self.state = "cutscene"
        game = self.game
        golem = Golem(game, (self.boss_pos.x, self.boss_pos.y - settings.BOSS_SPAWN_HEIGHT))
        golem.bounds = (self.seal_x + golem.hitbox.width / 2 + settings.TILE_SIZE / 2,
                        game.tilemap.width - golem.hitbox.width / 2)
        game.cutscene = BossCutscene(game, self, golem)

    def begin_battle(self):
        """The cutscene is over: the seal closes, the golem wakes, music!"""
        self.state = "fight"
        game = self.game
        if settings.BOSS_FIGHT_HEAL:
            game.player.health = game.player.max_health
        if game.boss:
            game.boss.active = True
            game.boss.set_mode("walk")
        game.audio.play_music(settings.BOSS_MUSIC, loop=True, fade_ms=600)

    def on_boss_defeated(self):
        self.state = "done"
        self.banner_timer = 4.0
        self.game.audio.stop_music(fade_ms=2500)
        self.music_timer = 3.0

    @property
    def exit_open(self):
        return self.state == "done"

    # ------------------------------------------------------------ drawing
    def draw_world(self, surface, camera):
        """The rune seal: a shimmering wall of light at the arena entrance."""
        if self.seal_alpha <= 0:
            return
        h = settings.BOSS_SEAL_HEIGHT
        world = pygame.Rect(0, 0, 28, h)
        world.midbottom = (self.seal_x, self.ground_y)
        rect = camera.apply(world)
        if not rect.colliderect(surface.get_rect()):
            return
        layer = pygame.Surface(world.size, pygame.SRCALPHA)
        r, g, b = settings.BOSS_SEAL_COLOR
        a = self.seal_alpha
        for i, (x, width, base) in enumerate(((14, 10, 50), (14, 4, 110), (5, 2, 70), (23, 2, 70))):
            flicker = 0.75 + 0.25 * math.sin(self.time * 6 + i * 1.7)
            pygame.draw.rect(layer, (r, g, b, round(base * flicker * a)), (x - width // 2, 0, width, h))
        for k in range(8):                     # rune glyphs drifting upwards
            y = (h - (self.time * 60 + k * h / 8) % h)
            gx = 8 + (k * 7) % 12
            alpha = round(220 * a * min(1.0, y / 40) * min(1.0, (h - y) / 40))
            for dx, dy in ((0, 0), (4, 0), (0, 4), (4, 4), (2, 2)) if k % 2 else ((2, 0), (0, 2), (4, 2), (2, 4)):
                pygame.draw.rect(layer, (230, 252, 255, alpha), (gx + dx, y + dy, 3, 3))
        surface.blit(layer, rect)

    def draw_hud(self, surface):
        game = self.game
        w, h = surface.get_size()
        if self.hint_timer > 0:
            alpha = round(255 * min(1.0, self.hint_timer / 0.5))
            game.draw_text(self.font, "An ancient seal blocks the way - defeat every enemy first",
                           (w // 2, 150), color=(200, 236, 255), alpha=alpha)
        boss = game.boss
        if self.state == "fight" and boss is not None and boss.alive():
            bar = pygame.Rect(0, 0, 520, 18)
            bar.midbottom = (w // 2, h - 26)
            draw_bar(surface, bar, boss.health, boss.max_health)
            game.draw_text(self.name_font, settings.GOLEM_NAME.upper(), (w // 2, bar.top - 16),
                           color=(214, 236, 255))
        if self.banner_timer > 0:
            alpha = round(255 * min(1.0, self.banner_timer / 0.8, (4.0 - self.banner_timer) / 0.5))
            game.draw_text(game.big_font, f"The {settings.GOLEM_NAME} has fallen", (w // 2, 170),
                           color=(232, 186, 82), alpha=alpha)
            game.draw_text(game.font, "The way into the ancient caves is open", (w // 2, 216), alpha=alpha)


class BossCutscene:
    """Pan to the arena -> the golem falls from the sky and lands -> hold on him
    (name + title) -> pan back -> fight."""

    PAN_TIME = 1.1
    SKY_HOLD = 0.35
    RETURN_TIME = 0.9

    def __init__(self, game: Game, arena: BossArena, golem: Golem):
        self.game = game
        self.arena = arena
        self.golem = golem
        self.active = True
        self.time = 0.0
        self.phase, self.phase_time = "pan", 0.0
        self.fall_speed = settings.BOSS_FALL_SPEED
        self.landed = False

        player = game.player
        player.cancel_attack()
        player.cancel_dash()
        player.cancel_shot()
        player.vel.update(0, 0)
        player.flipping = False
        player.facing_right = golem.hitbox.centerx > player.hitbox.centerx
        golem.facing_right = not player.facing_right
        game.audio.stop_music(fade_ms=900)

        cam = game.camera
        self.cam_from = pygame.Vector2(cam.pos)
        self.cam_arena = cam.clamp(pygame.Vector2(arena.boss_pos.x - cam.view_w / 2,
                                                  arena.boss_pos.y - cam.view_h * 0.62))
        sound = game.audio.sounds.get(settings.BOSS_CUTSCENE_SOUND)
        self.hold_time = max(2.2, sound.get_length() - 0.2) if sound else 2.4

    # ------------------------------------------------------------ running
    def set_phase(self, name):
        self.phase, self.phase_time = name, 0.0

    def land_golem(self, effects=True):
        g = self.golem
        g.pos.y = self.arena.boss_pos.y
        g.sync_hitbox()
        g.vel.update(0, 0)
        g.on_ground = True
        self.landed = True
        self.landed_at = self.time
        if effects:
            self.game.camera.shake(*settings.BOSS_CUTSCENE_SHAKE)
            self.game.audio.play(settings.BOSS_CUTSCENE_LAND_SOUND)
            self.game.audio.play(settings.BOSS_CUTSCENE_SOUND)
            dust_burst(self.game, g.hitbox.centerx, g.hitbox.bottom, g.hitbox.width * 1.4, chunks=14)

    def update(self, dt):
        if any(k in self.game.just_pressed for k in SKIP_KEYS):
            self.finish(skipped=True)
            return
        self.time += dt
        self.phase_time += dt
        game, cam, golem = self.game, self.game.camera, self.golem

        if self.phase == "pan":
            t = smoothstep(self.phase_time / self.PAN_TIME)
            cam.pos.update(self.cam_from.lerp(self.cam_arena, t))
            if self.phase_time >= self.PAN_TIME:
                self.set_phase("sky")
        elif self.phase == "sky":
            cam.pos.update(self.cam_arena)
            if self.phase_time >= self.SKY_HOLD:
                self.set_phase("fall")
        elif self.phase == "fall":
            cam.pos.update(self.cam_arena)
            self.fall_speed += settings.GRAVITY * 1.5 * dt
            golem.pos.y += self.fall_speed * dt
            golem.sync_hitbox()
            if golem.pos.y >= self.arena.boss_pos.y:
                self.land_golem()
                self.set_phase("hold")
        elif self.phase == "hold":
            cam.pos.update(self.cam_arena)
            if self.phase_time >= self.hold_time:
                self.cam_back = game.camera.desired_position()
                self.set_phase("return")
        elif self.phase == "return":
            t = smoothstep(self.phase_time / self.RETURN_TIME)
            cam.pos.update(self.cam_arena.lerp(self.cam_back, t))
            if self.phase_time >= self.RETURN_TIME:
                self.finish()
                return
        cam.update_shake()

        # golem pose: falling -> landing impact (fists on the ground) -> standing
        if not self.landed:
            golem.play_anim("air", dt)
        elif self.time - self.landed_at < 0.7:
            golem.play_anim("land", dt)
        else:
            golem.play_anim("idle", dt)
        game.player.cutscene_animate("idle", dt)

    def finish(self, skipped=False):
        if not self.active:
            return
        self.active = False
        game = self.game
        if skipped:
            for name in (settings.BOSS_CUTSCENE_SOUND, settings.BOSS_CUTSCENE_LAND_SOUND):
                game.audio.stop(name, fade_ms=400)
        if not self.landed:
            self.land_golem(effects=False)
        self.golem.play_anim("idle", 0)
        game.camera.snap()
        self.arena.begin_battle()

    # ------------------------------------------------------------ drawing
    def draw(self, surface):
        w, h = surface.get_size()
        bar = round(settings.INTRO_BAR_HEIGHT * smoothstep(self.time / 0.4))
        pygame.draw.rect(surface, (8, 6, 10), (0, 0, w, bar))
        pygame.draw.rect(surface, (8, 6, 10), (0, h - bar, w, bar))
        if self.phase in ("hold", "return") and self.landed:
            t = self.phase_time if self.phase == "hold" else self.hold_time
            alpha = round(255 * min(1.0, max(0.0, (t - 0.5) / 0.6)))
            if self.phase == "return":
                alpha = round(255 * max(0.0, 1 - self.phase_time / 0.4))
            if alpha:
                self.game.draw_text(self.game.big_font, settings.GOLEM_NAME.upper(), (w // 2, 110),
                                    color=(214, 236, 255), alpha=alpha)
                self.game.draw_text(self.game.font, settings.GOLEM_TITLE, (w // 2, 152), alpha=alpha)
        hint = self.game.font.render("Enter: skip", True, (200, 196, 188))
        surface.blit(hint, (w - hint.get_width() - 16, h - bar // 2 - hint.get_height() // 2))
