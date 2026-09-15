from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .state import utc_now_iso


class Severity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class EventCode(str, Enum):
    POWER_SWITCH_ON = "POWER_SWITCH_ON"
    POWER_SWITCH_OFF = "POWER_SWITCH_OFF"
    PHYSICAL_ESTOP_ON = "PHYSICAL_ESTOP_ON"
    PHYSICAL_ESTOP_OFF = "PHYSICAL_ESTOP_OFF"
    TS1_ESTOP = "TS1_ESTOP"
    WEB_ESTOP = "WEB_ESTOP"
    SOFTWARE_ESTOP = "SOFTWARE_ESTOP"
    K1_ON = "K1_ON"
    K1_OFF = "K1_OFF"
    LIGHTBURN_CONNECTED = "LIGHTBURN_CONNECTED"
    LIGHTBURN_DISCONNECTED = "LIGHTBURN_DISCONNECTED"
    LIGHTBURN_STREAM_STARTED = "LIGHTBURN_STREAM_STARTED"
    LIGHTBURN_STREAM_LOST = "LIGHTBURN_STREAM_LOST"
    LASER_USB_CONNECTED = "LASER_USB_CONNECTED"
    LASER_USB_DISCONNECTED = "LASER_USB_DISCONNECTED"
    CAMERA_USB_CONNECTED = "CAMERA_USB_CONNECTED"
    CAMERA_USB_DISCONNECTED = "CAMERA_USB_DISCONNECTED"
    TS1_CONNECTED = "TS1_CONNECTED"
    TS1_DISCONNECTED = "TS1_DISCONNECTED"
    WIFI_CONNECTED = "WIFI_CONNECTED"
    WIFI_DISCONNECTED = "WIFI_DISCONNECTED"
    WIFI_CHANGED = "WIFI_CHANGED"
    IP_CHANGED = "IP_CHANGED"
    MODE_CHANGED = "MODE_CHANGED"
    GRBL_ALARM = "GRBL_ALARM"
    GRBL_ERROR = "GRBL_ERROR"
    CONTROLLER_RECOVERED = "CONTROLLER_RECOVERED"
    CAMERA_FAILURE = "CAMERA_FAILURE"


@dataclass(frozen=True)
class ControllerEvent:
    code: EventCode
    severity: Severity = Severity.INFO
    source: str = "backend"
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)

    def as_log_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "severity": self.severity.value,
            "event": self.code.value,
            "source": self.source,
            "details": self.details,
        }
