"""Sound effects and background music.

Every .wav/.ogg/.mp3 file in assets/audio/ is loaded once and played by its name:

    game.audio.play("jump")             # assets/audio/jump.wav
    game.audio.play("attack", volume=0.8)
    game.audio.stop("intro_scene_sound", fade_ms=600)

Files listed in settings.MUSIC_FILES are NOT preloaded; they're streamed:

    game.audio.play_music("level_bg_music")     # loops, at MUSIC_VOLUME
    game.audio.stop_music(fade_ms=800)

If no audio device is available, the game keeps running without sound.
"""

import os

import pygame

from src import settings

AUDIO_DIR = os.path.join(settings.ASSETS_DIR, "audio")


class Audio:
    def __init__(self):
        self.sounds = {}
        self.music_files = {}          # music name -> file path (streamed, not loaded)
        self.current_music = None
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
            if ext.lower() not in (".wav", ".ogg", ".mp3"):
                continue
            if stem in settings.MUSIC_FILES:
                self.music_files[stem] = os.path.join(AUDIO_DIR, name)
            else:
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
        return channel

    def stop(self, name, fade_ms=0):
        """Stop a sound (fading out over fade_ms milliseconds)."""
        if not self.enabled or name not in self.sounds:
            return
        if fade_ms > 0:
            self.sounds[name].fadeout(fade_ms)
        else:
            self.sounds[name].stop()

    # ------------------------------------------------------------ music
    def play_music(self, name, loop=True, fade_ms=0):
        """Stream a music file from assets/audio (restarts it from the beginning)."""
        if not self.enabled or name not in self.music_files:
            return
        pygame.mixer.music.load(self.music_files[name])
        pygame.mixer.music.set_volume(settings.MUSIC_VOLUME * settings.MASTER_VOLUME)
        pygame.mixer.music.play(loops=-1 if loop else 0, fade_ms=fade_ms)
        self.current_music = name

    def stop_music(self, fade_ms=0):
        if not self.enabled or self.current_music is None:
            return
        if fade_ms > 0:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()
        self.current_music = None
