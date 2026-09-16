from __future__ import annotations

from backend.application.ui import LocalUI
from backend.input.touch_interface import TouchEvent, TouchPoint
from backend.local_app import _screen_for_touch, _should_return_home


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


def test_touch_down_on_nav_changes_screen() -> None:
    ui = LocalUI()
    event = TouchEvent("down", (TouchPoint(0, 230, 288),))

    assert _screen_for_touch(ui, event, "home") == "net"


def test_touch_move_does_not_change_screen() -> None:
    ui = LocalUI()
    event = TouchEvent("move", (TouchPoint(0, 230, 288),))

    assert _screen_for_touch(ui, event, "home") == "home"


def test_idle_timeout_returns_non_home_screen_home() -> None:
    assert _should_return_home("net", last_touch_at=10.0, now=30.0)


def test_idle_timeout_keeps_home_screen_home() -> None:
    assert not _should_return_home("home", last_touch_at=10.0, now=60.0)


def test_idle_timeout_waits_for_full_twenty_seconds() -> None:
    assert not _should_return_home("system", last_touch_at=10.0, now=29.9)
