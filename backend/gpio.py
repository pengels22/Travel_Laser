from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol


class GPIOBackend(Protocol):
    async def initialize_safe(self) -> None: ...
    async def read_power_switch(self) -> bool: ...
    async def read_estop_switch(self) -> bool: ...
    async def set_k1(self, energized: bool) -> None: ...
    async def set_k2(self, energized: bool) -> None: ...


@dataclass
class MockGPIOBackend:
    power_switch: bool = False
    estop_switch: bool = False
    k1: bool = False
    k2: bool = False

    async def initialize_safe(self) -> None:
        self.k1 = False
        self.k2 = False

    async def read_power_switch(self) -> bool:
        return self.power_switch

    async def read_estop_switch(self) -> bool:
        return self.estop_switch

    async def set_k1(self, energized: bool) -> None:
        self.k1 = energized

    async def set_k2(self, energized: bool) -> None:
        self.k2 = energized


class LinuxGPIOBackend:
    """Thin placeholder for libgpiod/gpiod integration on Orange Pi."""

    def __init__(self, *_: object, **__: object) -> None:
        self._k1 = False
        self._k2 = False

    async def initialize_safe(self) -> None:
        await self.set_k1(False)
        await self.set_k2(False)

    async def read_power_switch(self) -> bool:
        await asyncio.sleep(0)
        return False

    async def read_estop_switch(self) -> bool:
        await asyncio.sleep(0)
        return False

    async def set_k1(self, energized: bool) -> None:
        await asyncio.sleep(0)
        self._k1 = energized

    async def set_k2(self, energized: bool) -> None:
        await asyncio.sleep(0)
        self._k2 = energized

