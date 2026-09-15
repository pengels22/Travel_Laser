from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class WifiNetwork:
    ssid: str
    signal: int | None = None


class NetworkManager:
    def __init__(self, uplink_interface: str = "wlan1") -> None:
        self.uplink_interface = uplink_interface
        self.actions: list[tuple[str, str, str | None]] = []

    async def scan_wifi(self, interface: str | None = None) -> list[WifiNetwork]:
        interface = interface or self.uplink_interface
        self.actions.append(("scan", interface, None))
        await asyncio.sleep(0)
        return []

    async def connect_wifi(self, ssid: str, password: str, interface: str | None = None) -> bool:
        del password
        interface = interface or self.uplink_interface
        self.actions.append(("connect", interface, ssid))
        await asyncio.sleep(0)
        return True

    async def forget_wifi(self, ssid: str, interface: str | None = None) -> bool:
        interface = interface or self.uplink_interface
        self.actions.append(("forget", interface, ssid))
        await asyncio.sleep(0)
        return True
