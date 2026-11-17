"""The Game class: owns pygame setup, shared state, levels and the main loop.

Pass the Game instance to any object that needs shared state, e.g.:

    class Enemy(pygame.sprite.Sprite):
        def __init__(self, game, pos):
            super().__init__(game.all_sprites, game.actors)
            self.game = game    # -> game.dt, game.keys, game.screen, game.tilemap, game.player ...

The game opens on the main menu (src/menu.py) when created with Game(menu=True)
(as main.py does); Game() / Game(start_level=n) jumps straight into a stage.

Levels come from src/level.py LEVELS. Walking through a level's exit gate
marks the stage cleared (unlocking the next one in the menu), shows
"Stage clear" and loads the next one; after the last one: victory
(Enter: main menu, R: play again from stage 1). If the ninja dies he
collapses, the defeat message shows, and Enter starts over from stage 1.
Esc in a stage goes back to the menu; Esc in the menu quits.
"""

import math
import os
import random

import pygame

from src import settings
from src.audio import Audio
from src.background import ParallaxBackground
from src.boss import BossArena
from src.camera import Camera
from src.cutscene import IntroCutscene
from src.inventory import WeaponBar, weapon_icon
from src.level import LEVELS, load_level
from src.menu import MainMenu
from src.progress import Progress
from src.shop import ShopUI
from src.sprites import Coin, coin_spots
from src.sprites.animation import load_frames
from src.ui import PlayerHealthBar, draw_coin_counter, draw_enemy_bar


