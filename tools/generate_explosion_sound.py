"""Generate assets/audio/explosion.wav (stdlib only): a low thump plus a
crackling noise burst that dies away - the ninja's bomb.

Usage (from the repo root):
    python tools/generate_explosion_sound.py
"""

import math
import os
import random
import struct
import wave

RATE = 44100
LENGTH = 1.1        # seconds


def main(path=os.path.join("assets", "audio", "explosion.wav")):
    rnd = random.Random("boom")
    n = int(RATE * LENGTH)
    samples = []
    lp1 = lp2 = 0.0                       # two one-pole low-pass filters on the noise
    phase = 0.0
    for i in range(n):
        t = i / RATE
        # noise burst: sharp attack, long decay; filter closes over time (bright -> rumble)
        noise = rnd.uniform(-1, 1)
        cutoff = 0.35 * math.exp(-t * 5) + 0.03
        lp1 += cutoff * (noise - lp1)
        lp2 += cutoff * (lp1 - lp2)
        burst = lp2 * 3.2 * math.exp(-t * 4.2) * min(1.0, t / 0.004)
        # crackle: sparse random pops in the first half
        if t < 0.5 and rnd.random() < 0.002:
            burst += rnd.uniform(-0.5, 0.5) * math.exp(-t * 6)
        # thump: a sine sweeping down from 110 Hz to 35 Hz
        freq = 35 + 75 * math.exp(-t * 9)
        phase += 2 * math.pi * freq / RATE
        thump = math.sin(phase) * 0.9 * math.exp(-t * 6)
        v = math.tanh((burst + thump) * 1.4)          # soft clip = punchier
        samples.append(v)

    peak = max(abs(v) for v in samples) or 1.0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", round(v / peak * 0.92 * 32767)) for v in samples))
    print(path)


if __name__ == "__main__":
    main()
