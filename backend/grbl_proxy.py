from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Protocol

from .events import EventCode, Severity
from .grbl_parser import parse_error_line, parse_status_line
from .safety import SafetyController
from .state import ControllerState, MachineState

LOGGER = logging.getLogger(__name__)
REALTIME_PAUSE = b"!"
REALTIME_RESUME = b"~"
REALTIME_STOP = b"\x18"
STATUS_QUERY = b"?"
REALTIME_BYTES = {REALTIME_PAUSE[0], REALTIME_RESUME[0], REALTIME_STOP[0], STATUS_QUERY[0]}
JOB_TRAFFIC_PATTERN = re.compile(rb"(^|\s)(G0|G00|G1|G01|G2|G02|G3|G03|M3|M03|M4|M04)\b", re.IGNORECASE)
CUSTOM_COMMAND_ERRORS = {
    "CUSTOM_HANDLER_UNAVAILABLE": 110,
    "CUSTOM_ESTOP_FAILED": 111,
    "CUSTOM_RECOVERY_BLOCKED": 112,
    "CUSTOM_RECOVERY_FAILED": 113,
    "GCODE_BLOCKED": 121,
}


class MockSerialEndpoint:
    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.connected = True
        self._rx: asyncio.Queue[bytes] = asyncio.Queue()

    async def write(self, data: bytes) -> None:
        self.written.append(data)

    async def read(self, n: int = 4096) -> bytes:
        del n
        return await self._rx.get()

    async def inject_rx(self, data: bytes) -> None:
        await self._rx.put(data)

    async def close(self) -> None:
        self.connected = False


class SerialEndpoint(Protocol):
    async def write(self, data: bytes) -> None: ...
    async def read(self, n: int = 4096) -> bytes: ...
    async def close(self) -> None: ...


class CustomCommandHandler(Protocol):
    async def custom_m112_estop(self) -> object: ...
    async def recover_to_ready(self) -> object: ...


