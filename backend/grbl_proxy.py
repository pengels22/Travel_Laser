from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

from .grbl_parser import parse_error_line, parse_status_line
from .safety import SafetyController
from .state import ControllerState, MachineState

LOGGER = logging.getLogger(__name__)
REALTIME_PAUSE = b"!"
REALTIME_RESUME = b"~"
REALTIME_STOP = b"\x18"
STATUS_QUERY = b"?"


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


class GrblProxy:
    def __init__(
        self,
        state: ControllerState,
        safety: SafetyController,
        host: str = "0.0.0.0",
        port: int = 23,
        serial_factory: Callable[[], Awaitable[SerialEndpoint]] | None = None,
        status_poll_interval: float = 0.25,
    ) -> None:
        self.state = state
        self.safety = safety
        self.host = host
        self.port = port
        self.status_poll_interval = status_poll_interval
        self.serial_factory = serial_factory or self._default_serial_factory
        self.serial: SerialEndpoint | None = None
        self.server: asyncio.AbstractServer | None = None
        self.active = False
        self._client_connected = False
        self._poll_task: asyncio.Task | None = None
        self._serial_read_task: asyncio.Task | None = None

    async def start(self) -> None:
        if self.active:
            return
        self.serial = await self.serial_factory()
        self.server = await asyncio.start_server(self._handle_client, self.host, self.port)
        self.active = True

        def mutate(snapshot):
            snapshot.machine.laser_usb_connected = True
            snapshot.machine.connected_to_grbl = True
            snapshot.machine.state = MachineState.IDLE

        await self.state.update(mutate)
        self._poll_task = asyncio.create_task(self._status_poll_loop())
        self._serial_read_task = asyncio.create_task(self._serial_read_loop())

    async def stop(self) -> None:
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
        if self.serial:
            await self.serial.close()
            self.serial = None

        def mutate(snapshot):
            snapshot.lightburn.connected = False
            snapshot.lightburn.stream_active = False
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

        def connected(snapshot):
            snapshot.lightburn.connected = True

        await self.state.update(connected)
        try:
            while not reader.at_eof():
                data = await reader.read(4096)
                if not data:
                    break
                await self._write_serial(data)
                if self._is_meaningful_job_traffic(data):
                    def mark_stream(snapshot):
                        snapshot.lightburn.stream_active = True

                    await self.state.update(mark_stream)
        finally:
            self._client_connected = False
            writer.close()
            await writer.wait_closed()
            await self.safety.handle_lightburn_disconnect()

    async def handle_serial_line(self, line: str) -> None:
        status = parse_status_line(line)
        error = parse_error_line(line)

        def mutate(snapshot):
            if status:
                snapshot.machine.state = status.state
                snapshot.machine.mpos = status.mpos
                snapshot.machine.wpos = status.wpos
                snapshot.machine.feed = status.feed
                snapshot.machine.spindle = status.spindle
                if status.state == MachineState.IDLE:
                    snapshot.lightburn.stream_active = False
            if error:
                snapshot.machine.error = error
                if error.lower().startswith("alarm:"):
                    snapshot.machine.state = MachineState.ALARM

        await self.state.update(mutate)

    async def _status_poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self.status_poll_interval)
            if self.serial:
                try:
                    await self.serial.write(STATUS_QUERY)
                except Exception as exc:
                    LOGGER.error("laser serial status poll failed: %s", exc)
                    await self.safety.handle_laser_usb_disconnected()
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
                await self.safety.handle_laser_usb_disconnected()
                return
            if not data:
                await self.safety.handle_laser_usb_disconnected()
                return
            pending += data
            lines = pending.split(b"\n")
            pending = lines.pop()
            for line in lines:
                await self.handle_serial_line(line.decode(errors="replace").rstrip("\r"))
                await self.handle_serial_line(line)

    async def _default_serial_factory(self) -> MockSerialEndpoint:
        return MockSerialEndpoint()

    def _is_meaningful_job_traffic(self, data: bytes) -> bool:
        stripped = data.strip()
        if not stripped or stripped in {b"?", b"!", b"~", b"\x18"}:
            return False
        return True
