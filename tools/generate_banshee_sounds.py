"""Generate the banshee's sounds (stdlib only). Replace either file with a real
recording of the same name to use that instead.

Usage (from the repo root):
    python tools/generate_banshee_sounds.py

Output:
    assets/audio/banshee_scream.wav   ~1 s eerie wail rising in pitch (her attack)
    assets/audio/banshee_death.wav    ~1.3 s wail falling away as she fades
"""

import math
import os
import random
import struct
import wave

RATE = 44100


def wail(length, f_from, f_to, seed, rise_time=0.12, breath=0.25):
    """Two slightly detuned voices with vibrato and a few harmonics, plus a
    breathy noise layer; pitch glides from f_from to f_to."""
    rnd = random.Random(seed)
    n = int(RATE * length)
    out = []
    phases = [0.0, 0.0]
    lp = 0.0
    for i in range(n):
        t = i / RATE
        k = t / length
        f = f_from * (f_to / f_from) ** k                  # exponential glide
        vib = 1 + 0.035 * math.sin(2 * math.pi * 6.5 * t) * min(1.0, t * 4)
        v = 0.0
        for j, detune in enumerate((1.0, 1.013)):
            phases[j] += 2 * math.pi * f * vib * detune / RATE
            p = phases[j]
            v += math.sin(p) + 0.45 * math.sin(2 * p + 0.3) + 0.22 * math.sin(3 * p + 1.1)
        v *= 0.32
        lp += 0.25 * (rnd.uniform(-1, 1) - lp)             # breath (soft noise)
        v += lp * breath
        env = min(1.0, t / rise_time) * (1 - k) ** 0.6
        out.append(math.tanh(v * env * 1.6))
    return out


def save(path, samples):
    peak = max(abs(v) for v in samples) or 1.0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", round(v / peak * 0.85 * 32767)) for v in samples))
    print(path)


def main(folder=os.path.join("assets", "audio")):
    save(os.path.join(folder, "banshee_scream.wav"), wail(1.0, 560, 1180, "scream"))
    save(os.path.join(folder, "banshee_death.wav"), wail(1.3, 940, 260, "death", rise_time=0.05, breath=0.4))


if __name__ == "__main__":
    main()
