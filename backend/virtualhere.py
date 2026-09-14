from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class VirtualHereService:
    service_name: str = "virtualhere"
    installed: bool = False
    active: bool = False

    async def start(self) -> bool:
        await asyncio.sleep(0)
        self.active = True
        return True

    async def stop(self) -> bool:
        await asyncio.sleep(0)
        self.active = False
        return True

    async def is_active(self) -> bool:
        await asyncio.sleep(0)
        return self.active

