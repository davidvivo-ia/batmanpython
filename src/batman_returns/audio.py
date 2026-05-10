"""Procedural SFX synthesised at startup with numpy. No .wav files shipped.

A small helper builds short pygame Sound objects from waveforms. Inspired by
the original sound IDs in BATMAN.EQU (SFX_BDFIRE_A, BDHIT_A, etc.).
"""

from __future__ import annotations

from functools import cache
from typing import Final

import numpy as np
import pygame

SAMPLE_RATE: Final = 44100


class _SilentSound:
    """No-op stand-in used when the mixer isn't initialised."""
    def play(self, *_: object, **__: object) -> None:
        pass

    def set_volume(self, *_: object) -> None:
        pass

    def get_length(self) -> float:
        return 0.0


def _to_sound(wave: np.ndarray, volume: float = 0.4):
    if not pygame.mixer.get_init():
        return _SilentSound()
    wave = np.clip(wave * volume, -1.0, 1.0)
    samples = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((samples, samples))
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _adsr(n: int, attack: float = 0.02, decay: float = 0.4) -> np.ndarray:
    a = max(1, int(n * attack))
    d = max(1, int(n * decay))
    s = max(1, n - a - d)
    return np.concatenate([
        np.linspace(0, 1, a),
        np.linspace(1, 0.7, d),
        np.linspace(0.7, 0, s),
    ])[:n]


def _tone(freq: float, dur: float, *, shape: str = "sine", noise: float = 0.0) -> np.ndarray:
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, endpoint=False)
    match shape:
        case "sine":
            wave = np.sin(2 * np.pi * freq * t)
        case "square":
            wave = np.sign(np.sin(2 * np.pi * freq * t))
        case "saw":
            wave = 2 * (t * freq - np.floor(0.5 + t * freq))
        case "tri":
            wave = 2 * np.abs(2 * (t * freq - np.floor(0.5 + t * freq))) - 1
        case _:
            wave = np.zeros(n)
    if noise > 0:
        wave = (1 - noise) * wave + noise * (np.random.uniform(-1, 1, n))
    return wave * _adsr(n)


@cache
def punch() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.12)
    t = np.linspace(0, 0.12, n, endpoint=False)
    sweep = 220 * np.exp(-t * 14)
    wave = np.sign(np.sin(2 * np.pi * sweep * t)) * _adsr(n, 0.01, 0.3)
    wave += np.random.uniform(-0.4, 0.4, n) * np.exp(-t * 22)
    return _to_sound(wave, 0.5)


@cache
def kick() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.18)
    t = np.linspace(0, 0.18, n, endpoint=False)
    sweep = 140 * np.exp(-t * 8)
    wave = np.sin(2 * np.pi * sweep * t) * _adsr(n, 0.01, 0.4)
    wave += np.random.uniform(-0.3, 0.3, n) * np.exp(-t * 14)
    return _to_sound(wave, 0.55)


@cache
def batarang() -> pygame.mixer.Sound:
    # Sweeping whoosh
    n = int(SAMPLE_RATE * 0.25)
    t = np.linspace(0, 0.25, n, endpoint=False)
    freq = 800 + 400 * np.sin(2 * np.pi * 14 * t)
    wave = np.sin(2 * np.pi * freq * t) * _adsr(n, 0.05, 0.5)
    return _to_sound(wave, 0.35)


@cache
def jump() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.18)
    t = np.linspace(0, 0.18, n, endpoint=False)
    freq = 300 + 700 * t / 0.18
    wave = np.sign(np.sin(2 * np.pi * freq * t)) * _adsr(n)
    return _to_sound(wave, 0.3)


@cache
def hit() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.15)
    wave = np.random.uniform(-1, 1, n) * _adsr(n, 0.005, 0.3)
    return _to_sound(wave, 0.5)


@cache
def hurt() -> pygame.mixer.Sound:
    return _to_sound(_tone(180, 0.25, shape="saw"), 0.45)


@cache
def pickup() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.18)
    t = np.linspace(0, 0.18, n, endpoint=False)
    wave = (
        np.sin(2 * np.pi * 880 * t)
        + 0.5 * np.sin(2 * np.pi * 1320 * t * (1 + t * 2))
    )
    return _to_sound(wave * _adsr(n), 0.4)


@cache
def boss_roar() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.5)
    t = np.linspace(0, 0.5, n, endpoint=False)
    base = 80 + 30 * np.sin(2 * np.pi * 6 * t)
    wave = np.sign(np.sin(2 * np.pi * base * t))
    wave += np.random.uniform(-0.3, 0.3, n)
    return _to_sound(wave * _adsr(n, 0.05, 0.6), 0.55)


@cache
def fire() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.4)
    wave = np.random.uniform(-1, 1, n)
    # Lowpass-ish: cumulative average
    kernel = np.ones(50) / 50
    wave = np.convolve(wave, kernel, mode="same")
    return _to_sound(wave * _adsr(n, 0.02, 0.6), 0.4)


@cache
def death() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.7)
    t = np.linspace(0, 0.7, n, endpoint=False)
    freq = 400 * np.exp(-t * 2.0)
    wave = np.sin(2 * np.pi * freq * t)
    return _to_sound(wave * _adsr(n, 0.05, 0.6), 0.5)


@cache
def thunder() -> pygame.mixer.Sound:
    n = int(SAMPLE_RATE * 0.9)
    wave = np.random.uniform(-1, 1, n)
    # Cumulative low-pass (heavy) for rumble
    kernel = np.ones(120) / 120
    wave = np.convolve(wave, kernel, mode="same")
    env = np.exp(-np.linspace(0, 4, n))
    return _to_sound(wave * env, 0.6)


@cache
def title_jingle() -> pygame.mixer.Sound:
    notes = [(523, 0.15), (659, 0.15), (784, 0.15), (1047, 0.4)]
    parts = [_tone(f, d, shape="square") for f, d in notes]
    wave = np.concatenate(parts)
    return _to_sound(wave, 0.3)


_sfx_volume = 1.0


def init() -> None:
    """Init mixer (must be called before pygame.display.set_mode for safety).

    Tolerates systems without an audio device (no ALSA, headless server, etc.):
    in that case the mixer simply isn't initialised and every play() call
    becomes a no-op via pygame.mixer.get_init() guards in the rest of the code.
    """
    try:
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
        pygame.mixer.init()
    except pygame.error as exc:
        print(f"[audio] mixer not available ({exc}); running silent.")


def set_sfx_volume(v: float) -> None:
    """0.0..1.0; applied to all currently-cached sounds."""
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, v))
    for fn in (
        punch, kick, batarang, jump, hit, hurt, pickup,
        boss_roar, fire, death, title_jingle, thunder,
    ):
        try:
            fn().set_volume(_sfx_volume)
        except Exception:
            pass
