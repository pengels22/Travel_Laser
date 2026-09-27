from __future__ import annotations

from backend.application.dialogs import DialogKind, DialogState, TextEntryState
from backend.application.ui import LocalUI, UIState
from backend.application.ui import RGB565Frame, WHITE
from backend.input.touch_interface import TouchEvent, TouchPoint
from backend.local_app import (
    LocalUIRuntime,
    _apply_dialog_touch,
    _apply_touch,
    _open_connect_dialog,
    _screen_for_touch,
    _should_return_home,
)


def test_local_ui_renders_all_primary_screens() -> None:
    ui = LocalUI()

    for screen in ("home", "status", "net", "net_results", "mode", "system"):
        frame = ui.render(screen)

        assert len(frame) == ui.width * ui.height * 2


def test_text_renderer_uses_real_5x7_font() -> None:
    frame = RGB565Frame(8, 8)
    frame.text(0, 0, "A", WHITE)
    white = WHITE.to_bytes(2, "big")

    def lit(x: int, y: int) -> bool:
        start = (y * frame.width + x) * 2
        return frame.data[start:start + 2] == white

    assert lit(1, 0)
    assert lit(2, 0)
    assert lit(3, 0)
    assert lit(0, 3)
    assert lit(4, 3)
    assert not lit(0, 0)


def test_ui_state_comes_from_controller_payload_and_supports_offline() -> None:
    state = UIState.from_payload(
        {
            "machine": {"state": "idle", "connected_to_grbl": True},
            "physical": {"power_sense": True, "k1": True},
            "network": {"wifi_connected": True, "wifi_ip": "192.0.2.10"},
        }
    )
    assert state.online is True
    assert state.grbl_connected is True
    assert state.wifi_ip == "192.0.2.10"
    offline = UIState(online=False)
    assert len(LocalUI().render("home", state=offline)) == 480 * 320 * 2


def test_local_ui_nav_hit_testing() -> None:
    ui = LocalUI()

    assert ui.hit_nav(230, 288) == "net"
    assert ui.hit_nav(330, 288) == "mode"
    assert ui.hit_nav(20, 20) is None


def test_local_ui_clamps_scroll_to_screen_content() -> None:
    ui = LocalUI()

    assert ui.clamp_scroll("net", 999) == ui.max_scroll("net")
    assert ui.clamp_scroll("net_results", 999, _networks(10)) == ui.max_scroll("net_results", _networks(10))
    assert ui.clamp_scroll("net", -20) == 0
    assert ui.max_scroll("home") == 0


def test_local_ui_detects_content_controls_with_scroll_offset() -> None:
    ui = LocalUI()

    assert ui.hit_content_control("home", 90, 140) == "home"
    assert ui.hit_content_control("net", 150, 249, scroll_y=46) == "results"
    assert ui.hit_content_control("net_results", 200, 235, scroll_y=112, networks=_networks(10)) == "ssid:8"
    assert ui.hit_content_control("system", 50, 257, scroll_y=82) == "shutdown"


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
    runtime = LocalUIRuntime(screen="net_results", networks=_networks(10))

    assert not _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 460, 180),)))
    assert _apply_touch(ui, runtime, TouchEvent("move", (TouchPoint(0, 460, 120),)))

    assert runtime.scroll_y > 0


def test_touch_down_on_content_button_delays_scroll_drag() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net", scroll_y=20)

    assert not _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 150, 249),)), now=10.0)
    assert runtime.drag_last_y == 249
    assert runtime.drag_pending_control
    assert not _apply_touch(ui, runtime, TouchEvent("move", (TouchPoint(0, 150, 220),)), now=10.2)
    assert runtime.scroll_y == 20


def test_touch_up_after_content_button_tap_preserves_pending_command() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net")

    _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 45, 240),)), now=10.0)
    _apply_touch(ui, runtime, TouchEvent("up", (TouchPoint(0, 45, 240),)), now=10.1)

    assert runtime.pending_control == "scan"


