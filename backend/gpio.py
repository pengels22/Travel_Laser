from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from .config import GPIOConfig, GPIOLineConfig


class GPIOBackend(Protocol):
    async def initialize_safe(self) -> None: ...
    async def read_power_sense(self) -> bool: ...
    async def read_estop_sense(self) -> bool: ...
    async def set_k1(self, energized: bool) -> None: ...


@dataclass
class MockGPIOBackend:
    power_sense: bool = False
    estop_sense: bool = False
    k1: bool = False
    k1_start_energized: bool = True

    async def initialize_safe(self) -> None:
        self.k1 = self.k1_start_energized

    async def read_power_sense(self) -> bool:
        return self.power_sense

    async def read_estop_sense(self) -> bool:
        return self.estop_sense

    async def set_k1(self, energized: bool) -> None:
        self.k1 = energized


class LinuxGPIOBackend:
    """Config-driven libgpiod v2 backend for Orange Pi GPIO."""

    def __init__(self, config: GPIOConfig) -> None:
        self.config = config
        self._requests: dict[str, object] = {}
        self.k1 = False

    async def initialize_safe(self) -> None:
        self._ensure_requested()
        await self.set_k1(self.config.k1_start_energized)

    async def read_power_sense(self) -> bool:
        return await self._read("power_input", self.config.power_input)

    async def read_estop_sense(self) -> bool:
        if not _line_configured(self.config.estop_input):
            return False
        return await self._read("estop_input", self.config.estop_input)

    async def set_k1(self, energized: bool) -> None:
        await self._write("k1_output", self.config.k1_output, energized)
        self.k1 = energized

    def close(self) -> None:
        for request in self._requests.values():
            release = getattr(request, "release", None)
            if release is not None:
                release()
        self._requests.clear()

    def _ensure_requested(self) -> None:
        if self._requests:
            return

        try:
            import gpiod
            from gpiod.line import Direction, Value
        except ImportError as exc:
            raise RuntimeError("LinuxGPIOBackend requires libgpiod Python v2 bindings") from exc

        if _line_configured(self.config.power_input):
            self._requests["power_input"] = self._request_input(
                gpiod,
                Direction,
                self.config.power_input,
                "travel-laser-power-input",
            )
        if _line_configured(self.config.estop_input):
            self._requests["estop_input"] = self._request_input(
                gpiod,
                Direction,
                self.config.estop_input,
                "travel-laser-estop-input",
            )

        k1 = self.config.k1_output
        self._validate_line(k1, "k1_output")
        self._requests["k1_output"] = gpiod.request_lines(
            _chip_path(k1.chip),
            consumer="travel-laser-k1-output",
            config={
                k1.line: gpiod.LineSettings(
                    direction=Direction.OUTPUT,
                    output_value=Value.ACTIVE
                    if self._physical_value(k1, self.config.k1_start_energized)
                    else Value.INACTIVE,
                )
            },
        )

    def _request_input(self, gpiod, Direction, line_config: GPIOLineConfig, consumer: str):
        from gpiod.line import Bias

        self._validate_line(line_config, consumer)
        settings_kwargs = {"direction": Direction.INPUT}
        bias = _bias_value(Bias, line_config.bias)
        if bias is not None:
            settings_kwargs["bias"] = bias

        return gpiod.request_lines(
            _chip_path(line_config.chip),
            consumer=consumer,
            config={
                line_config.line: gpiod.LineSettings(**settings_kwargs)
            },
        )

    async def _read(self, name: str, line_config: GPIOLineConfig) -> bool:
        await asyncio.sleep(0)
        self._ensure_requested()
        if not _line_configured(line_config):
            return False

        from gpiod.line import Value

        request = self._requests[name]
        physical = request.get_value(line_config.line) == Value.ACTIVE
        return physical if line_config.active_high else not physical

    async def _write(self, name: str, line_config: GPIOLineConfig, energized: bool) -> None:
        await asyncio.sleep(0)
        self._ensure_requested()

        from gpiod.line import Value

        request = self._requests[name]
        physical = self._physical_value(line_config, energized)
        request.set_value(
            line_config.line,
            Value.ACTIVE if physical else Value.INACTIVE,
        )

    @staticmethod
    def _physical_value(line_config: GPIOLineConfig, logical: bool) -> bool:
        return logical if line_config.active_high else not logical

    @staticmethod
    def _validate_line(line_config: GPIOLineConfig, name: str) -> None:
        if not line_config.chip:
            raise ValueError(f"GPIO chip is required for {name}")
        if line_config.line is None:
            raise ValueError(f"GPIO line is required for {line_config.board_pin or name}")


def _chip_path(chip: str | None) -> str:
    if not chip:
        raise ValueError("GPIO chip is required")
    return chip if chip.startswith("/") else f"/dev/{chip}"


def _line_configured(line_config: GPIOLineConfig) -> bool:
    return bool(line_config.chip) and line_config.line is not None


def _bias_value(Bias, value: str):
    normalized = value.strip().lower()
    if normalized in {"", "none", "disabled"}:
        return Bias.DISABLED
    if normalized in {"pull-up", "pull_up", "up"}:
        return Bias.PULL_UP
    if normalized in {"pull-down", "pull_down", "down"}:
        return Bias.PULL_DOWN
    raise ValueError(f"unsupported GPIO bias: {value}")
