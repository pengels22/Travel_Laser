#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from backend.config import load_config
from backend.display.desktop_display import DesktopDisplay
from backend.display.interface import DisplayConfig
from backend.display.st7796_display import ST7796Display


async def main() -> None:
    parser = argparse.ArgumentParser(description="Travel Laser display diagnostic")
    parser.add_argument("--config", type=Path, default=Path("config/controller.example.yaml"))
    parser.add_argument("--display", choices=["desktop", "st7796"], default="desktop")
    args = parser.parse_args()
    config = load_config(args.config)
    display_config = DisplayConfig(
        width=config.display.width,
        height=config.display.height,
        rotation=config.display.rotation,
        spi_device=config.display.spi_device,
        spi_speed_hz=config.display.spi_speed_hz,
        dc_gpio_chip=config.display.dc_gpio_chip,
        dc_gpio_line=config.display.dc_gpio_line,
        reset_gpio_chip=config.display.reset_gpio_chip,
        reset_gpio_line=config.display.reset_gpio_line,
        backlight_gpio_chip=config.display.backlight_gpio_chip,
        backlight_gpio_line=config.display.backlight_gpio_line,
    )
    display = DesktopDisplay(display_config) if args.display == "desktop" else ST7796Display(display_config)
    await display.initialize()
    try:
        for color in (0xF800, 0x07E0, 0x001F, 0xFFFF, 0x0000):
            await display.clear(color)
            await asyncio.sleep(0.5)
        await draw_grid(display)
    finally:
        await display.close()


async def draw_grid(display) -> None:
    data = bytearray(display.width * display.height * 2)
    for y in range(display.height):
        for x in range(display.width):
            color = 0xFFFF if x % 40 == 0 or y % 40 == 0 else 0x0000
            if x < 20 or y < 20:
                color = 0xF800
            start = (y * display.width + x) * 2
            data[start : start + 2] = color.to_bytes(2, "big")
    await display.draw_rgb565(0, 0, display.width, display.height, bytes(data))


if __name__ == "__main__":
    asyncio.run(main())

