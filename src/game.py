"""The Game class: owns pygame setup, shared state, and the main loop.

Pass the Game instance to any object that needs shared state, e.g.:

    class Enemy(pygame.sprite.Sprite):
        def __init__(self, game, pos):
            super().__init__(game.all_sprites)
            self.game = game          # -> game.dt, game.keys, game.screen, game.player ...
"""

import pygame

from src import settings
from src.sprites import Player


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
        self.keys = pygame.key.get_pressed()

        # sprite groups
        self.all_sprites = pygame.sprite.Group()

        # entities
        self.player = Player(self, (settings.SCREEN_W // 2, settings.GROUND_Y))

    # ------------------------------------------------------------ loop
    def run(self):
        while self.running:
            self.dt = self.clock.tick(settings.FPS) / 1000.0
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

    def update(self):
        self.keys = pygame.key.get_pressed()
        self.all_sprites.update()

    # ------------------------------------------------------------ drawing
    def draw(self):
        self.draw_background()
        self.all_sprites.draw(self.screen)
        self.draw_hud()
        pygame.display.flip()

    def draw_background(self):
        w, h, gy = settings.SCREEN_W, settings.SCREEN_H, settings.GROUND_Y
        self.screen.fill((236, 214, 180))                                  # dusk sky
        pygame.draw.circle(self.screen, (214, 72, 52), (760, 170), 70)     # red sun
        pygame.draw.rect(self.screen, (64, 52, 60), (0, gy, w, h - gy))    # ground
        pygame.draw.line(self.screen, (40, 30, 36), (0, gy), (w, gy), 3)

    def draw_hud(self):
        anim = self.player.animation
        lines = [
            "A / D: walk    Shift + A / D: run    Esc: quit",
            f"state: {self.player.state}   frame: {anim.index + 1}/{len(anim.frames)}",
        ]
        for i, line in enumerate(lines):
            self.screen.blit(self.font.render(line, True, (30, 24, 30)), (16, 16 + i * 26))
