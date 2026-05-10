"""Unified input layer (keyboard + gamepad).

Every per-frame query goes through ``InputState`` so the rest of the game
doesn't care whether the input came from a key or a stick. Edge events
(``pressed.x``) are filled by ``feed_event``; analog hold state
(``held.left``) is read each frame from the keyboard + connected joysticks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame


@dataclass(slots=True)
class HeldState:
    left: bool = False
    right: bool = False
    up: bool = False
    down: bool = False
    run: bool = False


@dataclass(slots=True)
class PressedState:
    """One-shot press flags. Cleared by InputState.end_frame()."""
    jump: bool = False
    punch: bool = False
    kick: bool = False
    throw: bool = False
    slide: bool = False
    pause: bool = False
    confirm: bool = False
    cancel: bool = False
    up: bool = False
    down: bool = False


KEY_MAP = {
    "jump":    {pygame.K_SPACE, pygame.K_UP, pygame.K_w},
    "punch":   {pygame.K_z, pygame.K_j},
    "kick":    {pygame.K_x, pygame.K_k},
    "throw":   {pygame.K_c, pygame.K_l},
    "slide":   {pygame.K_DOWN, pygame.K_s},
    "pause":   {pygame.K_p},
    "confirm": {pygame.K_RETURN, pygame.K_KP_ENTER},
    "cancel":  {pygame.K_ESCAPE},
    "up":      {pygame.K_UP, pygame.K_w},
    "down":    {pygame.K_DOWN, pygame.K_s},
}

# Standard SDL/pygame controller button mapping (Xbox-like)
PAD_MAP = {
    "jump":    {0},        # A / Cross
    "punch":   {2},        # X / Square
    "kick":    {3},        # Y / Triangle
    "throw":   {1},        # B / Circle
    "slide":   {4, 5},     # shoulder buttons
    "pause":   {7, 9},     # Start / Options
    "confirm": {0, 7},
    "cancel":  {1, 6},
}


@dataclass(slots=True)
class InputState:
    held: HeldState = field(default_factory=HeldState)
    pressed: PressedState = field(default_factory=PressedState)
    joysticks: list[pygame.joystick.JoystickType] = field(default_factory=list)

    def init_joysticks(self) -> None:
        pygame.joystick.init()
        self.joysticks = []
        for i in range(pygame.joystick.get_count()):
            try:
                j = pygame.joystick.Joystick(i)
                j.init()
                self.joysticks.append(j)
            except pygame.error:
                pass

    # ------------------------------------------------------------------
    def feed_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            self._set_pressed_from(KEY_MAP, event.key)
        elif event.type == pygame.JOYBUTTONDOWN:
            self._set_pressed_from(PAD_MAP, event.button)
        elif event.type == pygame.JOYHATMOTION:
            x, y = event.value
            if x < 0:
                self.held.left = True
            if x > 0:
                self.held.right = True
            if y > 0:
                self.pressed.up = True
            if y < 0:
                self.pressed.down = True
                self.pressed.slide = True
        elif event.type == pygame.JOYDEVICEADDED:
            self.init_joysticks()

    def _set_pressed_from(self, table: dict[str, set[int]], code: int) -> None:
        for action, codes in table.items():
            if code in codes:
                setattr(self.pressed, action, True)

    # ------------------------------------------------------------------
    def sample(self, keys: pygame.key.ScancodeWrapper) -> None:
        self.held.left = bool(keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.held.right = bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])
        self.held.up = bool(keys[pygame.K_UP] or keys[pygame.K_w])
        self.held.down = bool(keys[pygame.K_DOWN] or keys[pygame.K_s])
        self.held.run = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])

        # Analog stick / dpad fallback
        for j in self.joysticks:
            try:
                if j.get_numaxes() >= 2:
                    ax = j.get_axis(0)
                    ay = j.get_axis(1)
                    if ax < -0.4:
                        self.held.left = True
                    if ax > 0.4:
                        self.held.right = True
                    if ay < -0.4:
                        self.held.up = True
                    if ay > 0.4:
                        self.held.down = True
                if j.get_numhats() >= 1:
                    hx, hy = j.get_hat(0)
                    if hx < 0:
                        self.held.left = True
                    if hx > 0:
                        self.held.right = True
                    if hy > 0:
                        self.held.up = True
                    if hy < 0:
                        self.held.down = True
            except pygame.error:
                pass

    def end_frame(self) -> None:
        self.pressed = PressedState()
