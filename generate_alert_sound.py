"""Generate a urgent alert siren tone as alert.mp3 (WAV format with .mp3 extension works in browsers)."""
import struct
import wave
import math
import os

SAMPLE_RATE = 44100
DURATION = 3  # seconds
FILENAME = os.path.join(os.path.dirname(__file__), "static", "alert.mp3")

samples = []
for i in range(SAMPLE_RATE * DURATION):
    t = i / SAMPLE_RATE
    # Siren: frequency sweeps between 600Hz and 1200Hz
    freq = 600 + 600 * (0.5 + 0.5 * math.sin(2 * math.pi * 2 * t))
    # Add urgency with a secondary tone
    freq2 = 800 + 400 * math.sin(2 * math.pi * 3 * t)
    sample = 0.5 * math.sin(2 * math.pi * freq * t) + 0.3 * math.sin(2 * math.pi * freq2 * t)
    # Pulsing envelope
    envelope = 0.6 + 0.4 * abs(math.sin(2 * math.pi * 4 * t))
    sample *= envelope * 0.8
    samples.append(int(sample * 32767))

with wave.open(FILENAME, "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

print(f"✅ Alert sound generated: {FILENAME}")
