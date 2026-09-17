from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal


BLACK = 0x0000
WHITE = 0xFFFF
RED = 0xF800
GREEN = 0x07E0
BLUE = 0x001F
YELLOW = 0xFFE0
DARK = 0x2104
PANEL = 0x18E4
PANEL_ALT = 0x2946
GRAY = 0x632C
MUTED = 0xBDF7

ScreenName = Literal["home", "status", "net", "mode", "system"]
CONTENT_TOP = 44
CONTENT_BOTTOM = 264
CONTENT_HEIGHT = CONTENT_BOTTOM - CONTENT_TOP


@dataclass(frozen=True)
class Button:
    label: str
    x: int
    y: int
    width: int
    height: int


@dataclass
class UIState:
    online: bool = False
    machine_state: str = "offline"
    homed: bool = False
    power_present: bool = False
    estop_active: bool = False
    k1_energized: bool = False
    laser_usb_connected: bool = False
    grbl_connected: bool = False
    lightburn_connected: bool = False
    lightburn_stream_active: bool = False
    tailscale_connected: bool = False
    tailscale_ip: str | None = None
    ethernet_connected: bool = False
    ethernet_ip: str | None = None
    wifi_connected: bool = False
    wifi_ssid: str | None = None
    wifi_ip: str | None = None
    current_mode: str = "network"
    camera_connected: bool = False
    faults: tuple[str, ...] = ()

    @classmethod
    def from_payload(cls, payload: dict[str, Any], online: bool = True) -> "UIState":
        machine = payload.get("machine", {})
        physical = payload.get("physical", {})
        lightburn = payload.get("lightburn", {})
        network = payload.get("network", {})
        mode = payload.get("mode", {})
        camera = payload.get("camera", {})
        safety = payload.get("safety", {})
        faults = []
        if machine.get("error"):
            faults.append(str(machine["error"]))
        if safety.get("software_estop"):
            faults.append("Software E-stop active")
        return cls(
            online=online,
            machine_state=str(machine.get("state", "offline")),
            homed=bool(machine.get("homed", False)),
            power_present=bool(physical.get("power_sense", False)),
            estop_active=bool(physical.get("estop_sense", False)),
            k1_energized=bool(physical.get("k1", False)),
            laser_usb_connected=bool(machine.get("laser_usb_connected", False)),
            grbl_connected=bool(machine.get("connected_to_grbl", False)),
            lightburn_connected=bool(lightburn.get("connected", False)),
            lightburn_stream_active=bool(lightburn.get("stream_active", False)),
            tailscale_connected=bool(network.get("tailscale_connected", False)),
            tailscale_ip=network.get("tailscale_ip"),
            ethernet_connected=bool(network.get("ethernet_connected", False)),
            ethernet_ip=network.get("ethernet_ip") or network.get("ip_address"),
            wifi_connected=bool(network.get("wifi_connected", False)),
            wifi_ssid=network.get("wifi_ssid"),
            wifi_ip=network.get("wifi_ip"),
            current_mode=str(mode.get("laser_mode", "network")),
            camera_connected=bool(camera.get("connected", False)),
            faults=tuple(faults),
        )


