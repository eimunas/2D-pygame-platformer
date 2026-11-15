"""Image/frame loading (cached) and frame-based animation playback."""

import os

import pygame

_cache = {}


def load_image(path, scale=1):
    """Load one PNG and scale it up. Cached, so many sprites can share it."""
    key = (path, scale)
    if key not in _cache:
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        _cache[key] = pygame.transform.scale(img, (w * scale, h * scale))
    return _cache[key]


def load_frames(folder, scale=1):
    """Load every PNG in a folder (sorted by name) and scale it up."""
    files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".png"))
    if not files:
        raise FileNotFoundError(f"No PNG frames found in {folder}")
    return [load_image(os.path.join(folder, name), scale) for name in files]


class Animation:
    """Plays a list of frames at a fixed frame rate.

    loop=True  -> repeats forever
    loop=False -> plays once, then `finished` becomes True
    """

    def __init__(self, frames, fps, start=0, loop=True):
        self.frames = frames
        self.frame_time = 1.0 / fps
        self.loop = loop
        self.timer = 0.0
        self.index = start % len(frames)
        self.finished = False

    def reset(self):
        self.timer = 0.0
        self.index = 0
        self.finished = False

    def update(self, dt):
        if self.finished:
            return
        self.timer += dt
        while self.timer >= self.frame_time:
            self.timer -= self.frame_time
            if self.index + 1 < len(self.frames):
                self.index += 1
            elif self.loop:
                self.index = 0
            else:
                self.finished = True   # stay on the last frame
                break

    @property
    def image(self):
        return self.frames[self.index]
