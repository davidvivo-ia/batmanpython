"""Procedural chiptune music — three short loops, one per stage.

Each track is a list of (note_in_semitones_from_A4, duration_in_beats) tuples
played on a square-wave lead with a triangle bass an octave below. Built once
at startup and looped via pygame.mixer.Channel so the SFX channels stay free.
"""

from __future__ import annotations

from functools import cache
from typing import Final

import numpy as np
import pygame

SAMPLE_RATE: Final = 44100
BPM: Final = 132
SEC_PER_BEAT: Final = 60.0 / BPM


def _hz(semitones_from_a4: int) -> float:
    return 440.0 * 2 ** (semitones_from_a4 / 12)


def _square(freq: float, n: int, duty: float = 0.5) -> np.ndarray:
    t = np.arange(n) / SAMPLE_RATE
    phase = (t * freq) % 1.0
    return np.where(phase < duty, 1.0, -1.0)


def _triangle(freq: float, n: int) -> np.ndarray:
    t = np.arange(n) / SAMPLE_RATE
    phase = (t * freq) % 1.0
    return 4 * np.abs(phase - 0.5) - 1


def _env(n: int, attack: int = 200, release: int = 2000) -> np.ndarray:
    env = np.ones(n, dtype=np.float32)
    a = min(attack, n // 4)
    r = min(release, n // 2)
    env[:a] = np.linspace(0, 1, a)
    env[-r:] *= np.linspace(1, 0, r)
    return env


def _render_track(notes: list[tuple[int | None, float]], wave_fn) -> np.ndarray:
    out = []
    for semi, beats in notes:
        n = int(beats * SEC_PER_BEAT * SAMPLE_RATE)
        if semi is None or n <= 0:
            out.append(np.zeros(n, dtype=np.float32))
            continue
        wave = wave_fn(_hz(semi), n) * _env(n) * 0.18
        out.append(wave.astype(np.float32))
    return np.concatenate(out)


# Tracks: notes are semitones from A4 (440 Hz). 1.0 = quarter beat.
# Stage 1: dark Gotham theme (A minor, walking bass)
GOTHAM_LEAD: list[tuple[int | None, float]] = [
    (0, 1), (3, 1), (7, 1), (3, 1),
    (-2, 1), (3, 1), (7, 1), (3, 1),
    (5, 1), (8, 1), (12, 1), (8, 1),
    (3, 1), (7, 1), (10, 1), (7, 1),
]
GOTHAM_BASS: list[tuple[int | None, float]] = [
    (-12, 2), (-9, 2), (-14, 2), (-9, 2),
    (-7, 2), (-4, 2), (-12, 2), (-9, 2),
]

# Stage 2: ICE PLAZA (mysterious, suspended)
ICE_LEAD = [
    (12, 2), (10, 1), (12, 1), (15, 2), (12, 2),
    (10, 2), (8, 1), (10, 1), (12, 4),
]
ICE_BASS = [(-12, 4), (-15, 4), (-10, 4), (-12, 4)]

# Stage 3: PENGUIN'S LAIR (driving)
LAIR_LEAD = [
    (3, 0.5), (3, 0.5), (7, 1), (3, 0.5), (3, 0.5), (10, 1),
    (12, 0.5), (10, 0.5), (7, 1), (5, 0.5), (3, 0.5), (0, 1),
    (3, 0.5), (3, 0.5), (7, 1), (3, 0.5), (3, 0.5), (12, 1),
    (15, 0.5), (12, 0.5), (10, 1), (7, 1), (3, 1),
]
LAIR_BASS = [
    (-12, 1), (-9, 1), (-12, 1), (-7, 1),
    (-12, 1), (-9, 1), (-12, 1), (-5, 1),
] * 2


@cache
def _track(stage_idx: int) -> pygame.mixer.Sound:
    # Cycle through the three composed loops by mood:
    #   Gotham/Streets/Rooftops/Sewers/Docks → dark walking-bass
    #   ICE PLAZA → suspended fourths
    #   ARKHAM/LAIR → driving lead
    stage_to_mood = {
        0: "gotham", 1: "gotham", 2: "gotham",
        3: "ice",
        4: "gotham", 5: "lair", 6: "lair",
    }
    mood = stage_to_mood.get(stage_idx, "gotham")
    if mood == "gotham":
        lead = _render_track(GOTHAM_LEAD, _square)
        bass = _render_track(GOTHAM_BASS, _triangle)
    elif mood == "ice":
        lead = _render_track(ICE_LEAD, _square)
        bass = _render_track(ICE_BASS, _triangle)
    else:
        lead = _render_track(LAIR_LEAD, lambda f, n: _square(f, n, duty=0.25))
        bass = _render_track(LAIR_BASS, _triangle)
    # Pad to same length
    L = max(len(lead), len(bass))
    if len(lead) < L:
        lead = np.pad(lead, (0, L - len(lead)))
    if len(bass) < L:
        bass = np.pad(bass, (0, L - len(bass)))
    mix = lead * 0.6 + bass * 0.5
    mix = np.clip(mix, -1, 1)
    samples = (mix * 32767 * 0.5).astype(np.int16)
    stereo = np.column_stack((samples, samples))
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


_channel: pygame.mixer.Channel | None = None
_volume = 0.6


def play_stage(stage_idx: int) -> None:
    global _channel
    if not pygame.mixer.get_init():
        return
    if _channel is None:
        _channel = pygame.mixer.Channel(7)  # reserve a high-numbered channel
    _channel.stop()
    track = _track(stage_idx)
    track.set_volume(_volume)
    _channel.play(track, loops=-1)


def stop() -> None:
    if _channel is not None and pygame.mixer.get_init():
        _channel.stop()


def set_volume(v: float) -> None:
    global _volume
    _volume = max(0.0, min(1.0, v))
    # Push the new volume only to the actively-playing channel to avoid
    # synthesising tracks that haven't been requested yet.
    if _channel is not None and pygame.mixer.get_init():
        try:
            _channel.set_volume(_volume)
        except pygame.error:
            pass