class LocalUI:
    def __init__(self, width: int = 480, height: int = 320) -> None:
        self.width = width
        self.height = height
        self.nav_buttons = (
            Button("Home", 8, 264, 88, 48),
            Button("Status", 104, 264, 88, 48),
            Button("Net", 200, 264, 88, 48),
            Button("Mode", 296, 264, 80, 48),
            Button("System", 384, 264, 88, 48),
        )
        self.home_actions = (
            Button("HOME", 28, 82, 196, 142),
            Button("STOP", 256, 82, 196, 142),
        )

    def render(self, screen: ScreenName = "home", machine_state: str = "idle", scroll_y: int = 0, state: UIState | None = None) -> bytes:
        state = state or UIState(online=True, machine_state=machine_state)
        frame = RGB565Frame(self.width, self.height, BLACK)
        if screen == "home":
            self._draw_home(frame, state)
        elif screen == "status":
            self._draw_status(frame, scroll_y, state)
        elif screen == "net":
            self._draw_network(frame, scroll_y, state)
        elif screen == "mode":
            self._draw_mode(frame, scroll_y, state)
        elif screen == "system":
            self._draw_system(frame, scroll_y)
        self._draw_shell(frame, screen, state)
        return bytes(frame.data)

    def render_home(self, machine_state: str = "idle") -> bytes:
        return self.render("home", machine_state)

    def hit_nav(self, x: int, y: int) -> ScreenName | None:
        screen_names: tuple[ScreenName, ...] = ("home", "status", "net", "mode", "system")
        for screen_name, button in zip(screen_names, self.nav_buttons, strict=True):
            if button.x <= x < button.x + button.width and button.y <= y < button.y + button.height:
                return screen_name
        return None

    def max_scroll(self, screen: ScreenName) -> int:
        content_heights: dict[ScreenName, int] = {
            "home": CONTENT_HEIGHT,
            "status": 252,
            "net": 258,
            "mode": CONTENT_HEIGHT,
            "system": 252,
        }
        return max(0, content_heights[screen] - CONTENT_HEIGHT)

    def clamp_scroll(self, screen: ScreenName, scroll_y: int) -> int:
        return max(0, min(self.max_scroll(screen), scroll_y))

    def hit_content_control(self, screen: ScreenName, x: int, y: int, scroll_y: int = 0) -> str | None:
        content_y = y + scroll_y
        if screen == "home":
            for button in self.home_actions:
                if _contains(button, x, y):
                    return button.label.lower()
            return None
        if screen == "net":
            for button in (
                Button("scan", 18, 260, 100, 36),
                Button("connect", 130, 260, 110, 36),
                Button("forget", 252, 260, 100, 36),
                Button("refresh", 364, 260, 98, 36),
            ):
                if _contains(button, x, content_y):
                    return button.label
        if screen == "mode":
            for button in (
                Button("network", 24, 66, 432, 72),
                Button("virtualhere", 24, 150, 432, 72),
            ):
                if _contains(button, x, content_y):
                    return button.label
        if screen == "system":
            row_y = 70
            for label in (
                "gpio",
                "usb",
                "spi-i2c",
                "logs",
                "export-logs",
                "restart-services",
                "reboot",
                "shutdown",
            ):
                if 24 <= x < 456 and row_y <= content_y < row_y + 30:
                    return label
                row_y += 30
        return None

    def _draw_shell(self, frame: "RGB565Frame", active_screen: ScreenName, state: UIState) -> None:
        frame.fill_rect(0, 0, self.width, 44, DARK)
        frame.text(12, 14, "Travel-Laser", WHITE, scale=2)
        if not state.online:
            frame.fill_circle(272, 21, 6, RED)
            frame.text(286, 14, "Offline", WHITE)
        else:
            frame.fill_circle(272, 21, 6, GREEN if state.machine_state == "idle" else YELLOW)
            frame.text(286, 14, state.machine_state.title(), WHITE)

        for button, screen_name in zip(
            self.nav_buttons,
            ("home", "status", "net", "mode", "system"),
            strict=True,
        ):
            color = BLUE if screen_name == active_screen else DARK
            frame.fill_rect(button.x, button.y, button.width, button.height, color)
            frame.rect(button.x, button.y, button.width, button.height, GRAY)
            if screen_name == "net":
                frame.globe(button.x + 18, button.y + 24, WHITE)
                frame.text(button.x + 34, button.y + 19, button.label, WHITE)
            else:
                frame.text(button.x + 12, button.y + 19, button.label, WHITE)

    def _draw_home(self, frame: "RGB565Frame", state: UIState) -> None:
        if not state.online:
            frame.text(78, 92, "CONTROLLER OFFLINE", RED, scale=2)
            frame.text(70, 126, "Machine control unavailable", WHITE)
            frame.text(72, 150, "Physical E-stop remains active", MUTED)
            return
        for button in self.home_actions:
            color = RED if button.label == "STOP" else GREEN
            frame.fill_rect(button.x, button.y, button.width, button.height, color)
            frame.rect(button.x, button.y, button.width, button.height, GRAY)
            frame.text(button.x + 54, button.y + 52, button.label, WHITE, scale=3)
        frame.text(176, 244, "Ready to operate" if state.grbl_connected else "Waiting for laser", MUTED)

    def _draw_status(self, frame: "RGB565Frame", scroll_y: int, state: UIState) -> None:
        rows = (
            ("GRBL State", state.machine_state.title(), GREEN if state.grbl_connected else YELLOW),
            ("LightBurn", "Connected" if state.lightburn_connected else "Disconnected", GREEN if state.lightburn_connected else GRAY),
            ("Active Stream", "Active" if state.lightburn_stream_active else "None", RED if state.lightburn_stream_active else GRAY),
            ("Power", "12V OK" if state.power_present else "Off", GREEN if state.power_present else GRAY),
            ("E-stop Sense", "Active" if state.estop_active else "OK", RED if state.estop_active else GREEN),
            ("Safety Relay", "Engaged" if state.k1_energized else "Dropped", GREEN if state.k1_energized else RED),
            ("Laser USB", "Connected" if state.laser_usb_connected else "Missing", GREEN if state.laser_usb_connected else RED),
            ("Tailscale", state.tailscale_ip or "Waiting", GREEN if state.tailscale_connected else YELLOW),
        )
        y = 58 - scroll_y
        for label, value, color in rows:
            frame.fill_rect(20, y, 440, 26, PANEL)
            frame.rect(20, y, 440, 26, GRAY)
            frame.text(34, y + 9, label, WHITE)
            frame.fill_rect(288, y + 4, 142, 18, color)
            frame.text(318, y + 9, value, WHITE)
            y += 28
        self._draw_scrollbar(frame, "status", scroll_y)

    def _draw_network(self, frame: "RGB565Frame", scroll_y: int, state: UIState) -> None:
        y_offset = -scroll_y
        frame.fill_rect(18, 56 + y_offset, 214, 74, PANEL)
        frame.rect(18, 56 + y_offset, 214, 74, GRAY)
        frame.text(34, 76 + y_offset, "Ethernet", WHITE, scale=2)
        frame.text(132, 80 + y_offset, "Connected" if state.ethernet_connected else "Offline", WHITE)
        frame.text(34, 108 + y_offset, state.ethernet_ip or "No address", MUTED)

        frame.fill_rect(248, 56 + y_offset, 214, 74, PANEL)
        frame.rect(248, 56 + y_offset, 214, 74, GRAY)
        frame.text(264, 76 + y_offset, "Wi-Fi", WHITE, scale=2)
        frame.text(336, 80 + y_offset, state.wifi_ssid or "Offline", MUTED)
        frame.text(264, 108 + y_offset, state.wifi_ip or "No address", MUTED)

        frame.fill_rect(18, 140 + y_offset, 444, 112, PANEL)
        frame.rect(18, 140 + y_offset, 444, 112, GRAY)
        frame.text(36, 160 + y_offset, "Available Wi-Fi Networks", MUTED)
        networks = ("Workshop WiFi", "TravelLaser-Guest", "Office", "Other...")
        row_y = 174 + y_offset
        for index, network in enumerate(networks):
            color = BLUE if index == 0 else DARK
            frame.fill_rect(34, row_y, 410, 22, color)
            frame.text(50, row_y + 8, network, WHITE)
            frame.text(360, row_y + 8, "selected" if index == 0 else "locked", WHITE)
            row_y += 24

        toolbar = (
            Button("Scan", 18, 260 + y_offset, 100, 36),
            Button("Connect", 130, 260 + y_offset, 110, 36),
            Button("Forget", 252, 260 + y_offset, 100, 36),
            Button("Refresh", 364, 260 + y_offset, 98, 36),
        )
        for button in toolbar:
            frame.fill_rect(button.x, button.y, button.width, button.height, DARK)
            frame.rect(button.x, button.y, button.width, button.height, GRAY)
            frame.text(button.x + 20, button.y + 14, button.label, WHITE)
        self._draw_scrollbar(frame, "net", scroll_y)

    def _draw_mode(self, frame: "RGB565Frame", scroll_y: int, state: UIState) -> None:
        y_offset = -scroll_y
        frame.fill_rect(24, 66 + y_offset, 432, 72, PANEL_ALT)
        frame.rect(24, 66 + y_offset, 432, 72, BLUE)
        frame.text(56, 94 + y_offset, "Network Mode", WHITE, scale=2)
        frame.text(56, 118 + y_offset, "ACTIVE" if state.current_mode == "network" else "Select to use", MUTED)

        frame.fill_rect(24, 150 + y_offset, 432, 72, PANEL)
        frame.rect(24, 150 + y_offset, 432, 72, GRAY)
        frame.text(56, 178 + y_offset, "VirtualHere Service Mode", WHITE, scale=2)
        frame.text(56, 202 + y_offset, "ACTIVE" if state.current_mode == "virtualhere" else "Select to use", MUTED)

    def _draw_system(self, frame: "RGB565Frame", scroll_y: int) -> None:
        items = (
            "GPIO Status",
            "USB Identity",
            "SPI / I2C",
            "View Logs",
            "Export Logs to USB",
            "Restart Services",
            "Reboot",
            "Shutdown",
        )
        frame.fill_rect(24, 56 - scroll_y, 432, 244, PANEL)
        frame.rect(24, 56 - scroll_y, 432, 244, GRAY)
        y = 82 - scroll_y
        for item in items:
            frame.text(48, y, item, WHITE, scale=2)
            y += 30
        self._draw_scrollbar(frame, "system", scroll_y)

    def _draw_scrollbar(self, frame: "RGB565Frame", screen: ScreenName, scroll_y: int) -> None:
        max_scroll = self.max_scroll(screen)
        if max_scroll <= 0:
            return
        track_y = CONTENT_TOP + 6
        track_height = CONTENT_HEIGHT - 12
        thumb_height = max(24, int(track_height * CONTENT_HEIGHT / (CONTENT_HEIGHT + max_scroll)))
        thumb_y = track_y + int((track_height - thumb_height) * scroll_y / max_scroll)
        frame.fill_rect(self.width - 8, track_y, 3, track_height, DARK)
        frame.fill_rect(self.width - 9, thumb_y, 5, thumb_height, MUTED)


