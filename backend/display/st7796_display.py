from __future__ import annotations

import asyncio
import time

from .desktop_display import _check_bounds
from .interface import DisplayConfig


class ST7796Display:
    """Userspace SPI ST7796U display backend for the validated Orange Pi Zero 3 wiring."""

    def __init__(self, config: DisplayConfig) -> None:
        if not config.spi_device:
            raise ValueError("display.spi_device is required for ST7796 display mode")
        if config.dc_gpio_line is None:
            raise ValueError("display.dc_gpio_line is required for ST7796 display mode")

        self.config = config
        self.width = config.width
        self.height = config.height
        self._spi = None
        self._dc_request = None
        self._reset_request = None
        self._backlight_request = None

    async def initialize(self) -> None:
        import spidev

        bus, device = _parse_spidev(self.config.spi_device)
        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = self.config.spi_speed_hz
        self._spi.mode = 0
        self._spi.no_cs = False

        self._dc_request = _request_output(
            self.config.dc_gpio_chip or "/dev/gpiochip1",
            self.config.dc_gpio_line,
            False,
            "travel-laser-display-dc",
        )

        if self.config.reset_gpio_line is not None:
            self._reset_request = _request_output(
                self.config.reset_gpio_chip or "/dev/gpiochip1",
                self.config.reset_gpio_line,
                True,
                "travel-laser-display-reset",
            )

        if self.config.backlight_gpio_line is not None:
            self._backlight_request = _request_output(
                self.config.backlight_gpio_chip or "/dev/gpiochip1",
                self.config.backlight_gpio_line,
                False,
                "travel-laser-display-backlight",
            )

        await self._hardware_reset()
        self._init_sequence()
        self._set_rotation(self.config.rotation)

        if self._backlight_request is not None:
            _set_request_value(self._backlight_request, self.config.backlight_gpio_line, True)

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
        if self._backlight_request is not None and self.config.backlight_gpio_line is not None:
            _set_request_value(self._backlight_request, self.config.backlight_gpio_line, False)

        if self._spi is not None:
            self._spi.close()

        for request in (self._dc_request, self._reset_request, self._backlight_request):
            if request is not None:
                request.release()

    async def _hardware_reset(self) -> None:
        if self._reset_request is None or self.config.reset_gpio_line is None:
            # Validated production wiring leaves LCD_RST software-unmanaged because
            # PC9/GPIO73 is reserved by the Orange Pi Zero 3 PMIC interrupt.
            await asyncio.sleep(0.25)
            return

        _set_request_value(self._reset_request, self.config.reset_gpio_line, True)
        await asyncio.sleep(0.05)
        _set_request_value(self._reset_request, self.config.reset_gpio_line, False)
        await asyncio.sleep(0.10)
        _set_request_value(self._reset_request, self.config.reset_gpio_line, True)
        await asyncio.sleep(0.15)

    def _init_sequence(self) -> None:
        # Sequence physically validated on the Hosyond ST7796U panel.
        self._cmd(0x01)  # software reset
        time.sleep(0.15)

        self._cmd(0xF0, bytes([0xC3]))
        self._cmd(0xF0, bytes([0x96]))

        self._cmd(0x36, bytes([0x28]))  # landscape + BGR
        self._cmd(0x3A, bytes([0x55]))  # RGB565 / 16-bit

        self._cmd(0xB4, bytes([0x01]))
        self._cmd(0xB7, bytes([0xC6]))
        self._cmd(0xE8, bytes([0x40, 0x8A, 0x00, 0x00, 0x29, 0x19, 0xA5, 0x33]))
        self._cmd(0xC1, bytes([0x06]))
        self._cmd(0xC2, bytes([0xA7]))
        self._cmd(0xC5, bytes([0x18]))

        self._cmd(0xE0, bytes([
            0xF0, 0x09, 0x0B, 0x06, 0x04, 0x15, 0x2F,
            0x54, 0x42, 0x3C, 0x17, 0x14, 0x18, 0x1B,
        ]))
        self._cmd(0xE1, bytes([
            0xE0, 0x09, 0x0B, 0x06, 0x04, 0x03, 0x2B,
            0x43, 0x42, 0x3B, 0x16, 0x14, 0x17, 0x1B,
        ]))

        self._cmd(0xF0, bytes([0x3C]))
        self._cmd(0xF0, bytes([0x69]))

        self._cmd(0x11)  # sleep out
        time.sleep(0.15)

        self._cmd(0x21)  # inversion ON; required for correct colors on this panel
        time.sleep(0.05)

        self._cmd(0x29)  # display on
        time.sleep(0.10)

    def _set_rotation(self, rotation: int) -> None:
        madctl = {
            0: 0x48,
            90: 0x28,
            180: 0x88,
            270: 0xE8,
        }.get(rotation)
        if madctl is None:
            raise ValueError("display rotation must be one of 0, 90, 180, 270")
        self._cmd(0x36, bytes([madctl]))

    def _set_window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self._cmd(0x2A, x0.to_bytes(2, "big") + x1.to_bytes(2, "big"))
        self._cmd(0x2B, y0.to_bytes(2, "big") + y1.to_bytes(2, "big"))
        self._cmd(0x2C)

    def _cmd(self, command: int, payload: bytes | None = None) -> None:
        if self._spi is None or self._dc_request is None:
            raise RuntimeError("ST7796 display is not initialized")

        _set_request_value(self._dc_request, self.config.dc_gpio_line, False)
        self._spi.writebytes([command])

        if payload is not None:
            self._data(payload)

    def _data(self, payload: bytes) -> None:
        if self._spi is None or self._dc_request is None:
            raise RuntimeError("ST7796 display is not initialized")

        _set_request_value(self._dc_request, self.config.dc_gpio_line, True)
        self._spi.writebytes2(payload)


def _request_output(chip: str, line: int, initial_high: bool, consumer: str):
    import gpiod
    from gpiod.line import Direction, Value

    chip_path = _chip_path(chip)
    return gpiod.request_lines(
        chip_path,
        consumer=consumer,
        config={
            line: gpiod.LineSettings(
                direction=Direction.OUTPUT,
                output_value=Value.ACTIVE if initial_high else Value.INACTIVE,
            )
        },
    )


def _set_request_value(request, line: int | None, high: bool) -> None:
    if line is None:
        return

    from gpiod.line import Value

    request.set_value(line, Value.ACTIVE if high else Value.INACTIVE)


def _chip_path(chip: str) -> str:
    return chip if chip.startswith("/") else f"/dev/{chip}"


def _parse_spidev(path: str) -> tuple[int, int]:
    name = path.rsplit("/", 1)[-1]
    if not name.startswith("spidev") or "." not in name:
        raise ValueError(f"invalid spidev path: {path}")
    bus_text, device_text = name.removeprefix("spidev").split(".", 1)
    return int(bus_text), int(device_text)
