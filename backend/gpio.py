from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from .config import GPIOConfig, GPIOLineConfig


class GPIOBackend(Protocol):
    async def initialize_safe(self) -> None: ...
    async def read_power_switch(self) -> bool: ...
    async def read_estop_switch(self) -> bool: ...
    async def set_k1(self, energized: bool) -> None: ...


@dataclass
class MockGPIOBackend:
    power_switch: bool = False
    estop_switch: bool = False
    k1: bool = False

    async def initialize_safe(self) -> None:
        self.k1 = False

    async def read_power_switch(self) -> bool:
        return self.power_switch

    async def read_estop_switch(self) -> bool:
        return self.estop_switch

    async def set_k1(self, energized: bool) -> None:
        self.k1 = energized


class LinuxGPIOBackend:
    """Config-driven libgpiod backend for Orange Pi GPIO."""

    def __init__(self, config: GPIOConfig) -> None:
        self.config = config
        self._chip = None
        self._lines: dict[str, object] = {}

    async def initialize_safe(self) -> None:
        self._ensure_requested()
        await self.set_k1(False)

    async def read_power_switch(self) -> bool:
        return await self._read("power_input", self.config.power_input)

    async def read_estop_switch(self) -> bool:
        return await self._read("estop_input", self.config.estop_input)

    async def set_k1(self, energized: bool) -> None:
        await self._write("k1_output", self.config.k1_output, energized)

    def _ensure_requested(self) -> None:
        try:
            import gpiod
        except ImportError as exc:
            raise RuntimeError("LinuxGPIOBackend requires python3-libgpiod or the gpiod Python package") from exc

        chip_name = self.config.k1_output.chip
        if not chip_name:
            raise ValueError("GPIO chip is required for LinuxGPIOBackend")
        self._chip = gpiod.Chip(chip_name)
        self._request_input(gpiod, "power_input", self.config.power_input)
        self._request_input(gpiod, "estop_input", self.config.estop_input)
        self._request_output(gpiod, "k1_output", self.config.k1_output, False)

    def _request_input(self, gpiod, name: str, line_config: GPIOLineConfig) -> None:
        line = self._get_line(line_config)
        line.request(consumer="travel-laser-controller", type=gpiod.LINE_REQ_DIR_IN)
        self._lines[name] = line

    def _request_output(self, gpiod, name: str, line_config: GPIOLineConfig, energized: bool) -> None:
        line = self._get_line(line_config)
        physical = self._physical_value(line_config, energized)
        line.request(consumer="travel-laser-controller", type=gpiod.LINE_REQ_DIR_OUT, default_vals=[physical])
        self._lines[name] = line

    def _get_line(self, line_config: GPIOLineConfig):
        if self._chip is None:
            raise RuntimeError("GPIO chip is not open")
        if line_config.line is None:
            raise ValueError(f"GPIO line is required for {line_config.board_pin or 'unnamed line'}")
        return self._chip.get_line(line_config.line)

    async def _read(self, name: str, line_config: GPIOLineConfig) -> bool:
        await asyncio.sleep(0)
        line = self._lines[name]
        physical = bool(line.get_value())
        return physical if line_config.active_high else not physical

    async def _write(self, name: str, line_config: GPIOLineConfig, energized: bool) -> None:
        await asyncio.sleep(0)
        if not self._lines:
            self._ensure_requested()
        line = self._lines[name]
        line.set_value(self._physical_value(line_config, energized))

    def _physical_value(self, line_config: GPIOLineConfig, logical: bool) -> int:
        value = logical if line_config.active_high else not logical
        return 1 if value else 0
