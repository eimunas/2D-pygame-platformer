"""Generate the guardian's shield sounds (stdlib only). Replace either file with a
real recording of the same name to use that instead.

Usage (from the repo root):
    python tools/generate_guardian_sounds.py

Output:
    assets/audio/shield_block.wav   short metallic clang (an arrow or blade hits the shield)
    assets/audio/shield_break.wav   heavy crack + clatter (the shield breaks)
"""

import math
import os
import random
import struct
import wave

RATE = 44100


def clang(length, freqs, seed, noise=0.5, decay=9.0):
    """Inharmonic metal partials with fast decay, plus a click of noise at the start."""
    rnd = random.Random(seed)
    out = []
    for i in range(int(RATE * length)):
        t = i / RATE
        v = sum(a * math.sin(2 * math.pi * f * t) * math.exp(-decay * t * (1 + k * 0.4))
                for k, (f, a) in enumerate(freqs))
        v += rnd.uniform(-1, 1) * noise * math.exp(-60 * t)
        out.append(v)
    return out


def crack(length, seed):
    """A splintering crack: a burst of noise, then a few smaller clatters."""
    rnd = random.Random(seed)
    out = [0.0] * int(RATE * length)
    hits = [(0.0, 1.0)] + [(rnd.uniform(0.08, length - 0.25), rnd.uniform(0.25, 0.5)) for _ in range(5)]
    for start, amp in hits:
        part = clang(0.25, [(rnd.uniform(500, 900), 0.6), (rnd.uniform(1300, 2100), 0.4),
                            (rnd.uniform(2600, 3400), 0.25)], rnd.random(), noise=1.4, decay=18)
        s = int(start * RATE)
        for j, v in enumerate(part):
            if s + j < len(out):
                out[s + j] += v * amp
    lp = 0.0
    for i in range(int(0.35 * RATE)):                      # low thud under the crack
        lp += 0.02 * (rnd.uniform(-1, 1) - lp)
        out[i] += lp * 6 * math.exp(-8 * i / RATE)
    return out


def save(path, samples):
    peak = max(abs(v) for v in samples) or 1.0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", round(math.tanh(v / peak * 1.3) * 0.8 * 32767))
                               for v in samples))
    print(path)


def main(folder=os.path.join("assets", "audio")):
    save(os.path.join(folder, "shield_block.wav"),
         clang(0.45, [(1180, 1.0), (1730, 0.6), (2890, 0.45), (4120, 0.2)], "block"))
    save(os.path.join(folder, "shield_break.wav"), crack(0.9, "break"))


if __name__ == "__main__":
    main()
