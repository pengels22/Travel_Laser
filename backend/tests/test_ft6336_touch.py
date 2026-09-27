from __future__ import annotations

import pytest

from backend.input.ft6336_touch import FT6336Touch


class _FailingBus:
    closed = False

    def read_i2c_block_data(self, _address: int, _register: int, _length: int) -> list[int]:
        raise OSError(6, "No such device or address")

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_ft6336_read_error_recovers_without_crashing(monkeypatch) -> None:
    touch = FT6336Touch(i2c_bus=2, poll_interval=0)
    bus = _FailingBus()
    touch._bus = bus
    touch._was_down = True
    recovered = False

    async def recover_bus() -> None:
        nonlocal recovered
        recovered = True

    monkeypatch.setattr(touch, "_recover_bus", recover_bus)

    assert await touch.read_event() is None
    assert recovered is True
    assert touch._was_down is False
