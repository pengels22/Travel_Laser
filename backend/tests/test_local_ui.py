from __future__ import annotations

from backend.application.ui import LocalUI
from backend.input.touch_interface import TouchEvent, TouchPoint
from backend.local_app import LocalUIRuntime, _apply_touch, _screen_for_touch, _should_return_home


def test_local_ui_renders_all_primary_screens() -> None:
    ui = LocalUI()

    for screen in ("home", "status", "net", "mode", "system"):
        frame = ui.render(screen)

        assert len(frame) == ui.width * ui.height * 2


def test_local_ui_nav_hit_testing() -> None:
    ui = LocalUI()

    assert ui.hit_nav(230, 288) == "net"
    assert ui.hit_nav(330, 288) == "mode"
    assert ui.hit_nav(20, 20) is None


def test_local_ui_clamps_scroll_to_screen_content() -> None:
    ui = LocalUI()

    assert ui.clamp_scroll("net", 999) == ui.max_scroll("net")
    assert ui.clamp_scroll("net", -20) == 0
    assert ui.max_scroll("home") == 0


def test_local_ui_detects_content_controls_with_scroll_offset() -> None:
    ui = LocalUI()

    assert ui.hit_content_control("home", 90, 140) == "home"
    assert ui.hit_content_control("net", 150, 249, scroll_y=46) == "connect"
    assert ui.hit_content_control("system", 50, 257, scroll_y=52) == "shutdown"


def test_touch_down_on_nav_changes_screen() -> None:
    ui = LocalUI()
    event = TouchEvent("down", (TouchPoint(0, 230, 288),))

    assert _screen_for_touch(ui, event, "home") == "net"


def test_touch_move_does_not_change_screen() -> None:
    ui = LocalUI()
    event = TouchEvent("move", (TouchPoint(0, 230, 288),))

    assert _screen_for_touch(ui, event, "home") == "home"


def test_touch_drag_scrolls_current_screen() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net")

    assert not _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 100, 180),)))
    assert _apply_touch(ui, runtime, TouchEvent("move", (TouchPoint(0, 100, 120),)))

    assert runtime.scroll_y > 0


def test_touch_down_on_content_button_delays_scroll_drag() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net", scroll_y=20)

    assert not _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 150, 249),)), now=10.0)
    assert runtime.drag_last_y == 249
    assert runtime.drag_pending_control
    assert not _apply_touch(ui, runtime, TouchEvent("move", (TouchPoint(0, 150, 220),)), now=10.2)
    assert runtime.scroll_y == 20


def test_held_content_button_can_start_scroll_drag() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net", scroll_y=20)

    _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 150, 249),)), now=10.0)
    assert _apply_touch(ui, runtime, TouchEvent("move", (TouchPoint(0, 150, 220),)), now=10.3)

    assert not runtime.drag_pending_control
    assert runtime.scroll_y > 20


def test_touch_drag_is_clamped_at_top() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net")

    _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 100, 120),)))
    assert not _apply_touch(ui, runtime, TouchEvent("move", (TouchPoint(0, 100, 180),)))

    assert runtime.scroll_y == 0


def test_nav_touch_resets_scroll_for_new_screen() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net", scroll_y=25)

    assert _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 330, 288),)))

    assert runtime.screen == "mode"
    assert runtime.scroll_y == 0


def test_idle_timeout_returns_non_home_screen_home() -> None:
    assert _should_return_home("net", last_touch_at=10.0, now=30.0)


def test_idle_timeout_keeps_home_screen_home() -> None:
    assert not _should_return_home("home", last_touch_at=10.0, now=60.0)


def test_idle_timeout_waits_for_full_twenty_seconds() -> None:
    assert not _should_return_home("system", last_touch_at=10.0, now=29.9)
