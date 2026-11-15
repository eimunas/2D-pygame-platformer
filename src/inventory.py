"""Weapon bar: scroll the mouse wheel to switch weapons.

Each wheel notch moves the selection one weapon (down = next, up = previous,
wrapping around) and a bar of weapon slots pops up at the bottom of the
screen. Landing on a weapon equips it right away. Weapons you don't own yet
(the bow, until you buy it from the trader) show as locked and are skipped.
The bar fades out WEAPON_BAR_TIME seconds after the last scroll.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import load_image

if TYPE_CHECKING:
    from src.game import Game

SLOT, GAP = 76, 12
TEXT = (250, 244, 232)
DIM = (150, 146, 140)
RED = (214, 52, 64)
PANEL = (20, 16, 24)


def weapon_icon(weapon_id, scale):
    return load_image(os.path.join(settings.ASSETS_DIR, "items", f"{weapon_id}.png"), scale)


class WeaponBar:
    def __init__(self, game: Game):
        self.game = game
        self.timer = 0.0                       # > 0 while the bar is shown
        self.font = pygame.font.SysFont("consolas", 18, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 15)

    # ------------------------------------------------------------ weapons
    def owns(self, weapon):
        return weapon["item"] is None or self.game.progress.item_count(weapon["item"]) > 0

    def available(self):
        return [w["id"] for w in settings.WEAPONS if self.owns(w)]

    def current(self):
        return self.game.player.weapon

    # ------------------------------------------------------------ input
    def scroll(self, steps):
        """steps > 0: next weapon, < 0: previous. Shows the bar; equips the result."""
        self.timer = settings.WEAPON_BAR_TIME
        options = self.available()
        if not options:
            return
        cur = self.current()
        i = options.index(cur) if cur in options else 0
        choice = options[(i + steps) % len(options)]
        if choice != cur:
            self.game.player.set_weapon(choice)
            self.game.progress.equip(choice)

    def update(self, dt):
        self.timer = max(0.0, self.timer - dt)

    # ------------------------------------------------------------ drawing
    def draw(self, surface):
        if self.timer <= 0:
            return
        weapons = settings.WEAPONS
        sw, sh = surface.get_size()
        total = len(weapons) * SLOT + (len(weapons) - 1) * GAP
        layer = pygame.Surface((max(total + 40, 360), SLOT + 70), pygame.SRCALPHA)
        lw = layer.get_width()
        x0 = (lw - total) // 2

        current = self.current()
        locked_names = []
        for i, w in enumerate(weapons):
            owned = self.owns(w)
            selected = w["id"] == current
            rect = pygame.Rect(x0 + i * (SLOT + GAP), 10 - (6 if selected else 0), SLOT, SLOT)
            pygame.draw.rect(layer, (*PANEL, 225), rect, border_radius=6)
            pygame.draw.rect(layer, RED if selected else (90, 84, 92), rect, 3 if selected else 2,
                             border_radius=6)
            icon = weapon_icon(w["id"], 3)
            if not owned:
                icon = icon.copy()
                icon.fill((70, 66, 74, 255), special_flags=pygame.BLEND_RGBA_MIN)
                locked_names.append(w["name"])
            layer.blit(icon, icon.get_rect(center=rect.center))
            if not owned:
                self.draw_lock(layer, (rect.right - 14, rect.bottom - 14))
            num = self.small_font.render(str(i + 1), True, DIM)
            layer.blit(num, (rect.left + 6, rect.top + 4))

        name = next(w["name"] for w in weapons if w["id"] == current)
        strip = pygame.Rect(0, SLOT + 12, lw, 52 if locked_names else 30)
        pygame.draw.rect(layer, (*PANEL, 190), strip, border_radius=6)     # readable over any ground
        label = self.font.render(name, True, TEXT)
        layer.blit(label, label.get_rect(midtop=(lw // 2, SLOT + 16)))
        if locked_names:
            hint = self.small_font.render(f"{', '.join(locked_names)}: buy from the trader", True, (206, 200, 190))
            layer.blit(hint, hint.get_rect(midtop=(lw // 2, SLOT + 40)))

        fade = min(1.0, self.timer / 0.3)                   # fades out at the end
        layer.set_alpha(round(255 * fade))
        surface.blit(layer, ((sw - lw) // 2, sh - layer.get_height() - 16))

    @staticmethod
    def draw_lock(surface, center):
        cx, cy = center
        pygame.draw.rect(surface, DIM, (cx - 7, cy - 1, 14, 10))
        pygame.draw.rect(surface, DIM, (cx - 5, cy - 8, 10, 9), 2,
                         border_top_left_radius=5, border_top_right_radius=5)
