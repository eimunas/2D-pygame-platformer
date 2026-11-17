"""The trader's shop window (opened with E next to a Trader; the world pauses).

    W/S or Up/Down : choose an item       Enter / Space : buy it
    E or Esc       : leave

Items come from settings.SHOP_ITEMS; coins and bought items live in
game.progress (saved). "unique" items can only be held once: the bow forever,
the bomb until it's thrown - then the trader sells you a new one.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pygame

from src import settings
from src.sprites.animation import load_frames, load_image
from src.ui import draw_coin_counter

if TYPE_CHECKING:
    from src.game import Game

UP_KEYS = (pygame.K_w, pygame.K_UP)
DOWN_KEYS = (pygame.K_s, pygame.K_DOWN)
BUY_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
CLOSE_KEYS = (pygame.K_e,)                    # (Esc is handled by the game)

TEXT = (250, 244, 232)
DIM = (150, 146, 140)
GOLD = (232, 186, 82)
RED = (226, 76, 70)
GREEN = (126, 200, 120)
PANEL = (20, 16, 24)
PANEL_EDGE = (120, 84, 52)

W, H = 600, 360
ROW_H = 76

GREETINGS = [
    "Coins for steel, steel for coins. What'll it be?",
]


class ShopUI:
    def __init__(self, game: Game):
        self.game = game
        self.title_font = pygame.font.SysFont("consolas", 28, bold=True)
        self.name_font = pygame.font.SysFont("consolas", 22, bold=True)
        self.small_font = pygame.font.SysFont("consolas", 16)
        self.selected = 0
        self.trader = None
        self.message, self.message_color, self.message_timer = "", TEXT, 0.0
        self.icons = {item["id"]: load_image(os.path.join(settings.ASSETS_DIR, "items", f"{item['id']}.png"), 3)
                      for item in settings.SHOP_ITEMS}
        self.coin_icon = load_frames(os.path.join(settings.ASSETS_DIR, "items", "coin"), 2)[0]

    @property
    def items(self):
        return settings.SHOP_ITEMS

    # ------------------------------------------------------------ open / close
    def open(self, trader):
        self.trader = trader
        self.selected = 0
        self.say(GREETINGS[0], TEXT, 999)

    def close(self):
        self.trader = None
        self.game.state = "playing"

    def say(self, text, color, seconds=2.5):
        self.message, self.message_color, self.message_timer = text, color, seconds

    # ------------------------------------------------------------ buying
    def owned_out(self, item):
        """A unique item you already have can't be bought again."""
        return item["unique"] and self.game.progress.item_count(item["id"]) > 0

    def buy(self, item):
        progress = self.game.progress
        if self.owned_out(item):
            self.say(item.get("held", f"You already own the {item['name'].lower()}."), DIM)
        elif progress.coins < item["price"]:
            missing = item["price"] - progress.coins
            self.say(f"Not enough coins - you need {missing} more.", RED)
        else:
            progress.buy(item["id"], item["price"])
            self.game.audio.play("coin")
            self.say(f"Bought: {item['name']}! A fine choice.", GREEN)

    # ------------------------------------------------------------ loop
    def update(self, dt):
        self.message_timer = max(0.0, self.message_timer - dt)
        pressed = self.game.just_pressed
        if any(k in pressed for k in CLOSE_KEYS):
            self.close()
            return
        n = len(self.items)
        if any(k in pressed for k in UP_KEYS):
            self.selected = (self.selected - 1) % n
        if any(k in pressed for k in DOWN_KEYS):
            self.selected = (self.selected + 1) % n
        if any(k in pressed for k in BUY_KEYS):
            self.buy(self.items[self.selected])

    # ------------------------------------------------------------ drawing
    def panel_rect(self, surface):
        sw, sh = surface.get_size()
        return pygame.Rect((sw - W) // 2, (sh - H) // 2, W, H)

    def row_rect(self, panel, i):
        return pygame.Rect(panel.left + 24, panel.top + 108 + i * (ROW_H + 8), W - 48, ROW_H)

    def draw(self, surface):
        sw, sh = surface.get_size()
        shade = pygame.Surface((sw, sh), pygame.SRCALPHA)
        shade.fill((8, 6, 10, 150))
        surface.blit(shade, (0, 0))

        panel = self.panel_rect(surface)
        pygame.draw.rect(surface, PANEL, panel, border_radius=6)
        pygame.draw.rect(surface, PANEL_EDGE, panel, 4, border_radius=6)

        # header: portrait, name, wallet
        if self.trader:
            portrait = pygame.transform.scale_by(self.trader.animation.image, 1.25)
            surface.blit(portrait, portrait.get_rect(bottomleft=(panel.left + 18, panel.top + 96)))
        name = self.title_font.render(self.trader.NAME if self.trader else "Shop", True, GOLD)
        surface.blit(name, (panel.left + 110, panel.top + 26))
        if self.message:
            alpha_ok = self.message_timer > 0
            msg = self.small_font.render(self.message, True, self.message_color if alpha_ok else DIM)
            surface.blit(msg, (panel.left + 110, panel.top + 66))
        draw_coin_counter(surface, self.coin_icon, self.small_font, self.game.progress.coins,
                          topright=(panel.right - 20, panel.top + 20), font=self.name_font)

        progress = self.game.progress
        for i, item in enumerate(self.items):
            self.draw_row(surface, self.row_rect(panel, i), item, i == self.selected, progress)

        hint = self.small_font.render("W/S: choose    Enter: buy    E / Esc: leave", True, DIM)
        surface.blit(hint, hint.get_rect(midbottom=(panel.centerx, panel.bottom - 14)))

    def draw_row(self, surface, rect, item, selected, progress):
        bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        bg.fill((255, 255, 255, 22 if selected else 8))
        surface.blit(bg, rect)
        if selected:
            pygame.draw.rect(surface, RED, rect, 3, border_radius=4)

        icon = self.icons[item["id"]]
        surface.blit(icon, icon.get_rect(midleft=(rect.left + 12, rect.centery)))
        name = self.name_font.render(item["name"], True, TEXT)
        surface.blit(name, (rect.left + 76, rect.top + 12))
        desc = self.small_font.render(item["desc"], True, DIM)
        surface.blit(desc, (rect.left + 76, rect.top + 44))

        # right side: price (red when you can't afford it) or OWNED; how many you have
        right = rect.right - 16
        if self.owned_out(item):
            tag = self.name_font.render("OWNED", True, GREEN)
            surface.blit(tag, tag.get_rect(midright=(right, rect.centery - 8)))
        else:
            afford = progress.coins >= item["price"]
            price = self.name_font.render(str(item["price"]), True, TEXT if afford else RED)
            pr = price.get_rect(midright=(right, rect.centery - 8))
            surface.blit(price, pr)
            surface.blit(self.coin_icon, self.coin_icon.get_rect(midright=(pr.left - 4, pr.centery)))
        have = progress.item_count(item["id"])
        if have and not item["unique"]:
            label = self.small_font.render(f"have: {have}", True, DIM)
            surface.blit(label, label.get_rect(midright=(right, rect.centery + 20)))
