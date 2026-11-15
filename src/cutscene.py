"""Intro cutscene played before gameplay.

    1. walk_in : the ninja walks in from off-screen left to his spawn point
    2. tour    : the camera glides to each group of enemies and holds on them
    3. return  : the camera glides back to the ninja, then gameplay starts

While it runs, the ninja ignores input and enemies only play their idle
animation (no AI, no movement, no shooting). Enter skips it.
intro_scene_sound plays during the scene and fades out when it ends.

With INTRO_FIT_TO_SOUND the scene stretches/shrinks its camera holds (and, if
needed, its glides) so it lasts exactly as long as the intro sound.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from src import settings

if TYPE_CHECKING:
    from src.game import Game

SKIP_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class IntroCutscene:
    def __init__(self, game: Game):
        self.game = game
        self.active = True
        self.time = 0.0                    # total time since the scene started
        player = game.player
        self.spawn = pygame.Vector2(player.pos)

        # the camera frames the start area as if the ninja were already standing there
        game.camera.snap()
        self.home = pygame.Vector2(game.camera.pos)

        # ninja starts just off-screen to the left
        self.walk_from = self.home.x - player.hitbox.width
        player.pos.x = self.walk_from
        player.facing_right = True
        player.cutscene_animate("walk", 0)

        self.steps = self.build_steps()
        target = self.sound_length() if settings.INTRO_FIT_TO_SOUND else None
        if target:
            self.fit_to(target)
        self.step_index = 0
        self.step_time = 0.0

        game.audio.play(settings.INTRO_SOUND)

    # ------------------------------------------------------------ planning
    def enemy_groups(self):
        """Enemies close together share one camera stop."""
        enemies = sorted(self.game.enemies, key=lambda e: e.hitbox.centerx)
        groups = []
        for e in enemies:
            if groups and e.hitbox.centerx - groups[-1][0].hitbox.centerx <= settings.INTRO_GROUP_SPAN:
                groups[-1].append(e)
            else:
                groups.append([e])
        return groups

    def camera_for(self, x, y):
        cam = self.game.camera
        return cam.clamp(pygame.Vector2(x - cam.view_w / 2, y - cam.view_h / 2 + settings.INTRO_LOOK_OFFSET_Y))

    def build_steps(self):
        """List of steps, each a dict with a 'kind' and a 'time' (seconds)."""
        walk_time = (self.spawn.x - self.walk_from) / settings.WALK_SPEED
        steps = [{"kind": "walk_in", "time": walk_time},
                 {"kind": "hold", "time": settings.INTRO_HOLD_TIME * 0.5, "at": self.home}]
        cam = pygame.Vector2(self.home)

        def pan_to(target):
            time = max(settings.INTRO_MIN_PAN_TIME, cam.distance_to(target) / settings.INTRO_PAN_SPEED)
            steps.append({"kind": "pan", "time": time, "from": pygame.Vector2(cam), "to": target})
            cam.update(target)

        for group in self.enemy_groups():
            cx = sum(e.hitbox.centerx for e in group) / len(group)
            cy = sum(e.hitbox.centery for e in group) / len(group)
            target = self.camera_for(cx, cy)
            pan_to(target)
            steps.append({"kind": "hold", "time": settings.INTRO_HOLD_TIME, "at": target})
        pan_to(pygame.Vector2(self.home))
        steps.append({"kind": "hold", "time": 0.2, "at": self.home})
        return steps

    @property
    def duration(self):
        return sum(s["time"] for s in self.steps)

    def sound_length(self):
        sound = self.game.audio.sounds.get(settings.INTRO_SOUND)
        return sound.get_length() if sound else None

    def fit_to(self, target):
        """Make the whole scene last `target` seconds.
        The walk-in keeps its natural speed; the holds absorb the difference.
        If the holds alone can't absorb it, the glides are scaled too."""
        holds = [s for s in self.steps if s["kind"] == "hold"]
        pans = [s for s in self.steps if s["kind"] == "pan"]
        walk = sum(s["time"] for s in self.steps if s["kind"] == "walk_in")
        pan_total = sum(s["time"] for s in pans)
        hold_total = sum(s["time"] for s in holds)

        hold_budget = target - walk - pan_total
        min_holds = settings.INTRO_MIN_HOLD_TIME * len(holds)
        if hold_budget >= min_holds:
            scale = hold_budget / hold_total
            for s in holds:
                s["time"] *= scale
        else:                                   # very short sound: shorten the glides as well
            for s in holds:
                s["time"] = settings.INTRO_MIN_HOLD_TIME
            self.scale_with_floor(pans, target - walk - min_holds, settings.INTRO_MIN_FIT_PAN_TIME)

    @staticmethod
    def scale_with_floor(steps, budget, floor):
        """Scale step times to sum to `budget`, but never below `floor` each:
        steps that would drop under it are pinned to it, the rest share what's left.
        (If even all-at-floor doesn't fit, they all end up at the floor.)"""
        free = list(steps)
        pinned = []
        while free:
            scale = (budget - floor * len(pinned)) / sum(s["time"] for s in free)
            too_short = [s for s in free if s["time"] * scale < floor]
            if not too_short:
                for s in free:
                    s["time"] *= scale
                break
            for s in too_short:
                free.remove(s)
                pinned.append(s)
        for s in pinned:
            s["time"] = floor

    # ------------------------------------------------------------ running
    def update(self, dt):
        if any(k in self.game.just_pressed for k in SKIP_KEYS):
            self.finish()
            return
        self.time += dt
        self.step_time += dt
        # advance through finished steps, carrying leftover time so the total stays exact
        while self.step_time >= self.steps[self.step_index]["time"]:
            self.step_time -= self.steps[self.step_index]["time"]
            self.step_index += 1
            if self.step_index >= len(self.steps):
                self.finish()
                return

        step = self.steps[self.step_index]
        cam = self.game.camera
        player = self.game.player
        if step["kind"] == "walk_in":
            player.pos.x = self.walk_from + settings.WALK_SPEED * self.step_time
            player.cutscene_animate("walk", dt)
            cam.pos.update(self.home)
        else:
            player.pos.x = self.spawn.x
            player.cutscene_animate("idle", dt)
            if step["kind"] == "pan":
                t = smoothstep(self.step_time / step["time"])
                cam.pos.update(step["from"].lerp(step["to"], t))
            else:
                cam.pos.update(step["at"])

        for enemy in self.game.enemies:
            enemy.cutscene_animate(dt)

    def finish(self):
        """End the scene (also used to skip): ninja at spawn, camera on him."""
        if not self.active:
            return
        self.active = False
        # fade the intro music out instead of cutting it (and never let it run into gameplay)
        self.game.audio.stop(settings.INTRO_SOUND, fade_ms=settings.INTRO_SOUND_FADE_MS)
        player = self.game.player
        player.pos.update(self.spawn)
        player.vel.update(0, 0)
        player.sync_hitbox()
        player.cutscene_animate("idle", 0)
        self.game.camera.snap()

    # ------------------------------------------------------------ drawing
    def draw(self, surface):
        """Cinematic bars that slide in, plus a skip hint."""
        w, h = surface.get_size()
        bar = round(settings.INTRO_BAR_HEIGHT * smoothstep(self.time / 0.4))
        if bar:
            pygame.draw.rect(surface, (8, 6, 10), (0, 0, w, bar))
            pygame.draw.rect(surface, (8, 6, 10), (0, h - bar, w, bar))
        hint = self.game.font.render("Enter: skip", True, (200, 196, 188))
        surface.blit(hint, (w - hint.get_width() - 16, h - bar // 2 - hint.get_height() // 2))
