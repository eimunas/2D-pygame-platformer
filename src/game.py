"""The Game class: owns pygame setup, shared state, and the main loop.

Pass the Game instance to any object that needs shared state, e.g.:

    class Enemy(pygame.sprite.Sprite):
        def __init__(self, game, pos):
            super().__init__(game.all_sprites, game.actors)
            self.game = game    # -> game.dt, game.keys, game.screen, game.tilemap, game.player ...
"""

import os

import pygame

from src import settings
from src.background import ParallaxBackground
from src.camera import Camera
from src.level import DEMO_LEVEL, load_level


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((settings.SCREEN_W, settings.SCREEN_H))
        pygame.display.set_caption(settings.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 20)

        # shared per-frame state, read by sprites through their `game` reference
        self.running = True
        self.dt = 0.0
        self.keys = pygame.key.get_pressed()   # keys held down right now
        self.just_pressed = set()              # keys pressed this frame
        self.just_released = set()             # keys released this frame
        self.mouse_just_pressed = set()        # mouse buttons clicked this frame (1 = left)

        # sprite groups
        self.all_sprites = pygame.sprite.Group()        # everything that gets update()
        self.background_decor = pygame.sprite.Group()   # trees: behind the player
        self.effects_back = pygame.sprite.Group()       # afterimages: behind actors
        self.actors = pygame.sprite.Group()             # player (and later enemies)
        self.effects_front = pygame.sprite.Group()      # slash streaks: in front of actors
        self.foreground_decor = pygame.sprite.Group()   # rocks: in front of the player

        # level: creates the tilemap, decorations and self.player
        self.player = None
        self.tilemap = load_level(self, DEMO_LEVEL)
        if self.player is None:
            raise ValueError("Level has no 'P' (player spawn)")

        self.camera = Camera(self, self.player)

        self.background = ParallaxBackground(self.screen.get_size())
        for path, factor in settings.BACKGROUND_LAYERS:
            self.background.add_layer(os.path.join(settings.ASSETS_DIR, path), factor=factor)

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
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_just_pressed.add(event.button)
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.just_pressed.add(event.key)
                if event.key == pygame.K_ESCAPE:
                    self.running = False
            elif event.type == pygame.KEYUP:
                self.just_released.add(event.key)

    def update(self):
        self.keys = pygame.key.get_pressed()
        self.all_sprites.update()
        self.camera.update()   # after sprites, so it follows this frame's position

    # ------------------------------------------------------------ drawing
    def draw(self):
        self.background.draw(self.screen, self.camera.render_pos)   # scrolls slower = parallax
        self.tilemap.draw(self.screen, self.camera.offset)
        self.draw_group(self.background_decor)
        self.draw_group(self.effects_back)
        self.draw_group(self.actors)
        self.draw_group(self.effects_front)
        self.draw_group(self.foreground_decor)
        self.draw_hud()                                 # screen space
        pygame.display.flip()

    def draw_group(self, group):
        """Draw a sprite group shifted by the camera, skipping off-screen sprites."""
        view = self.camera.view_rect
        for sprite in group:
            if sprite.rect.colliderect(view):
                self.screen.blit(sprite.image, self.camera.apply(sprite.rect))

    def draw_hud(self):
        p = self.player
        anim = p.animation
        lines = [
            "A/D: walk  Shift: run  W/Space: jump (x2)  LMB: attack  RMB: dash attack  Esc: quit",
            f"state: {p.state}   frame: {anim.index + 1}/{len(anim.frames)}   "
            f"on ground: {p.on_ground}   air jumps: {p.air_jumps_left}",
        ]
        for i, line in enumerate(lines):
            self.screen.blit(self.font.render(line, True, (30, 24, 30)), (16, 16 + i * 26))
