from __future__ import annotations

import asyncio

from .touch_interface import TouchEvent, TouchPoint


class FT6336Touch:
    def __init__(
        self,
        i2c_bus: int,
        address: int = 0x38,
        width: int = 480,
        height: int = 320,
        rotation: int = 90,
        poll_interval: float = 0.03,
    ) -> None:
        self.i2c_bus = i2c_bus
        self.address = address
        self.width = width
        self.height = height
        self.rotation = rotation
        self.poll_interval = poll_interval
        self._bus = None
        self._was_down = False

    async def initialize(self) -> None:
        from smbus2 import SMBus

        self._bus = SMBus(self.i2c_bus)
        await asyncio.sleep(0)

    async def read_event(self) -> TouchEvent | None:
        await asyncio.sleep(self.poll_interval)
        if self._bus is None:
            raise RuntimeError("FT6336Touch is not initialized")
        data = self._bus.read_i2c_block_data(self.address, 0x02, 11)
        count = data[0] & 0x0F
        if count == 0:
            if self._was_down:
                self._was_down = False
                return TouchEvent("up", ())
            return None

        raw_x = ((data[1] & 0x0F) << 8) | data[2]
        raw_y = ((data[3] & 0x0F) << 8) | data[4]
        x, y = self._transform(raw_x, raw_y)
        kind = "move" if self._was_down else "down"
        self._was_down = True
        return TouchEvent(kind, (TouchPoint(0, x, y),))

    async def close(self) -> None:
        if self._bus is not None:
            self._bus.close()

    def _transform(self, raw_x: int, raw_y: int) -> tuple[int, int]:
        if self.rotation == 90:
            x = raw_y
            y = self.height - 1 - raw_x
        elif self.rotation == 270:
            x = self.width - 1 - raw_y
            y = raw_x
        elif self.rotation == 180:
            x = self.width - 1 - raw_x
            y = self.height - 1 - raw_y
        else:
            x = raw_x
            y = raw_y
        return max(0, min(self.width - 1, x)), max(0, min(self.height - 1, y))

