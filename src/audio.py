"""Sound effects.

Every .wav/.ogg/.mp3 file in assets/audio/ is loaded once and played by its name:

    game.audio.play("jump")             # assets/audio/jump.wav
    game.audio.play("attack", volume=0.8)

If no audio device is available, the game keeps running without sound.
"""

import os

import pygame

from src import settings

AUDIO_DIR = os.path.join(settings.ASSETS_DIR, "audio")


class Audio:
    def __init__(self):
        self.sounds = {}
        self.enabled = pygame.mixer.get_init() is not None
        if not self.enabled:
            try:
                pygame.mixer.init()
                self.enabled = True
            except pygame.error as e:
                print(f"[audio] no sound device, running silently ({e})")
                return
        pygame.mixer.set_num_channels(16)   # enough for overlapping slashes/jumps

        if not os.path.isdir(AUDIO_DIR):
            return
        for name in sorted(os.listdir(AUDIO_DIR)):
            stem, ext = os.path.splitext(name)
            if ext.lower() in (".wav", ".ogg", ".mp3"):
                sound = pygame.mixer.Sound(os.path.join(AUDIO_DIR, name))
                sound.set_volume(settings.SOUND_VOLUMES.get(stem, 1.0) * settings.MASTER_VOLUME)
                self.sounds[stem] = sound

    def play(self, name, volume=None):
        """Play a sound by file name (without extension). Unknown names are ignored."""
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is None:
            return
        channel = sound.play()
        if channel is not None and volume is not None:
            channel.set_volume(volume)
