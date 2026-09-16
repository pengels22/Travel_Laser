from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .application.ui import LocalUI, ScreenName
from .config import load_config
from .display.desktop_display import DesktopDisplay
from .display.interface import Display, DisplayConfig
from .display.st7796_display import ST7796Display
from .input.touch_interface import TouchEvent
from .input.ft6336_touch import FT6336Touch

IDLE_HOME_TIMEOUT_SECONDS = 20.0


async def run(config_path: Path | None, display_mode: str, touch_mode: str) -> None:
    config = load_config(config_path)
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
    display = DesktopDisplay(display_config) if display_mode == "desktop" else ST7796Display(display_config)
    await display.initialize()
    ui = LocalUI(display.width, display.height)
    current_screen: ScreenName = "home"
    await _draw_screen(display, ui, current_screen)

    touch = None
    if touch_mode == "ft6336":
        if config.touch.i2c_bus is None:
            raise ValueError("touch.i2c_bus is required for FT6336U touch mode")
        touch = FT6336Touch(
            i2c_bus=config.touch.i2c_bus,
            address=config.touch.i2c_address,
            width=display.width,
            height=display.height,
            rotation=config.touch.rotation,
            reset_gpio_chip=config.touch.reset_gpio_chip,
            reset_gpio_line=config.touch.reset_gpio_line,
        )
        await touch.initialize()

    last_touch_at = asyncio.get_running_loop().time()
    try:
        while True:
            if touch is None:
                await asyncio.sleep(1)
            else:
                event = await touch.read_event()
                if event:
                    last_touch_at = asyncio.get_running_loop().time()
                    next_screen = _screen_for_touch(ui, event, current_screen)
                    if next_screen != current_screen:
                        current_screen = next_screen
                        await _draw_screen(display, ui, current_screen)
                elif _should_return_home(
                    current_screen=current_screen,
                    last_touch_at=last_touch_at,
                    now=asyncio.get_running_loop().time(),
                    timeout_seconds=IDLE_HOME_TIMEOUT_SECONDS,
                ):
                    current_screen = "home"
                    await _draw_screen(display, ui, current_screen)
    finally:
        if touch is not None:
            await touch.close()
        await display.close()


async def _draw_screen(display: Display, ui: LocalUI, screen: ScreenName) -> None:
    await display.draw_rgb565(0, 0, display.width, display.height, ui.render(screen))


def _screen_for_touch(ui: LocalUI, event: TouchEvent, current_screen: ScreenName) -> ScreenName:
    if event.kind != "down" or not event.points:
        return current_screen
    point = event.points[0]
    return ui.hit_nav(point.x, point.y) or current_screen


def _should_return_home(
    current_screen: ScreenName,
    last_touch_at: float,
    now: float,
    timeout_seconds: float = IDLE_HOME_TIMEOUT_SECONDS,
) -> bool:
    return current_screen != "home" and now - last_touch_at >= timeout_seconds


def main() -> None:
    parser = argparse.ArgumentParser(description="Travel Laser local touchscreen application")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--display", choices=["desktop", "st7796"], default="desktop")
    parser.add_argument("--touch", choices=["none", "ft6336"], default="none")
    args = parser.parse_args()
    asyncio.run(run(args.config, args.display, args.touch))


if __name__ == "__main__":
    main()