class Game:
    def __init__(self, start_level=0, menu=False):
        # small audio buffer = sounds start right when you press the button
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((settings.SCREEN_W, settings.SCREEN_H))
        pygame.display.set_caption(settings.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)
        self.big_font = pygame.font.SysFont("consolas", 48, bold=True)
        self.audio = Audio()               # game.audio.play("jump")

        # shared per-frame state, read by sprites through their `game` reference
        self.running = True
        self.dt = 0.0
        self.keys = pygame.key.get_pressed()   # keys held down right now
        self.just_pressed = set()              # keys pressed this frame
        self.just_released = set()             # keys released this frame
        self.mouse_just_pressed = set()        # mouse buttons clicked this frame (1 = left)
        self.wheel = 0                         # mouse wheel notches this frame (+ = up)

        self.backgrounds = {}                  # theme name -> ParallaxBackground (loaded on first use)
        self.background = self.get_background("day")

        self.progress = Progress(settings.SAVE_FILE)    # cleared stages, coins, items
        self.main_menu = MainMenu(self)
        self.shop = ShopUI(self)
        self.weapon_bar = WeaponBar(self)
        self.coin_icon = load_frames(os.path.join(settings.ASSETS_DIR, "items", "coin"), 2)[0]
        if menu:
            self.open_menu()
        else:
            self.load_level(start_level)

    def get_background(self, theme):
        """The parallax background for a theme in settings.BACKGROUND_THEMES."""
        if theme not in self.backgrounds:
            folder = settings.BACKGROUND_THEMES[theme]
            background = ParallaxBackground(self.screen.get_size())
            for path, factor in settings.BACKGROUND_LAYERS:
                file = os.path.join(settings.ASSETS_DIR, folder, os.path.basename(path))
                background.add_layer(file, factor=factor)
            self.backgrounds[theme] = background
        return self.backgrounds[theme]

    # ------------------------------------------------------------ menu
    def open_menu(self):
        """Back to the main menu (from anywhere): silence the stage, play the menu music."""
        self.state = "menu"
        self.background = self.get_background("day")
        if self.audio.enabled:
            pygame.mixer.stop()                    # cut intro / defeat sounds etc.
        self.audio.stop_music()
        self.audio.play_music(settings.MENU_MUSIC, loop=True, fade_ms=settings.MUSIC_FADE_IN_MS)
        self.main_menu.open()

    # ------------------------------------------------------------ levels
    def load_level(self, index):
        """(Re)build everything that belongs to a level."""
        self.level_index = index
        self.level = LEVELS[index]
        self.background = self.get_background(self.level.get("background", "day"))

        # fresh sprite groups (the old level's sprites simply get dropped)
        self.all_sprites = pygame.sprite.Group()        # everything that gets update()
        self.background_decor = pygame.sprite.Group()   # trees, props: behind the player
        self.effects_back = pygame.sprite.Group()       # afterimages: behind actors
        self.actors = pygame.sprite.Group()             # player and enemies (drawn)
        self.enemies = pygame.sprite.Group()            # just the enemies (for AI/combat)
        self.projectiles = pygame.sprite.Group()        # arrows (drawn over characters)
        self.effects_front = pygame.sprite.Group()      # slash streaks: in front of actors
        self.foreground_decor = pygame.sprite.Group()   # rocks, bushes: in front of the player
        self.pickups = pygame.sprite.Group()            # coins (drawn behind actors)
        self.npcs = pygame.sprite.Group()               # the trader (also in background_decor)

        # creates the tilemap, decorations, enemies, exit gate and self.player
        self.player = None
        self.exit_gate = None
        self.boss = None                       # the golem, once he has dropped in
        self.seal_pos = self.boss_spawn = None # boss arena markers (level chars S / B)
        self.tilemap = load_level(self, self.level["layout"])
        if self.player is None:
            raise ValueError(f"Level '{self.level['name']}' has no 'P' (player spawn)")
        self.place_coins()
        self.arena = BossArena(self, self.seal_pos or self.boss_spawn, self.boss_spawn) if self.boss_spawn else None

        self.camera = Camera(self, self.player)
        self.health_bar = PlayerHealthBar(self)
        self.state = "playing"                 # playing | stage_clear | victory | defeat
        self.state_timer = 0.0
        self.defeat_sound_timer = None         # seconds until the defeat sound starts
        self.title_timer = settings.STAGE_TITLE_TIME
        self.audio.stop_music()                # the stage's music starts once gameplay does
        self.music_started = False

        # intro: ninja walks in, camera tours the enemies, then gameplay
        self.cutscene = IntroCutscene(self) if settings.PLAY_INTRO else None

    def place_coins(self):
        """Hide this stage's coins at random spots - skipping coins already found."""
        count = self.level.get("coins", 0)
        missing = [i for i in range(count) if not self.progress.has_found(self.coin_id(i))]
        if not missing:
            return
        exit_x = self.exit_gate.rect.centerx if self.exit_gate else None
        spots = coin_spots(self.tilemap, self.player.pos.x, exit_x)
        ts = self.tilemap.tile_size
        for i, (col, row) in zip(missing, random.sample(spots, min(len(missing), len(spots)))):
            Coin(self, (col * ts + ts // 2, row * ts + ts // 2), self.coin_id(i))

    def coin_id(self, i):
        return f"{self.level['name']}#{i}"

    def equipped_weapon(self):
        """The saved weapon if the ninja still owns it, else the katana."""
        wanted = self.progress.equipped
        for w in settings.WEAPONS:
            if w["id"] == wanted and (w["item"] is None or self.progress.item_count(w["item"]) > 0):
                return wanted
        return "katana"

    def on_weapon_used_up(self):
        """The equipped consumable (the bomb) is gone: back to the katana, and
        flash the weapon bar so the switch is visible."""
        self.player.set_weapon("katana")
        self.progress.equip("katana")
        self.weapon_bar.timer = settings.WEAPON_BAR_TIME

    def on_boss_defeated(self):
        if self.arena:
            self.arena.on_boss_defeated()

    def trader_nearby(self):
        return next((npc for npc in self.npcs if npc.near), None)

    def open_shop(self, trader):
        self.state = "shop"
        self.player.vel.x = 0
        self.shop.open(trader)

    @property
    def is_last_level(self):
        return self.level_index == len(LEVELS) - 1

    def start_music(self):
        """Loop the stage music (quietly) once gameplay begins - after the intro."""
        if not self.music_started:
            self.audio.play_music(settings.LEVEL_MUSIC, loop=True, fade_ms=settings.MUSIC_FADE_IN_MS)
            self.music_started = True

    def complete_level(self):
        """The ninja walked through the exit gate."""
        self.audio.stop_music(fade_ms=settings.MUSIC_FADE_OUT_MS)
        self.progress.mark_cleared(self.level_index)     # unlocks the next stage in the menu
        if self.is_last_level:
            self.state = "victory"
        else:
            self.state = "stage_clear"
            self.state_timer = settings.STAGE_CLEAR_TIME

    def on_player_death(self):
        """Called by the player at 0 health: the world calms down, his
        collapse plays, then the defeat message (see update/draw)."""
        self.state = "defeat"
        self.state_timer = 0.0                 # counts up: seconds since he died
        self.audio.stop_music(fade_ms=settings.MUSIC_FADE_OUT_MS)
        # the defeat sound follows once the blood splash has finished
        splash = self.audio.sounds.get(settings.DEATH_SOUND)
        self.defeat_sound_timer = splash.get_length() if splash else 0.0

    @property
    def defeat_message_shown(self):
        return self.state == "defeat" and self.player.lying_time >= settings.DEFEAT_MESSAGE_DELAY

    @property
    def in_cutscene(self):
        return self.cutscene is not None and self.cutscene.active

    def end_cutscene(self):
        """Skip straight to gameplay (also handy in tests)."""
        if self.cutscene:
            self.cutscene.finish()

    # ------------------------------------------------------------ loop
    def run(self):
        while self.running:
            # capped so a long freeze can't make things jump through tiles
            self.dt = min(self.clock.tick(settings.FPS) / 1000.0, settings.MAX_DT)
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()

    def handle_events(self):
        self.just_pressed.clear()
        self.just_released.clear()
        self.mouse_just_pressed.clear()
        self.wheel = 0
        for event in pygame.event.get():
            if event.type == pygame.MOUSEWHEEL:
                self.wheel += event.y
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_just_pressed.add(event.button)
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.just_pressed.add(event.key)
                if event.key == pygame.K_ESCAPE:
                    if self.state == "menu":
                        self.running = False       # Esc in the menu quits
                    elif self.state == "shop":
                        self.shop.close()          # Esc in the shop just leaves it
                    else:
                        self.open_menu()           # Esc in a stage: back to the menu
            elif event.type == pygame.KEYUP:
                self.just_released.add(event.key)

    def update_scenery(self):
        """Trees, props and effects - everything except the player, enemies and arrows."""
        for sprite in self.all_sprites:
            if sprite not in self.actors and sprite not in self.projectiles:
                sprite.update()

    def update(self):
        self.keys = pygame.key.get_pressed()
        if self.state == "menu":
            self.main_menu.update(self.dt)
            return
        self.title_timer = max(0.0, self.title_timer - self.dt)

        if self.state == "victory":
            if pygame.K_r in self.just_pressed:
                self.load_level(0)
            elif any(k in self.just_pressed for k in (pygame.K_RETURN, pygame.K_KP_ENTER)):
                self.open_menu()
            else:
                self.update_scenery()
            return
        if self.state == "defeat":
            self.state_timer += self.dt
            if self.defeat_sound_timer is not None:
                self.defeat_sound_timer -= self.dt
                if self.defeat_sound_timer <= 0:
                    self.audio.play(settings.DEFEAT_SOUND)     # once
                    self.defeat_sound_timer = None
            if self.defeat_message_shown and any(
                    k in self.just_pressed for k in (pygame.K_RETURN, pygame.K_KP_ENTER)):
                self.audio.stop(settings.DEFEAT_SOUND, fade_ms=settings.DEFEAT_SOUND_FADE_MS)
                self.load_level(0)                 # try again from the first stage
                return
            self.player.update()                   # bleeding, collapsing
            for enemy in list(self.enemies):
                enemy.stand_down_update()          # enemies just stand there now
            self.projectiles.update()              # arrows in flight land
            self.update_scenery()                  # trees, blood, effects
            self.camera.update()
            self.health_bar.update(self.dt)
            return
        if self.state == "stage_clear":            # world pauses, message shows
            self.state_timer -= self.dt
            self.update_scenery()
            if self.state_timer <= 0:
                self.load_level(self.level_index + 1)
            return

        if self.in_cutscene:
            # the cutscene drives the ninja, the enemies and the camera;
            # scenery (swaying trees) and effects keep animating as usual
            self.cutscene.update(self.dt)
            self.update_scenery()
            return
        self.start_music()     # first gameplay frame (intro finished or skipped)
        if self.state == "shop":                   # the world pauses while you browse
            self.shop.update(self.dt)
            return
        if self.wheel and not self.player.dead:
            self.weapon_bar.scroll(-self.wheel)    # wheel down = next weapon
        self.weapon_bar.update(self.dt)
        self.all_sprites.update()
        if self.arena:
            self.arena.update(self.dt)         # rune seal, boss cutscene trigger
        self.camera.update()   # after sprites, so it follows this frame's position
        self.health_bar.update(self.dt)

        trader = self.trader_nearby()
        if trader and pygame.K_e in self.just_pressed and self.state == "playing":
            self.open_shop(trader)
            return

        if (self.state == "playing" and self.exit_gate and not self.in_cutscene
                and (self.arena is None or self.arena.exit_open)
                and self.player.hitbox.colliderect(self.exit_gate.trigger)):
            self.complete_level()

    # ------------------------------------------------------------ drawing
    def draw(self):
        if self.state == "menu":
            self.main_menu.draw(self.screen)
            pygame.display.flip()
            return
        self.background.draw(self.screen, self.camera.render_pos)   # scrolls slower = parallax
        self.tilemap.draw(self.screen, self.camera.offset)
        self.draw_group(self.background_decor)
        self.draw_group(self.pickups)
        self.draw_group(self.effects_back)
        self.draw_group(self.actors)
        self.draw_group(self.projectiles)
        self.draw_group(self.effects_front)
        self.draw_group(self.foreground_decor)
        if self.level.get("night"):
            self.screen.blit(self.night_veil(), (0, 0))  # darkens the world, not the HUD
        if self.arena:
            self.arena.draw_world(self.screen, self.camera)   # glowing seal (over the veil)
        if self.in_cutscene:
            self.cutscene.draw(self.screen)             # letterbox bars, no HUD
        elif self.state in ("playing", "shop"):
            self.draw_enemy_bars()
            self.draw_trade_prompt()
            self.draw_hud()                             # screen space
            if self.arena:
                self.arena.draw_hud(self.screen)        # boss health bar, seal hint
            if self.state == "playing":
                self.weapon_bar.draw(self.screen)
            if self.state == "shop":
                self.shop.draw(self.screen)
        elif self.state == "defeat":
            self.draw_defeat()
        self.draw_stage_title()
        if self.state == "stage_clear":
            self.draw_banner("Stage clear!", f"Next: {LEVELS[self.level_index + 1]['name']}")
        elif self.state == "victory":
            self.draw_banner("Victory!", "All stages cleared  -  Enter: main menu   R: play again")
        pygame.display.flip()

    def night_veil(self):
        if getattr(self, "_night_veil", None) is None:
            self._night_veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            self._night_veil.fill(settings.NIGHT_TINT)
        return self._night_veil

    def draw_group(self, group):
        """Draw a sprite group shifted by the camera, skipping off-screen sprites."""
        view = self.camera.view_rect
        for sprite in group:
            if sprite.rect.colliderect(view):
                self.screen.blit(sprite.image, self.camera.apply(sprite.rect))

    def draw_enemy_bars(self):
        view = self.camera.view_rect
        for enemy in self.enemies:
            if getattr(enemy, "BOSS", False):
                continue                        # the boss has his own big bar
            if enemy.rect.colliderect(view):
                draw_enemy_bar(self.screen, enemy, self.camera)

    def draw_text(self, font, text, center, color=(250, 244, 232), alpha=255):
        shadow = font.render(text, True, (14, 12, 22))
        label = font.render(text, True, color)
        for img, (dx, dy) in ((shadow, (3, 3)), (label, (0, 0))):
            img.set_alpha(alpha)
            self.screen.blit(img, img.get_rect(center=(center[0] + dx, center[1] + dy)))

    def draw_stage_title(self):
        """'Stage 2 - Bamboo Valley' at the start of a level, fading out.
        Near the top during the intro; lower down (clear of the HUD) in gameplay."""
        if self.title_timer <= 0 or self.state != "playing":
            return
        alpha = round(255 * min(1.0, self.title_timer / 0.6))
        w = self.screen.get_width()
        y = 92 if self.in_cutscene else 190
        self.draw_text(self.font, f"STAGE {self.level_index + 1}", (w // 2, y), alpha=alpha)
        self.draw_text(self.big_font, self.level["name"], (w // 2, y + 40), alpha=alpha)

    def draw_defeat(self):
        """The screen darkens (with a red tint) while he collapses, then the message."""
        w, h = self.screen.get_size()
        t = min(1.0, self.state_timer / settings.DEFEAT_FADE_TIME)
        shade = pygame.Surface((w, h), pygame.SRCALPHA)
        shade.fill((40, 0, 4, round(settings.DEFEAT_DARKEN * t)))
        self.screen.blit(shade, (0, 0))
        self.health_bar.draw(self.screen)              # empty bar stays visible
        if not self.defeat_message_shown:
            return
        shown = self.player.lying_time - settings.DEFEAT_MESSAGE_DELAY
        alpha = round(255 * min(1.0, shown / 0.8))
        self.draw_text(self.big_font, "You have been defeated...", (w // 2, h // 2 - 30),
                       color=(232, 70, 64), alpha=alpha)
        self.draw_text(self.font, "Try again?", (w // 2, h // 2 + 26), alpha=alpha)
        if shown > 0.8 and int(shown * 2) % 2 == 0:     # blinking prompt
            self.draw_text(self.font, "Press Enter", (w // 2, h // 2 + 60), color=(200, 196, 188))

    def draw_banner(self, title, subtitle):
        w, h = self.screen.get_size()
        shade = pygame.Surface((w, 150), pygame.SRCALPHA)
        shade.fill((8, 6, 10, 170))
        self.screen.blit(shade, (0, h // 2 - 75))
        self.draw_text(self.big_font, title, (w // 2, h // 2 - 20))
        self.draw_text(self.font, subtitle, (w // 2, h // 2 + 34))

    def draw_trade_prompt(self):
        """A small [E] Trade bubble above the trader while the ninja is close."""
        trader = self.trader_nearby()
        if not trader or self.state != "playing":
            return
        x, y = self.camera.apply(trader.rect).midtop
        bob = round(2 * math.sin(pygame.time.get_ticks() / 180))
        key = self.font.render("E", True, (30, 24, 30))
        label = self.font.render("Trade", True, (250, 244, 232))
        shadow = self.font.render("Trade", True, (14, 12, 22))
        cap = pygame.Rect(0, 0, 28, 28)
        total = cap.width + 8 + label.get_width()
        cap.topleft = (x - total // 2, y - 40 + bob)
        pygame.draw.rect(self.screen, (250, 244, 232), cap, border_radius=4)
        pygame.draw.rect(self.screen, (30, 24, 30), cap, 2, border_radius=4)
        self.screen.blit(key, key.get_rect(center=cap.center))
        lx = cap.right + 8
        self.screen.blit(shadow, (lx + 2, cap.centery - label.get_height() // 2 + 2))
        self.screen.blit(label, (lx, cap.centery - label.get_height() // 2))

    def draw_hud(self):
        coins = draw_coin_counter(self.screen, self.coin_icon, self.font, self.progress.coins,
                                  topright=(self.screen.get_width() - 20, 18))
        # current weapon, left of the coins (scroll the mouse wheel to switch)
        slot = pygame.Rect(0, 0, 40, 40)
        slot.midright = (coins.left - 18, coins.centery + 2)
        pygame.draw.rect(self.screen, (20, 16, 24), slot, border_radius=4)
        pygame.draw.rect(self.screen, (214, 52, 64), slot, 2, border_radius=4)
        icon = weapon_icon(self.player.weapon, 2)
        self.screen.blit(icon, icon.get_rect(center=slot.center))
        bar = self.health_bar.draw(self.screen)       # top-left health bar
        p = self.player
        anim = p.animation
        lines = [
            "A/D walk  Shift run  W/Space jump x2  LMB attack  RMB dash  Wheel weapon  Esc menu",
            f"stage {self.level_index + 1}/{len(LEVELS)}: {self.level['name']}   "
            f"state: {p.state}   frame: {anim.index + 1}/{len(anim.frames)}   "
            f"air jumps: {p.air_jumps_left}",
        ]
        color = (206, 212, 232) if self.level.get("night") else (30, 24, 30)   # readable at night
        for i, line in enumerate(lines):
            self.screen.blit(self.font.render(line, True, color), (16, bar.bottom + 10 + i * 26))
