from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class WifiNetwork:
    ssid: str
    signal: int | None = None


class NetworkManager:
    async def scan_wifi(self) -> list[WifiNetwork]:
        await asyncio.sleep(0)
        return []

    async def connect_wifi(self, ssid: str, password: str) -> bool:
        del ssid, password
        await asyncio.sleep(0)
        return True

    async def forget_wifi(self, ssid: str) -> bool:
        del ssid
        await asyncio.sleep(0)
        return True

