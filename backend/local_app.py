from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from .application.ui import CONTENT_BOTTOM, CONTENT_TOP, LocalUI, ScreenName, UIState
from .config import load_config
from .display.desktop_display import DesktopDisplay
from .display.interface import Display, DisplayConfig
from .display.st7796_display import ST7796Display
from .input.touch_interface import TouchEvent
from .input.ft6336_touch import FT6336Touch
from .ui_client import LocalAPIClient

IDLE_HOME_TIMEOUT_SECONDS = 20.0
SCROLL_REDRAW_DELTA_PIXELS = 2
CONTROL_SCROLL_HOLD_SECONDS = 0.3


@dataclass
class LocalUIRuntime:
    screen: ScreenName = "home"
    scroll_y: int = 0
    drag_last_y: int | None = None
    drag_moved: bool = False
    drag_pending_control: bool = False
    drag_pending_started_at: float = 0.0
    pending_control: str | None = None
    backend_state: UIState = field(default_factory=UIState)
    message: str | None = None


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
    runtime = LocalUIRuntime()
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
    last_backend_poll = 0.0
    try:
        async with LocalAPIClient() as api:
            await _draw_screen(display, ui, runtime)
            while True:
                now = asyncio.get_running_loop().time()
                if now - last_backend_poll >= 0.2:
                    backend = await api.state()
                    next_state = UIState.from_payload(backend.raw, online=backend.online)
                    if next_state != runtime.backend_state:
                        runtime.backend_state = next_state
                        await _draw_screen(display, ui, runtime)
                    last_backend_poll = now

                if touch is None:
                    await asyncio.sleep(0.1)
                    continue

                event = await touch.read_event()
                if event:
                    last_touch_at = now
                    if _apply_touch(ui, runtime, event, now=now):
                        await _draw_screen(display, ui, runtime)
                    if event.kind == "up" and runtime.pending_control:
                        command = runtime.pending_control
                        runtime.pending_control = None
                        path = {
                            "home": "/commands/home", "stop": "/commands/stop", "estop": "/commands/estop",
                            "scan": "/network/scan", "export-logs": "/logs/export",
                            "restart-services": "/system/restart", "reboot": "/system/reboot", "shutdown": "/system/shutdown",
                        }.get(command)
                        if path and runtime.backend_state.online:
                            result = await api.command(path)
                            runtime.message = result.get("message")
                            await _draw_screen(display, ui, runtime)
                elif _should_return_home(runtime.screen, last_touch_at, now):
                    runtime.screen = "home"
                    runtime.scroll_y = 0
                    await _draw_screen(display, ui, runtime)
    finally:
        if touch is not None:
            await touch.close()
    await display.close()


async def _draw_screen(display: Display, ui: LocalUI, runtime: LocalUIRuntime) -> None:
    await display.draw_rgb565(
        0,
        0,
        display.width,
        display.height,
        ui.render(runtime.screen, scroll_y=runtime.scroll_y, state=runtime.backend_state),
    )


def _screen_for_touch(ui: LocalUI, event: TouchEvent, current_screen: ScreenName) -> ScreenName:
    if event.kind != "down" or not event.points:
        return current_screen
    point = event.points[0]
    return ui.hit_nav(point.x, point.y) or current_screen


def _apply_touch(ui: LocalUI, runtime: LocalUIRuntime, event: TouchEvent, now: float = 0.0) -> bool:
    if event.kind == "up":
        runtime.drag_last_y = None
        runtime.drag_moved = False
        runtime.drag_pending_control = False
        runtime.drag_pending_started_at = 0.0
        return False
    if not event.points:
        return False

    point = event.points[0]
    if event.kind == "down":
        next_screen = ui.hit_nav(point.x, point.y)
        if next_screen is not None:
            changed = next_screen != runtime.screen or runtime.scroll_y != 0
            runtime.screen = next_screen
            runtime.scroll_y = 0
            runtime.drag_last_y = None
            runtime.drag_moved = False
            runtime.drag_pending_control = False
            runtime.drag_pending_started_at = 0.0
            return changed
        if ui.hit_content_control(runtime.screen, point.x, point.y, runtime.scroll_y):
            runtime.drag_last_y = point.y
            runtime.drag_moved = False
            runtime.drag_pending_control = True
            runtime.drag_pending_started_at = now
            runtime.pending_control = ui.hit_content_control(runtime.screen, point.x, point.y, runtime.scroll_y)
            return False
        if CONTENT_TOP <= point.y < CONTENT_BOTTOM:
            runtime.drag_last_y = point.y
            runtime.drag_moved = False
            runtime.drag_pending_control = False
            runtime.drag_pending_started_at = 0.0
        return False

    if event.kind != "move" or runtime.drag_last_y is None:
        return False

    if runtime.drag_pending_control:
        if now - runtime.drag_pending_started_at < CONTROL_SCROLL_HOLD_SECONDS:
            return False
        runtime.drag_pending_control = False
        runtime.pending_control = None

    delta_y = point.y - runtime.drag_last_y
    runtime.drag_last_y = point.y
    if abs(delta_y) < SCROLL_REDRAW_DELTA_PIXELS:
        return False

    next_scroll = ui.clamp_scroll(runtime.screen, runtime.scroll_y - delta_y)
    changed = next_scroll != runtime.scroll_y
    runtime.scroll_y = next_scroll
    runtime.drag_moved = runtime.drag_moved or changed
    return changed


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
