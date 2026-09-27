from __future__ import annotations

from backend.config import GPIOConfig, GPIOLineConfig
from backend.gpio import LinuxGPIOBackend


async def test_unconfigured_estop_feedback_reads_inactive() -> None:
    backend = LinuxGPIOBackend(
        GPIOConfig(
            estop_input=GPIOLineConfig(chip=None, line=None),
            k1_output=GPIOLineConfig(chip="/dev/gpiochip1", line=72),
        )
    )

    assert await backend.read_estop_sense() is False
