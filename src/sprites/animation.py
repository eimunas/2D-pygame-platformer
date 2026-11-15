"""Frame loading and frame-based animation playback."""

import os

import pygame


def load_frames(folder, scale=1):
    """Load every PNG in a folder (sorted by name) and scale it up."""
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    frames = []
    for name in files:
        img = pygame.image.load(os.path.join(folder, name)).convert_alpha()
        w, h = img.get_size()
        frames.append(pygame.transform.scale(img, (w * scale, h * scale)))
    if not frames:
        raise FileNotFoundError(f"No PNG frames found in {folder}")
    return frames


class Animation:
    """Loops through a list of frames at a fixed frame rate."""

    def __init__(self, frames, fps):
        self.frames = frames
        self.frame_time = 1.0 / fps
        self.timer = 0.0
        self.index = 0

    def reset(self):
        self.timer = 0.0
        self.index = 0

    def update(self, dt):
        self.timer += dt
        while self.timer >= self.frame_time:
            self.timer -= self.frame_time
            self.index = (self.index + 1) % len(self.frames)

    @property
    def image(self):
        return self.frames[self.index]
