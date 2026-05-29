import math
import os
import wave

import numpy as np

SAMPLE_RATE = 44100


def _write_wav(path: str, samples: np.ndarray) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    pcm    = (samples * 32767).astype(np.int16)
    stereo = np.stack([pcm, pcm], axis=1)
    with wave.open(path, "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(stereo.tobytes())
    print(f"Created {path}")


def _make_kick(duration: float = 0.6) -> np.ndarray:
    """bass punch: pitch drops 150 → 40 Hz + low thump."""
    t     = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freqs = np.linspace(150, 40, len(t))
    phase = np.cumsum(2 * math.pi * freqs / SAMPLE_RATE)
    tone  = np.sin(phase)
    # Hard transient click on attack
    click = np.random.default_rng(0).uniform(-1.0, 1.0, len(t)) * np.exp(-80 * t)
    env   = np.exp(-6.0 * t)
    return (tone * 0.85 + click * 0.2) * env

#snare
def _make_snare(duration: float = 0.3) -> np.ndarray:
    t     = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    tone  = np.sin(2 * math.pi * 180 * t) * 0.35
    noise = np.random.default_rng(1).uniform(-1.0, 1.0, len(t)) * 0.75
    env   = np.exp(-13.0 * t)
    return (tone + noise) * env * 0.82

#hihat
def _make_hihat(duration: float = 0.12) -> np.ndarray:
    t     = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    noise = np.random.default_rng(2).uniform(-1.0, 1.0, len(t))
    hf    = np.sin(2 * math.pi * 9000 * t) * 0.5
    env   = np.exp(-25.0 * t)
    return (noise * 0.55 + hf) * env * 0.72

#tom
def _make_tom(duration: float = 0.5) -> np.ndarray:
    t     = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    freqs = np.linspace(120, 55, len(t))
    phase = np.cumsum(2 * math.pi * freqs / SAMPLE_RATE)
    tone  = np.sin(phase)
    noise = np.random.default_rng(3).uniform(-1.0, 1.0, len(t)) * 0.06
    env   = np.exp(-7.5 * t)
    return (tone + noise) * env * 0.85


def main() -> None:
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
    os.makedirs(out_dir, exist_ok=True)

    print("Generating drum sounds")
    _write_wav(os.path.join(out_dir, "kick.wav"),  _make_kick())
    _write_wav(os.path.join(out_dir, "snare.wav"), _make_snare())
    _write_wav(os.path.join(out_dir, "hihat.wav"), _make_hihat())
    _write_wav(os.path.join(out_dir, "tom.wav"),   _make_tom())
    print("Don")


if __name__ == "__main__":
    main()
