"""Main menu: pick a stage (only unlocked ones can be started) or quit.

    W/S or Up/Down : choose          Enter / Space : start the stage
    mouse          : hover + click   Esc           : quit the game

Stage 1 is always open; every other stage opens once the stage before it is
cleared (see src/progress.py). The forest background drifts slowly, the ninja
and a samurai face off in the foreground, and main_menu music loops.
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.level import LEVELS
from src.sprites.animation import Animation, load_frames
from src.ui import draw_coin_counter

if TYPE_CHECKING:
    from src.game import Game

UP_KEYS = (pygame.K_w, pygame.K_UP)
DOWN_KEYS = (pygame.K_s, pygame.K_DOWN)
CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)

TEXT = (250, 244, 232)
DIM = (150, 146, 140)
GOLD = (232, 186, 82)
RED = (214, 52, 64)
PANEL = (14, 12, 22)

ROW_W, ROW_H, ROW_GAP = 440, 46, 10


class MainMenu:
    def __init__(self, game: Game):
        self.game = game
        self.title_font = pygame.font.SysFont("consolas", 80, bold=True)
        self.row_font = pygame.font.SysFont("consolas", 24, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 18)
        self.selected = 0
        self.scroll = 0.0                  # background drift
        self.time = 0.0
        self.notice = ""                   # e.g. "Clear Stage 1 to unlock"
        self.notice_timer = 0.0
        self.last_mouse = None

        # the ninja and a samurai facing each other in the foreground
        big = settings.SCALE * 2
        self.ninja = Animation(load_frames(os.path.join(settings.ASSETS_DIR, "player", "idle"), big), 6)
        self.samurai = Animation(
            load_frames(os.path.join(settings.ASSETS_DIR, "enemies", "samurai", "idle"), big), 6)
        # coin markers on the stage rows: gold = found, dark silhouette = still hidden
        self.coin = load_frames(os.path.join(settings.ASSETS_DIR, "items", "coin"), 2)[0]
        self.coin_missing = self.coin.copy()
        self.coin_missing.fill((60, 56, 64, 255), special_flags=pygame.BLEND_RGBA_MIN)

    # ------------------------------------------------------------ items
    @property
    def items(self):
        """One entry per stage, then Quit."""
        return list(range(len(LEVELS))) + ["quit"]

    def row_rect(self, i):
        w, _ = self.game.screen.get_size()
        top = 172
        return pygame.Rect((w - ROW_W) // 2, top + i * (ROW_H + ROW_GAP), ROW_W, ROW_H)

    def open(self):
        """Called whenever the menu is shown: highlight the furthest open stage."""
        progress = self.game.progress
        self.selected = max(i for i in range(len(LEVELS)) if progress.is_unlocked(i))
        self.notice_timer = 0.0
        self.last_mouse = None

    # ------------------------------------------------------------ input
    def activate(self, item):
        if item == "quit":
            self.game.running = False
        elif self.game.progress.is_unlocked(item):
            self.game.load_level(item)
        else:
            self.notice = f"Clear Stage {item} to unlock Stage {item + 1}"
            self.notice_timer = 2.0

    def update(self, dt):
        self.time += dt
        self.scroll += settings.MENU_SCROLL_SPEED * dt
        self.notice_timer = max(0.0, self.notice_timer - dt)
        self.ninja.update(dt)
        self.samurai.update(dt)

        game = self.game
        n = len(self.items)
        if any(k in game.just_pressed for k in UP_KEYS):
            self.selected = (self.selected - 1) % n
        if any(k in game.just_pressed for k in DOWN_KEYS):
            self.selected = (self.selected + 1) % n

        # mouse: hovering selects (only when the mouse actually moves), click starts
        mouse = pygame.mouse.get_pos()
        hovered = next((i for i in range(n) if self.row_rect(i).collidepoint(mouse)), None)
        if mouse != self.last_mouse and self.last_mouse is not None and hovered is not None:
            self.selected = hovered
        self.last_mouse = mouse
        if 1 in game.mouse_just_pressed and hovered is not None:
            self.selected = hovered
            self.activate(self.items[hovered])
            return

        if any(k in game.just_pressed for k in CONFIRM_KEYS):
            self.activate(self.items[self.selected])

    # ------------------------------------------------------------ drawing
    def draw(self, surface):
        w, h = surface.get_size()
        # same forest as in the levels, drifting sideways; y far down = ground-level view
        self.game.background.draw(surface, (self.scroll, 100000))
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((10, 8, 16, 120))
        surface.blit(shade, (0, 0))

        self.draw_duel(surface)
        self.draw_title(surface)
        draw_coin_counter(surface, self.coin, self.small_font, self.game.progress.coins,
                          topright=(w - 20, 18), font=self.row_font)
        progress = self.game.progress
        for i, item in enumerate(self.items):
            self.draw_row(surface, i, item, progress)

        if self.notice_timer > 0:
            self.text(surface, self.small_font, self.notice, (w // 2, self.row_rect(len(self.items)).top + 8),
                      color=RED, alpha=round(255 * min(1.0, self.notice_timer / 0.4)))
        hint = "W/S: choose    Enter: start    Esc: quit"
        self.text(surface, self.small_font, hint, (w // 2, h - 24), color=DIM)

    def draw_title(self, surface):
        w = surface.get_width()
        bob = round(math.sin(self.time * 1.6) * 3)
        self.text(surface, self.title_font, settings.MENU_TITLE, (w // 2, 82 + bob), color=TEXT, shadow=5)
        self.text(surface, self.small_font, settings.MENU_SUBTITLE, (w // 2, 140), color=GOLD)

    def draw_duel(self, surface):
        w, h = surface.get_size()
        ground = h - 52
        ninja = self.ninja.image
        samurai = pygame.transform.flip(self.samurai.image, True, False)
        surface.blit(ninja, ninja.get_rect(midbottom=(120, ground)))
        surface.blit(samurai, samurai.get_rect(midbottom=(w - 120, ground)))

    def draw_row(self, surface, i, item, progress):
        rect = self.row_rect(i)
        selected = i == self.selected
        locked = item != "quit" and not progress.is_unlocked(item)

        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((*PANEL, 215 if selected else 150))
        surface.blit(panel, rect)
        if selected:
            pygame.draw.rect(surface, DIM if locked else RED, rect, 3)
            # small marker that nudges left/right
            nudge = round(math.sin(self.time * 6) * 3)
            tip = (rect.left - 14 + nudge, rect.centery)
            pygame.draw.polygon(surface, DIM if locked else RED,
                                [(tip[0] - 12, tip[1] - 9), (tip[0], tip[1]), (tip[0] - 12, tip[1] + 9)])

        if item == "quit":
            self.text(surface, self.row_font, "Quit", rect.center, color=TEXT if selected else DIM)
            return

        name_color = DIM if locked else TEXT
        label = self.small_font.render(f"STAGE {item + 1}", True, GOLD if not locked else DIM)
        surface.blit(label, label.get_rect(midleft=(rect.left + 18, rect.centery)))
        name = self.row_font.render(LEVELS[item]["name"] if not locked else "? ? ?", True, name_color)
        surface.blit(name, name.get_rect(midleft=(rect.left + 118, rect.centery)))

        right = rect.right - 18
        coins = LEVELS[item].get("coins", 0)
        if coins and not locked:
            for k in range(coins):
                found = progress.has_found(f"{LEVELS[item]['name']}#{k}")
                icon = self.coin if found else self.coin_missing
                surface.blit(icon, icon.get_rect(midright=(right - 96 - k * 30, rect.centery)))
        if locked:
            self.draw_lock(surface, (right - 10, rect.centery))
        elif progress.is_cleared(item):
            tag = self.small_font.render("CLEARED", True, GOLD)
            surface.blit(tag, tag.get_rect(midright=(right, rect.centery)))

    @staticmethod
    def draw_lock(surface, center):
        """A little pixel padlock."""
        cx, cy = center
        color = DIM
        pygame.draw.rect(surface, color, (cx - 9, cy - 2, 18, 13))               # body
        pygame.draw.rect(surface, color, (cx - 6, cy - 11, 12, 11), 3,           # shackle
                         border_top_left_radius=6, border_top_right_radius=6)
        pygame.draw.rect(surface, PANEL, (cx - 1, cy + 2, 3, 5))                 # keyhole

    @staticmethod
    def text(surface, font, text, center, color=TEXT, alpha=255, shadow=3):
        for img, (dx, dy) in ((font.render(text, True, (14, 12, 22)), (shadow, shadow)),
                              (font.render(text, True, color), (0, 0))):
            img.set_alpha(alpha)
            surface.blit(img, img.get_rect(center=(center[0] + dx, center[1] + dy)))
