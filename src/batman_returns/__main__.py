"""Entry point: ``python -m batman_returns`` or ``batman-returns`` script."""

from __future__ import annotations

import sys

import pygame


def main() -> int:
    from .game import create_game

    game = create_game()
    try:
        game.run()
    finally:
        pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main())
