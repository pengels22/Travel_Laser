from __future__ import annotations

from dataclasses import dataclass


BLACK = 0x0000
WHITE = 0xFFFF
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
YELLOW = 0xFFE0
DARK = 0x2104


@dataclass(frozen=True)
class Button:
    label: str
    x: int
    y: int
    width: int
    height: int


class LocalUI:
    def __init__(self, width: int = 480, height: int = 320) -> None:
        self.width = width
        self.height = height
        self.nav_buttons = (
            Button("HOME", 8, 264, 88, 48),
            Button("STATUS", 104, 264, 88, 48),
            Button("NET", 200, 264, 88, 48),
            Button("MODE", 296, 264, 80, 48),
            Button("SYSTEM", 384, 264, 88, 48),
        )
        self.home_actions = (
            Button("HOME", 28, 82, 196, 142),
            Button("STOP", 256, 82, 196, 142),
        )

    def render_home(self, machine_state: str = "offline") -> bytes:
        frame = RGB565Frame(self.width, self.height, BLACK)
        frame.fill_rect(0, 0, self.width, 44, DARK)
        frame.text(12, 14, "Travel-Laser", WHITE)
        frame.text(340, 14, machine_state.upper(), GREEN if machine_state == "idle" else YELLOW)

        for button in self.home_actions:
            color = RED if button.label == "STOP" else GREEN
            frame.fill_rect(button.x, button.y, button.width, button.height, color)
            frame.rect(button.x, button.y, button.width, button.height, WHITE)
            frame.text(button.x + 74, button.y + 48, button.label, WHITE)
            frame.text(button.x + 38, button.y + 84, "GRBL" if button.label == "HOME" else "HOLD", WHITE)

        for button in self.nav_buttons:
            color = BLUE if button.label == "HOME" else DARK
            frame.fill_rect(button.x, button.y, button.width, button.height, color)
            frame.rect(button.x, button.y, button.width, button.height, WHITE)
            frame.text(button.x + 10, button.y + 18, button.label, WHITE)
        return bytes(frame.data)


class RGB565Frame:
    def __init__(self, width: int, height: int, color: int = BLACK) -> None:
        self.width = width
        self.height = height
        self.data = bytearray(width * height * 2)
        self.fill(color)

    def fill(self, color: int) -> None:
        self.data[:] = color.to_bytes(2, "big") * (self.width * self.height)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        pixel = color.to_bytes(2, "big")
        for row in range(max(0, y), min(self.height, y + height)):
            start = (row * self.width + max(0, x)) * 2
            end = (row * self.width + min(self.width, x + width)) * 2
            self.data[start:end] = pixel * ((end - start) // 2)

    def rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        self.fill_rect(x, y, width, 1, color)
        self.fill_rect(x, y + height - 1, width, 1, color)
        self.fill_rect(x, y, 1, height, color)
        self.fill_rect(x + width - 1, y, 1, height, color)

    def text(self, x: int, y: int, text: str, color: int) -> None:
        cursor = x
        for char in text[:32]:
            self._glyph(cursor, y, char, color)
            cursor += 8

    def _glyph(self, x: int, y: int, char: str, color: int) -> None:
        code = ord(char)
        for row in range(7):
            bits = ((code << row) ^ (code >> (row % 3))) & 0x1F
            for col in range(5):
                if bits & (1 << col):
                    self.fill_rect(x + col, y + row, 1, 1, color)
