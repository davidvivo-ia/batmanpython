"""Pytest setup: force pygame to use dummy SDL drivers so tests run headless."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest


@pytest.fixture(scope="session", autouse=True)
def _pygame_init():
    import pygame

    from batman_returns import audio

    audio.init()
    pygame.init()
    pygame.display.set_mode((100, 100))
    yield
    pygame.quit()
