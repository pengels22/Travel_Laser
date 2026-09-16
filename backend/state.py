from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MachineState(str, Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    RUN = "run"
    HOLD = "hold"
    JOG = "jog"
    ALARM = "alarm"
    HOME = "home"
    CHECK = "check"
    DOOR = "door"
    SLEEP = "sleep"
    RECOVERING = "recovering"
    FAULT = "fault"


class LaserMode(str, Enum):
    NETWORK = "network"
    VIRTUALHERE = "virtualhere"


@dataclass
class PhysicalState:
    power_sense: bool = False
    estop_sense: bool = False
    k1: bool = False


@dataclass
class MachineRuntimeState:
    state: MachineState = MachineState.OFFLINE
    homed: bool = False
    error: str | None = None
    laser_usb_connected: bool = False
    connected_to_grbl: bool = False
    mpos: tuple[float, ...] | None = None
    wpos: tuple[float, ...] | None = None
    feed: float | None = None
    spindle: float | None = None


@dataclass
class LightBurnState:
    connected: bool = False
    stream_active: bool = False


@dataclass
class CameraState:
    connected: bool = False
    stream_url: str | None = None
    stream_type: str = "webrtc"


@dataclass
class NetworkState:
    ethernet_connected: bool = False
    wifi_connected: bool = False
    wifi_ssid: str | None = None
    ip_address: str | None = None
    tailscale_connected: bool = False
    tailscale_interface: str = "tailscale0"
    tailscale_ip: str | None = None
    tailscale_status: str = "not configured"


@dataclass
class SafetyState:
    remote_estop: bool = False
    software_estop: bool = False
    fire_enabled: bool = False
    fire_active: bool = False


@dataclass
class ModeState:
    laser_mode: LaserMode = LaserMode.NETWORK


@dataclass
class ControllerSnapshot:
    physical: PhysicalState = field(default_factory=PhysicalState)
    machine: MachineRuntimeState = field(default_factory=MachineRuntimeState)
    lightburn: LightBurnState = field(default_factory=LightBurnState)
    camera: CameraState = field(default_factory=CameraState)
    network: NetworkState = field(default_factory=NetworkState)
    safety: SafetyState = field(default_factory=SafetyState)
    mode: ModeState = field(default_factory=ModeState)
    ready: bool = False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ControllerState:
    """Asyncio-safe state container with explicit mutation ownership."""

    def __init__(self, initial: ControllerSnapshot | None = None) -> None:
        self._snapshot = initial or ControllerSnapshot()
        self._lock = asyncio.Lock()

    async def snapshot(self) -> ControllerSnapshot:
        async with self._lock:
            return self._copy_snapshot()

    async def update(self, mutator: Any) -> ControllerSnapshot:
        async with self._lock:
            mutator(self._snapshot)
            return self._copy_snapshot()

    async def to_dict(self) -> dict[str, Any]:
        async with self._lock:
            return _enum_to_value(asdict(self._snapshot))

    def _copy_snapshot(self) -> ControllerSnapshot:
        data = asdict(self._snapshot)
        return ControllerSnapshot(
            physical=PhysicalState(**data["physical"]),
            machine=MachineRuntimeState(
                **{
                    **data["machine"],
                    "state": MachineState(data["machine"]["state"]),
                }
            ),
            lightburn=LightBurnState(**data["lightburn"]),
            camera=CameraState(**data["camera"]),
            network=NetworkState(**data["network"]),
            safety=SafetyState(**data["safety"]),
            mode=ModeState(laser_mode=LaserMode(data["mode"]["laser_mode"])),
            ready=data["ready"],
        )


def _enum_to_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _enum_to_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_enum_to_value(item) for item in value]
    if isinstance(value, tuple):
        return [_enum_to_value(item) for item in value]
    return value
