from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

from .events import ControllerEvent, EventCode, Severity
from .grbl_proxy import GrblProxy
from .mode_manager import ModeManager
from .network_manager import NetworkManager
from .safety import EstopSource, SafetyController
from .state import ControllerState, LaserMode, MachineState
from .log_export import USBLogExporter


class SystemActions(Protocol):
    async def restart(self) -> None: ...
    async def reboot(self) -> None: ...
    async def shutdown(self) -> None: ...


class DefaultSystemActions:
    async def _run(self, *command: str) -> None:
        process = await asyncio.create_subprocess_exec(*command)
        if await process.wait() != 0:
            raise RuntimeError(f"system action failed: {' '.join(command)}")

    async def restart(self) -> None:
        await self._run("systemctl", "restart", "travel-laser-controller.service")

    async def reboot(self) -> None:
        await self._run("systemctl", "reboot")

    async def shutdown(self) -> None:
        await self._run("systemctl", "poweroff")


class LogExporter(Protocol):
    async def export(self) -> str: ...


class DefaultLogExporter(USBLogExporter):
    pass


class CommandStatus(str, Enum):
    SUCCESS = "success"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    status: CommandStatus
    message: str
    code: str = "OK"
    data: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status.value,
            "message": self.message,
            "code": self.code,
            "data": self.data,
        }


class ControllerCommandService:
    """Single backend-owned command boundary for local and remote frontends."""

    def __init__(
        self,
        state: ControllerState,
        safety: SafetyController,
        proxy: GrblProxy,
        mode_manager: ModeManager,
        network: NetworkManager,
        system_actions: SystemActions | None = None,
        log_exporter: LogExporter | None = None,
        event_sink: object | None = None,
    ) -> None:
        self.state = state
        self.safety = safety
        self.proxy = proxy
        self.mode_manager = mode_manager
        self.network = network
        self.system_actions = system_actions or DefaultSystemActions()
        self.log_exporter = log_exporter or DefaultLogExporter()
        self.event_sink = event_sink
        self._transition_lock = asyncio.Lock()

    async def home(self) -> CommandResult:
        snapshot = await self.state.snapshot()
        blocked = self._machine_block(snapshot)
        if blocked:
            return blocked
        if not snapshot.machine.connected_to_grbl:
            return self._blocked("GRBL is not connected", "GRBL_NOT_CONNECTED")
        if not await self.proxy.home():
            return self._blocked("Home is unavailable while the machine is active", "HOME_BLOCKED")
        return self._success("Homing started")

    async def stop(self) -> CommandResult:
        try:
            await self.proxy.stop_job()
        except RuntimeError as exc:
            return self._error(str(exc), "GRBL_NOT_CONNECTED")
        return self._success("Stop requested")

    async def estop(self, source: EstopSource, reason: str | None = None) -> CommandResult:
        await self.safety.request_estop(source, reason)
        return self._success("E-stop active")

    async def network_scan(self) -> CommandResult:
        try:
            networks = await self.network.scan_wifi()
        except Exception as exc:
            return self._error(str(exc), "NETWORK_SCAN_FAILED")
        return self._success("Wi-Fi scan complete", {"networks": [network.__dict__ for network in networks]})

    async def wifi_connect(self, ssid: str, password: str) -> CommandResult:
        if not ssid:
            return self._blocked("SSID is required", "SSID_REQUIRED")
        try:
            await self.network.connect_wifi(ssid, password)
        except Exception as exc:
            return self._error(str(exc), "WIFI_CONNECT_FAILED")
        return self._success("Wi-Fi connection requested")

    async def wifi_forget(self, ssid: str) -> CommandResult:
        try:
            await self.network.forget_wifi(ssid)
        except Exception as exc:
            return self._error(str(exc), "WIFI_FORGET_FAILED")
        return self._success("Wi-Fi network forgotten")

    async def mode_change(self, mode: str) -> CommandResult:
        try:
            target = LaserMode(mode)
        except ValueError:
            return self._blocked("Unknown laser mode", "INVALID_MODE")
        async with self._transition_lock:
            snapshot = await self.state.snapshot()
            if self._machine_block(snapshot, allow_fault=True):
                return self._blocked("Machine is busy or faulted", "MODE_CHANGE_BLOCKED")
            if snapshot.physical.estop_sense or snapshot.safety.software_estop or snapshot.machine.state == MachineState.FAULT:
                return self._blocked("Machine has an active fault", "MODE_CHANGE_BLOCKED")
            if snapshot.lightburn.stream_active:
                return self._blocked("Cannot change mode while LightBurn is active", "MODE_CHANGE_BLOCKED")
            try:
                ok, reason = await self.mode_manager.switch(target)
            except Exception as exc:
                return self._error(str(exc), "MODE_CHANGE_FAILED")
        return self._success("Laser mode changed", {"mode": target.value}) if ok else self._blocked(
            reason or "Mode change was rejected", "MODE_CHANGE_BLOCKED"
        )

    async def log_export(self) -> CommandResult:
        try:
            destination = await self.log_exporter.export()
        except Exception as exc:
            return self._error(str(exc), "LOG_EXPORT_FAILED")
        return self._success("Logs exported", {"destination": destination})

    async def service_restart(self) -> CommandResult:
        safe = await self._require_system_safe()
        if safe:
            return safe
        try:
            await self.system_actions.restart()
        except Exception as exc:
            return self._error(str(exc), "SERVICE_RESTART_FAILED")
        return self._success("Controller restart requested")

    async def reboot(self) -> CommandResult:
        safe = await self._require_system_safe()
        if safe:
            return safe
        try:
            await self.system_actions.reboot()
        except Exception as exc:
            return self._error(str(exc), "REBOOT_FAILED")
        return self._success("System reboot requested")

    async def shutdown(self) -> CommandResult:
        safe = await self._require_system_safe()
        if safe:
            return safe
        try:
            await self.system_actions.shutdown()
        except Exception as exc:
            return self._error(str(exc), "SHUTDOWN_FAILED")
        return self._success("System shutdown requested")

    async def _require_system_safe(self) -> CommandResult | None:
        snapshot = await self.state.snapshot()
        if snapshot.lightburn.stream_active or snapshot.machine.state in {MachineState.RUN, MachineState.HOLD, MachineState.JOG, MachineState.HOME}:
            return self._blocked("Machine is active", "SYSTEM_ACTION_BLOCKED")
        if snapshot.physical.estop_sense or snapshot.safety.software_estop:
            return self._blocked("Machine has an active fault", "SYSTEM_ACTION_BLOCKED")
        return None

    def _machine_block(self, snapshot, allow_fault: bool = False) -> CommandResult | None:
        if snapshot.lightburn.stream_active:
            return self._blocked("LightBurn stream is active", "MACHINE_BUSY")
        if snapshot.machine.state in {MachineState.RUN, MachineState.HOLD, MachineState.JOG, MachineState.HOME}:
            return self._blocked("Machine is active", "MACHINE_BUSY")
        if not allow_fault and (snapshot.physical.estop_sense or snapshot.safety.software_estop or snapshot.machine.state == MachineState.FAULT):
            return self._blocked("Machine has an active fault", "MACHINE_FAULT")
        return None

    def _success(self, message: str, data: dict[str, Any] | None = None) -> CommandResult:
        return CommandResult(True, CommandStatus.SUCCESS, message, data=data or {})

    def _blocked(self, message: str, code: str) -> CommandResult:
        return CommandResult(False, CommandStatus.BLOCKED, message, code=code)

    def _error(self, message: str, code: str) -> CommandResult:
        return CommandResult(False, CommandStatus.ERROR, message, code=code)
