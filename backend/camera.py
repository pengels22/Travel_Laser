from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path

from .config import USBIdentity
from .usb import USBDevice, enumerate_usb_devices, matches_identity


@dataclass
class CameraAdapter:
    stream_url: str | None = None
    stream_type: str = "webrtc"
    identity: USBIdentity | None = None
    device_path: str | None = None
    device_provider: Callable[[], list[USBDevice]] = enumerate_usb_devices
    connected: bool = False

    async def status(self) -> dict[str, str | bool | None]:
        if self.device_path:
            path = self.device_path
            self.connected = Path(path).exists()
        elif self.identity is not None:
            devices = self.device_provider()
            matches = [device for device in devices if matches_identity(device, self.identity)]
            self.connected = len(matches) == 1
            path = matches[0].path if len(matches) == 1 else None
        else:
            path = None
        return {
            "connected": self.connected,
            "stream_url": self.stream_url,
            "stream_type": self.stream_type,
            "device_path": path,
        }