class GrblProxy:
    def __init__(
        self,
        state: ControllerState,
        safety: SafetyController,
        host: str = "0.0.0.0",
        port: int = 23,
        serial_factory: Callable[[], Awaitable[SerialEndpoint]] | None = None,
        status_poll_interval: float = 0.25,
        custom_command_handler: CustomCommandHandler | None = None,
    ) -> None:
        self.state = state
        self.safety = safety
        self.host = host
        self.port = port
        self.status_poll_interval = status_poll_interval
        self.serial_factory = serial_factory or self._default_serial_factory
        self.custom_command_handler = custom_command_handler
        self.serial: SerialEndpoint | None = None
        self.server: asyncio.AbstractServer | None = None
        self.active = False
        self._client_connected = False
        self._poll_task: asyncio.Task | None = None
        self._serial_read_task: asyncio.Task | None = None
        self._recovery_task: asyncio.Task | None = None
        self._client_writer: asyncio.StreamWriter | None = None
        self._homing_requested = False
        self._homing_in_progress = False

    def set_custom_command_handler(self, handler: CustomCommandHandler) -> None:
        self.custom_command_handler = handler

    async def start(self) -> None:
        if self.active:
            await self._ensure_serial_started()
            return
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        self.active = True
        await self._ensure_serial_started()

    async def _ensure_serial_started(self) -> bool:
        if self.serial:
            return True
        try:
            self.serial = await self.serial_factory()
        except Exception as exc:
            LOGGER.warning("laser proxy serial waiting for USB: %s", exc)
            await self._mark_grbl_disconnected()
            if not self._recovery_task or self._recovery_task.done():
                self._recovery_task = asyncio.create_task(self._recover_when_safe())
            return False
        def mutate(snapshot):
            snapshot.machine.laser_usb_connected = True
            snapshot.machine.connected_to_grbl = True
            if snapshot.machine.state == MachineState.OFFLINE:
                snapshot.machine.state = MachineState.IDLE

        await self.state.update(mutate)
        self.safety.record(EventCode.LASER_USB_CONNECTED, Severity.INFO, "grbl_proxy")
        self._poll_task = asyncio.create_task(self._status_poll_loop())
        self._serial_read_task = asyncio.create_task(self._serial_read_loop())
        return True

    async def stop(self) -> None:
        if self._recovery_task and self._recovery_task is not asyncio.current_task():
            self._recovery_task.cancel()
            await asyncio.gather(self._recovery_task, return_exceptions=True)
            self._recovery_task = None
        self.active = False
        if self._poll_task:
            self._poll_task.cancel()
            await asyncio.gather(self._poll_task, return_exceptions=True)
            self._poll_task = None
        if self._serial_read_task:
            self._serial_read_task.cancel()
            await asyncio.gather(self._serial_read_task, return_exceptions=True)
            self._serial_read_task = None
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None
        if self._client_writer:
            self._client_writer.close()
            await self._client_writer.wait_closed()
            self._client_writer = None
            self._client_connected = False
        if self.serial:
            await self.serial.close()
            self.serial = None

        def mutate(snapshot):
            snapshot.lightburn.connected = False
            snapshot.lightburn.stream_active = False
            snapshot.machine.laser_usb_connected = False
            snapshot.machine.connected_to_grbl = False

        await self.state.update(mutate)

    async def pause(self) -> None:
        await self.inject_realtime(REALTIME_PAUSE)

    async def resume(self) -> None:
        await self.inject_realtime(REALTIME_RESUME)

    async def stop_job(self) -> None:
        await self.inject_realtime(REALTIME_STOP)

        def mutate(snapshot):
            snapshot.machine.homed = False
            snapshot.lightburn.stream_active = False

        await self.state.update(mutate)

    async def home(self) -> bool:
        snapshot = await self.state.snapshot()
        if snapshot.lightburn.stream_active or snapshot.machine.state in {MachineState.RUN, MachineState.HOLD, MachineState.JOG}:
            return False
        await self._write_serial(b"$H\n")
        self._homing_requested = True
        self._homing_in_progress = False
        return True

    async def jog(self, axis: str, distance: float) -> bool:
        snapshot = await self.state.snapshot()
        if snapshot.lightburn.stream_active or snapshot.machine.state in {MachineState.RUN, MachineState.HOLD, MachineState.JOG}:
            return False
        axis = axis.upper()
        if axis not in {"X", "Y", "Z"}:
            return False
        await self._write_serial(f"$J=G91 {axis}{distance} F1000\n".encode())
        return True

    async def inject_realtime(self, command: bytes) -> None:
        await self._write_serial(command)

    async def ensure_connected(self, timeout: float = 10.0) -> bool:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            snapshot = await self.state.snapshot()
            if self.serial and snapshot.machine.connected_to_grbl:
                return True
            if snapshot.physical.k1:
                await self._ensure_serial_started()
            await asyncio.sleep(0.1)
        return False

    async def wait_for_homing_complete(self, timeout: float = 30.0) -> bool:
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            snapshot = await self.state.snapshot()
            if snapshot.machine.homed and snapshot.machine.state == MachineState.IDLE:
                return True
            if snapshot.machine.state in {MachineState.ALARM, MachineState.FAULT}:
                return False
            await asyncio.sleep(0.05)
        return False

    async def _write_serial(self, data: bytes) -> None:
        if not self.serial:
            raise RuntimeError("GRBL serial is not connected")
        await self.serial.write(data)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        if self._client_connected:
            writer.close()
            await writer.wait_closed()
            return
        self._client_connected = True
        self._client_writer = writer
        peer = writer.get_extra_info("peername")
        LOGGER.info("LightBurn TCP client connected from %s", peer)

        def connected(snapshot):
            snapshot.lightburn.connected = True

        await self.state.update(connected)
        self.safety.record(EventCode.LIGHTBURN_CONNECTED, Severity.INFO, "grbl_proxy")
        pending_line = b""
        job_invalidated = False
        try:
            while not reader.at_eof():
                data = await reader.read(4096)
                if not data:
                    break
                pending_line, job_invalidated = await self._process_client_data(data, pending_line, writer, job_invalidated)
            if pending_line:
                await self._handle_complete_client_line(pending_line, writer, job_invalidated)
        finally:
            self._client_connected = False
            if self._client_writer is writer:
                self._client_writer = None
            LOGGER.info("LightBurn TCP client disconnected")
            writer.close()
            await writer.wait_closed()
            await self.safety.handle_lightburn_disconnect()

    async def _process_client_data(
        self,
        data: bytes,
        pending_line: bytes,
        writer: asyncio.StreamWriter,
        job_invalidated: bool,
    ) -> tuple[bytes, bool]:
        for byte in data:
            if byte in REALTIME_BYTES:
                if pending_line:
                    job_invalidated = await self._handle_complete_client_line(pending_line, writer, job_invalidated)
                    pending_line = b""
                await self._forward_realtime_byte(bytes([byte]))
                continue
            pending_line += bytes([byte])
            if byte == 0x0A:
                job_invalidated = await self._handle_complete_client_line(pending_line, writer, job_invalidated)
                pending_line = b""
        return pending_line, job_invalidated

    async def _handle_complete_client_line(self, line: bytes, writer: asyncio.StreamWriter, job_invalidated: bool) -> bool:
        command = line.strip().upper()
        if command == b"M112":
            await self._handle_custom_m112(writer)
            return True
        if command == b"M113":
            await self._handle_custom_m113(writer)
            return True
        if not await self._normal_gcode_allowed(job_invalidated):
            await self._write_client_custom_error(writer, "GCODE_BLOCKED")
            return job_invalidated
        await self._forward_client_line(line, line)
        return job_invalidated

    async def _normal_gcode_allowed(self, job_invalidated: bool) -> bool:
        snapshot = await self.state.snapshot()
        return (
            not job_invalidated
            and self.serial is not None
            and snapshot.machine.connected_to_grbl
            and snapshot.machine.state not in {MachineState.FAULT, MachineState.RECOVERING}
            and not snapshot.safety.software_estop
            and not snapshot.safety.remote_estop
            and not snapshot.physical.estop_sense
        )

    async def _forward_client_line(self, wire_line: bytes, traffic_line: bytes) -> None:
        await self._write_serial(wire_line)
        await self._mark_stream_if_job_traffic(traffic_line)

    async def _forward_realtime_byte(self, command: bytes) -> None:
        if self.serial is None:
            return
        try:
            await self._write_serial(command)
        except RuntimeError:
            return

    async def _mark_stream_if_job_traffic(self, data: bytes) -> None:
        if not self._is_meaningful_job_traffic(data):
            return
        before_stream = (await self.state.snapshot()).lightburn.stream_active

        def mark_stream(snapshot):
            snapshot.lightburn.stream_active = True

        await self.state.update(mark_stream)
        if not before_stream:
            self.safety.record(EventCode.LIGHTBURN_STREAM_STARTED, Severity.INFO, "grbl_proxy")

    async def _handle_custom_m112(self, writer: asyncio.StreamWriter) -> None:
        if not self.custom_command_handler:
            await self._write_client_custom_error(writer, "CUSTOM_HANDLER_UNAVAILABLE")
            return
        result = await self.custom_command_handler.custom_m112_estop()
        if bool(getattr(result, "ok", False)):
            await self._write_client_custom_ok(writer)
        else:
            await self._write_client_custom_error(writer, "CUSTOM_ESTOP_FAILED")

    async def _handle_custom_m113(self, writer: asyncio.StreamWriter) -> None:
        if not self.custom_command_handler:
            await self._write_client_custom_error(writer, "CUSTOM_HANDLER_UNAVAILABLE")
            return
        result = await self.custom_command_handler.recover_to_ready()
        if bool(getattr(result, "ok", False)):
            await self._write_client_custom_ok(writer)
            return
        status = str(getattr(getattr(result, "status", ""), "value", getattr(result, "status", "")))
        await self._write_client_custom_error(
            writer,
            "CUSTOM_RECOVERY_BLOCKED" if status == "blocked" else "CUSTOM_RECOVERY_FAILED",
        )

    async def _write_client_custom_ok(self, writer: asyncio.StreamWriter) -> None:
        writer.write(b"ok\r\n")
        await writer.drain()

    async def _write_client_custom_error(self, writer: asyncio.StreamWriter, code: str) -> None:
        writer.write(f"error:{CUSTOM_COMMAND_ERRORS[code]}\r\n".encode())
        await writer.drain()

    async def handle_serial_line(self, line: str) -> None:
        status = parse_status_line(line)
        error = parse_error_line(line)
        completed_home = False
        if status:
            if status.state == MachineState.HOME and self._homing_requested:
                self._homing_in_progress = True
            elif status.state == MachineState.IDLE and self._homing_in_progress:
                self._homing_requested = False
                self._homing_in_progress = False
                completed_home = True
            elif status.state == MachineState.ALARM:
                self._homing_requested = False
                self._homing_in_progress = False
        if error and error.lower().startswith("alarm:"):
            self._homing_requested = False
            self._homing_in_progress = False

        def mutate(snapshot):
            if status:
                snapshot.machine.state = status.state
                snapshot.machine.mpos = status.mpos
                snapshot.machine.wpos = status.wpos
                snapshot.machine.feed = status.feed
                snapshot.machine.spindle = status.spindle
                if completed_home:
                    snapshot.machine.homed = True
                if status.state == MachineState.IDLE:
                    snapshot.lightburn.stream_active = False
            if error:
                snapshot.machine.error = error
                if error.lower().startswith("alarm:"):
                    snapshot.machine.state = MachineState.ALARM
                    snapshot.machine.homed = False

        await self.state.update(mutate)
        if error:
            self.safety.record(
                EventCode.GRBL_ALARM if error.lower().startswith("alarm:") else EventCode.GRBL_ERROR,
                Severity.CRITICAL if error.lower().startswith("alarm:") else Severity.WARNING,
                "grbl",
                {"line": error},
            )

    async def _status_poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self.status_poll_interval)
            if self.serial:
                try:
                    await self.serial.write(STATUS_QUERY)
                except Exception as exc:
                    LOGGER.error("laser serial status poll failed: %s", exc)
                    await self._handle_serial_loss()
                    return

    async def _serial_read_loop(self) -> None:
        pending = b""
        while True:
            if not self.serial:
                return
            try:
                data = await self.serial.read()
            except Exception as exc:
                LOGGER.error("laser serial read failed: %s", exc)
                await self._handle_serial_loss()
                return
            if not data:
                await self._handle_serial_loss()
                return
            await self._forward_serial_to_client(data)
            pending += data
            lines = pending.split(b"\n")
            pending = lines.pop()
            for line in lines:
                await self.handle_serial_line(line.decode(errors="replace").rstrip("\r"))

    async def _forward_serial_to_client(self, data: bytes) -> None:
        writer = self._client_writer
        if writer is None or writer.is_closing():
            return
        try:
            writer.write(data)
            await writer.drain()
        except (ConnectionError, RuntimeError, OSError) as exc:
            LOGGER.info("LightBurn TCP client write failed: %s", exc)
            if self._client_writer is writer:
                self._client_writer = None

    async def _handle_serial_loss(self) -> None:
        self._homing_requested = False
        self._homing_in_progress = False
        if self._poll_task and self._poll_task is not asyncio.current_task():
            self._poll_task.cancel()
            await asyncio.gather(self._poll_task, return_exceptions=True)
            self._poll_task = None
        if self._serial_read_task and self._serial_read_task is not asyncio.current_task():
            self._serial_read_task.cancel()
            await asyncio.gather(self._serial_read_task, return_exceptions=True)
            self._serial_read_task = None
        if self.serial:
            await self.serial.close()
            self.serial = None

        await self._mark_grbl_disconnected()
        await self.safety.handle_laser_usb_disconnected()
        if not self._recovery_task or self._recovery_task.done():
            self._recovery_task = asyncio.create_task(self._recover_when_safe())

    async def _recover_when_safe(self) -> None:
        while True:
            snapshot = await self.state.snapshot()
            blocked = (
                not snapshot.physical.k1
                or snapshot.physical.estop_sense
                or snapshot.safety.remote_estop
                or snapshot.safety.software_estop
                or (snapshot.safety.fire_enabled and snapshot.safety.fire_active)
            )
            if not blocked and self.active and not self.serial:
                if await self._ensure_serial_started():
                    self._recovery_task = None
                    return
            await asyncio.sleep(1.0)

    async def _mark_grbl_disconnected(self) -> None:
        def mutate(snapshot):
            snapshot.machine.laser_usb_connected = False
            snapshot.machine.connected_to_grbl = False
            snapshot.machine.homed = False

        await self.state.update(mutate)

    async def _default_serial_factory(self) -> MockSerialEndpoint:
        return MockSerialEndpoint()

    def _is_meaningful_job_traffic(self, data: bytes) -> bool:
        for command in data.replace(b"\r", b"\n").split(b"\n"):
            stripped = command.strip()
            if not stripped or stripped in {b"?", b"!", b"~", b"\x18"}:
                continue
            if stripped.startswith((b"$", b"(", b";")):
                continue
            if JOB_TRAFFIC_PATTERN.search(stripped):
                return True
        return False