class RGB565Frame:
    def __init__(self, width: int, height: int, color: int = BLACK) -> None:
        self.width = width
        self.height = height
        self.data = bytearray(width * height * 2)
        self.fill(color)

    def fill(self, color: int) -> None:
        self.data[:] = color.to_bytes(2, "big") * (self.width * self.height)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        if width <= 0 or height <= 0:
            return
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

    def fill_circle(self, cx: int, cy: int, radius: int, color: int) -> None:
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                    self.fill_rect(x, y, 1, 1, color)

    def circle(self, cx: int, cy: int, radius: int, color: int) -> None:
        outer = radius**2
        inner = (radius - 1) ** 2
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                distance = (x - cx) ** 2 + (y - cy) ** 2
                if inner <= distance <= outer:
                    self.fill_rect(x, y, 1, 1, color)

    def line_h(self, x: int, y: int, width: int, color: int) -> None:
        self.fill_rect(x, y, width, 1, color)

    def line_v(self, x: int, y: int, height: int, color: int) -> None:
        self.fill_rect(x, y, 1, height, color)

    def globe(self, cx: int, cy: int, color: int) -> None:
        self.circle(cx, cy, 8, color)
        self.line_h(cx - 8, cy, 16, color)
        self.line_v(cx, cy - 8, 16, color)
        self.line_v(cx - 4, cy - 6, 12, color)
        self.line_v(cx + 4, cy - 6, 12, color)

    def text(self, x: int, y: int, text: str, color: int, scale: int = 1) -> None:
        cursor = x
        for char in text[:32]:
            self._glyph(cursor, y, char, color, scale)
            cursor += 8 * scale

    def _glyph(self, x: int, y: int, char: str, color: int, scale: int) -> None:
        code = ord(char)
        for row in range(7):
            bits = ((code << row) ^ (code >> (row % 3))) & 0x1F
            for col in range(5):
                if bits & (1 << col):
                    self.fill_rect(x + col * scale, y + row * scale, scale, scale, color)


def _contains(button: Button, x: int, y: int) -> bool:
    return button.x <= x < button.x + button.width and button.y <= y < button.y + button.height
