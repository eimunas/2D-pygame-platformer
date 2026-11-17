"""Generate assets/audio/shinobi_spot.wav (stdlib only): the shinobi noticing the
ninja - a quick, quiet dagger draw (a soft swish, then a light metallic "shing").
Deliberately subtler than the samurai's shout.

Usage (from the repo root):
    python tools/generate_shinobi_spot_sound.py
"""

import math
import os
import random
import struct
import wave

RATE = 44100
LENGTH = 0.55       # seconds
RING_START = 0.07   # the blade clears the sheath after the swish


def main(path=os.path.join("assets", "audio", "shinobi_spot.wav")):
    rnd = random.Random("shing")
    n = int(RATE * LENGTH)
    # inharmonic partials = small metal blade: (Hz, amplitude, decay per second)
    partials = [(2350, 0.50, 11), (3610, 0.32, 14), (5190, 0.20, 19), (7020, 0.10, 26)]
    hp_prev_in = hp_prev_out = lp = 0.0
    samples = []
    for i in range(n):
        t = i / RATE

        # swish: band-passed noise that swells and fades over ~90 ms
        noise = rnd.uniform(-1, 1)
        hp_out = 0.96 * (hp_prev_out + noise - hp_prev_in)       # high-pass (drop the rumble)
        hp_prev_in, hp_prev_out = noise, hp_out
        lp += 0.35 * (hp_out - lp)                               # low-pass (soften the hiss)
        env = math.sin(math.pi * min(1.0, t / 0.09)) if t < 0.09 else 0.0
        swish = lp * 0.55 * env

        # shing: a light ring with a slight upward bend, fading fast
        ring = 0.0
        if t >= RING_START:
            tr = t - RING_START
            attack = min(1.0, tr / 0.003)
            bend = 1 + 0.015 * (1 - math.exp(-tr * 30))
            for freq, amp, decay in partials:
                ring += amp * math.sin(2 * math.pi * freq * bend * tr) * math.exp(-tr * decay)
            ring *= attack * 0.6

        samples.append(swish + ring)

    peak = max(abs(v) for v in samples) or 1.0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", round(v / peak * 0.85 * 32767)) for v in samples))
    print(path)


if __name__ == "__main__":
    main()
