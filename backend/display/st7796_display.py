from __future__ import annotations

import asyncio
import time

from .desktop_display import _check_bounds
from .interface import DisplayConfig


class ST7796Display:
    """Userspace SPI ST7796U display backend for Orange Pi/Linux."""

    def __init__(self, config: DisplayConfig) -> None:
        if not config.spi_device:
            raise ValueError("display.spi_device is required for ST7796 display mode")
        if config.dc_gpio_line is None:
            raise ValueError("display.dc_gpio_line is required for ST7796 display mode")
        self.config = config
        self.width = config.width
        self.height = config.height
        self._spi = None
        self._chip = None
        self._dc = None
        self._reset = None
        self._backlight = None

    async def initialize(self) -> None:
        import gpiod
        import spidev

        bus, device = _parse_spidev(self.config.spi_device)
        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = self.config.spi_speed_hz
        self._spi.mode = 0

        chip_name = self.config.dc_gpio_chip or "gpiochip0"
        self._chip = gpiod.Chip(chip_name)
        self._dc = self._request_output(self.config.dc_gpio_line, 0)
        if self.config.reset_gpio_line is not None:
            self._reset = self._request_output(self.config.reset_gpio_line, 1)
        if self.config.backlight_gpio_line is not None:
            self._backlight = self._request_output(self.config.backlight_gpio_line, 0)

        await self._hardware_reset()
        self._init_sequence()
        self._set_rotation(self.config.rotation)
        if self._backlight is not None:
            self._backlight.set_value(1)
        await self.clear()

    async def clear(self, color: int = 0x0000) -> None:
        pixel = color.to_bytes(2, "big")
        row = pixel * self.width
        await self.draw_rgb565(0, 0, self.width, self.height, row * self.height)

    async def draw_rgb565(self, x: int, y: int, width: int, height: int, data: bytes) -> None:
        _check_bounds(self.width, self.height, x, y, width, height, data)
        self._set_window(x, y, x + width - 1, y + height - 1)
        self._data(data)
        await asyncio.sleep(0)

    async def close(self) -> None:
        if self._backlight is not None:
            self._backlight.set_value(0)
        if self._spi is not None:
            self._spi.close()

    def _request_output(self, line_number: int, default: int):
        line = self._chip.get_line(line_number)
        import gpiod

        line.request(consumer="travel-laser-display", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[default])
        return line

    async def _hardware_reset(self) -> None:
        if self._reset is None:
            return
        self._reset.set_value(0)
        await asyncio.sleep(0.05)
        self._reset.set_value(1)
        await asyncio.sleep(0.12)

    def _init_sequence(self) -> None:
        self._cmd(0x01)
        time.sleep(0.12)
        self._cmd(0x11)
        time.sleep(0.12)
        self._cmd(0x3A, bytes([0x55]))
        self._cmd(0x36, bytes([0x28]))
        self._cmd(0xB6, bytes([0x00, 0x22, 0x3B]))
        self._cmd(0xF0, bytes([0xC3]))
        self._cmd(0xF0, bytes([0x96]))
        self._cmd(0x29)
        time.sleep(0.02)

    def _set_rotation(self, rotation: int) -> None:
        madctl = {0: 0x48, 90: 0x28, 180: 0x88, 270: 0xE8}.get(rotation)
        if madctl is None:
            raise ValueError("display rotation must be one of 0, 90, 180, 270")
        self._cmd(0x36, bytes([madctl]))

    def _set_window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self._cmd(0x2A, x0.to_bytes(2, "big") + x1.to_bytes(2, "big"))
        self._cmd(0x2B, y0.to_bytes(2, "big") + y1.to_bytes(2, "big"))
        self._cmd(0x2C)

    def _cmd(self, command: int, payload: bytes | None = None) -> None:
        self._dc.set_value(0)
        self._spi.writebytes([command])
        if payload:
            self._data(payload)

    def _data(self, payload: bytes) -> None:
        self._dc.set_value(1)
        self._spi.writebytes2(payload)


def _parse_spidev(path: str) -> tuple[int, int]:
    name = path.rsplit("/", 1)[-1]
    if not name.startswith("spidev") or "." not in name:
        raise ValueError(f"invalid spidev path: {path}")
    bus_text, device_text = name.removeprefix("spidev").split(".", 1)
    return int(bus_text), int(device_text)