def test_held_content_button_can_start_scroll_drag() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net", scroll_y=20)

    _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 150, 249),)), now=10.0)
    assert _apply_touch(ui, runtime, TouchEvent("move", (TouchPoint(0, 150, 220),)), now=10.3)

    assert not runtime.drag_pending_control
    assert runtime.scroll_y > 20
    _apply_touch(ui, runtime, TouchEvent("up", (TouchPoint(0, 150, 220),)), now=10.4)
    assert runtime.pending_control is None


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


def test_touch_up_after_scrolled_network_result_preserves_selected_row() -> None:
    ui = LocalUI()
    runtime = LocalUIRuntime(screen="net_results", scroll_y=112, networks=_networks(10))

    _apply_touch(ui, runtime, TouchEvent("down", (TouchPoint(0, 200, 235),)), now=10.0)
    _apply_touch(ui, runtime, TouchEvent("up", (TouchPoint(0, 200, 235),)), now=10.1)

    assert runtime.pending_control == "ssid:8"


def test_open_connect_dialog_uses_confirmation_for_open_network() -> None:
    runtime = LocalUIRuntime(selected_ssid="Guest")

    _open_connect_dialog(runtime, {"ssid": "Guest", "security": "open"})

    assert runtime.dialog
    assert runtime.dialog.kind == DialogKind.CONFIRMATION
    assert runtime.dialog.payload == {"ssid": "Guest", "password": ""}


def test_open_connect_dialog_uses_keyboard_for_secured_network() -> None:
    runtime = LocalUIRuntime(selected_ssid="Lab 42")

    _open_connect_dialog(runtime, {"ssid": "Lab 42", "security": "WPA/WPA2"})

    assert runtime.dialog
    assert runtime.dialog.kind == DialogKind.KEYBOARD
    assert runtime.dialog.payload == {"ssid": "Lab 42"}
    assert runtime.entry


def test_success_dialog_dismisses_from_visible_button_press() -> None:
    runtime = LocalUIRuntime(dialog=DialogState(DialogKind.SUCCESS, "Complete", "Wi-Fi scan complete"))

    action = _apply_dialog_touch(runtime, TouchEvent("down", (TouchPoint(0, 300, 205),)))

    assert action == "dismiss"


def test_dialog_release_without_coordinates_is_ignored() -> None:
    runtime = LocalUIRuntime(dialog=DialogState(DialogKind.SUCCESS, "Complete", "Wi-Fi scan complete"))

    action = _apply_dialog_touch(runtime, TouchEvent("up", ()))

    assert action is None


def test_confirmation_dialog_buttons_use_press_coordinates() -> None:
    runtime = LocalUIRuntime(dialog=DialogState(DialogKind.CONFIRMATION, "Connect", "Connect?"))

    assert _apply_dialog_touch(runtime, TouchEvent("down", (TouchPoint(0, 80, 205),))) == "cancel"
    assert _apply_dialog_touch(runtime, TouchEvent("down", (TouchPoint(0, 300, 205),))) == "confirm"


def test_keyboard_dialog_buttons_use_press_coordinates() -> None:
    runtime = LocalUIRuntime(
        dialog=DialogState(DialogKind.KEYBOARD, "Wi-Fi password", "Password"),
        entry=TextEntryState(),
    )

    assert _apply_dialog_touch(runtime, TouchEvent("down", (TouchPoint(0, 52, 160),))) == "key:1"
    assert _apply_dialog_touch(runtime, TouchEvent("down", (TouchPoint(0, 400, 248),))) == "confirm"


def test_idle_timeout_returns_non_home_screen_home() -> None:
    assert _should_return_home("net", last_touch_at=10.0, now=30.0)


def test_idle_timeout_keeps_home_screen_home() -> None:
    assert not _should_return_home("home", last_touch_at=10.0, now=60.0)


def test_idle_timeout_waits_for_full_twenty_seconds() -> None:
    assert not _should_return_home("system", last_touch_at=10.0, now=29.9)


def _networks(count: int) -> list[dict]:
    return [{"ssid": f"Network {index}", "signal": 90 - index, "security": "WPA/WPA2"} for index in range(count)]
