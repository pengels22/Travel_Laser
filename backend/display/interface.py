from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DisplayConfig:
    width: int = 480
    height: int = 320
    rotation: int = 90
    spi_device: str | None = None
    spi_speed_hz: int = 24_000_000
    dc_gpio_chip: str | None = None
    dc_gpio_line: int | None = None
    reset_gpio_chip: str | None = None
    reset_gpio_line: int | None = None
    backlight_gpio_chip: str | None = None
    backlight_gpio_line: int | None = None


class Display(Protocol):
    width: int
    height: int

    async def initialize(self) -> None: ...
    async def clear(self, color: int = 0x0000) -> None: ...
    async def draw_rgb565(self, x: int, y: int, width: int, height: int, data: bytes) -> None: ...
    async def close(self) -> None: ...

