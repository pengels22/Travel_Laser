import asyncio
from pathlib import Path

import backend.grbl_proxy as grbl_proxy_module
from backend.command_service import ControllerCommandService
from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import REALTIME_PAUSE, REALTIME_RESUME, REALTIME_STOP, GrblProxy, MockSerialEndpoint
from backend.mode_manager import ModeManager
from backend.network_manager import NetworkManager
from backend.safety import EstopSource, SafetyController
from backend.state import ControllerState, MachineState
from backend.virtualhere import VirtualHereService


async def _proxy(port: int = 0):
    state = ControllerState()
    gpio = MockGPIOBackend(power_sense=True)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()
    await safety.refresh_physical_inputs()
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=port, status_poll_interval=60)
    await proxy.start()
    return state, safety, proxy


async def _command_proxy(tmp_path: Path, port: int = 0):
    state = ControllerState()
    gpio = MockGPIOBackend(power_sense=True)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()
    await safety.refresh_physical_inputs()
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=port, status_poll_interval=60)
    virtualhere = VirtualHereService()
    manager = ModeManager(state, proxy, virtualhere, tmp_path / "mode.json")
    commands = ControllerCommandService(state, safety, proxy, manager, NetworkManager(dry_run=True))
    commands.recovery_connect_timeout_seconds = 0.3
    commands.recovery_home_timeout_seconds = 0.3
    proxy.set_custom_command_handler(commands)
    await proxy.start()
    return state, gpio, safety, proxy, commands


async def _open_proxy_client(proxy: GrblProxy):
    assert proxy.server is not None
    sock = proxy.server.sockets[0]
    host, port = sock.getsockname()[:2]
    return await asyncio.open_connection(host, port)


async def test_pause_resume_stop_inject_realtime_bytes():
    _, _, proxy = await _proxy()
    try:
        assert proxy.serial is not None
        await proxy.pause()
        await proxy.resume()
        await proxy.stop_job()
        assert REALTIME_PAUSE in proxy.serial.written
        assert REALTIME_RESUME in proxy.serial.written
        assert REALTIME_STOP in proxy.serial.written
    finally:
        await proxy.stop()


async def test_home_and_jog_rejected_if_job_active():
    state, _, proxy = await _proxy()
    try:
        def mutate(snapshot):
            snapshot.lightburn.stream_active = True
            snapshot.machine.state = MachineState.RUN

        await state.update(mutate)
        assert await proxy.home() is False
        assert await proxy.jog("x", 10) is False
    finally:
        await proxy.stop()


async def test_second_tcp_client_is_rejected():
    _, _, proxy = await _proxy()
    try:
        assert proxy.server is not None
        sock = proxy.server.sockets[0]
        host, port = sock.getsockname()[:2]
        reader1, writer1 = await asyncio.open_connection(host, port)
        reader2, writer2 = await asyncio.open_connection(host, port)
        await asyncio.sleep(0.1)
        writer2.write(b"G0 X1\n")
        await writer2.drain()
        assert reader2.at_eof() or writer2.is_closing()
        writer1.close()
        writer2.close()
        await writer1.wait_closed()
        await writer2.wait_closed()
        del reader1
    finally:
        await proxy.stop()


async def test_serial_status_line_processed_once_as_text(monkeypatch):
    state, _, proxy = await _proxy()
    calls = []

    original = grbl_proxy_module.parse_status_line

    def wrapped(line):
        calls.append(line)
        assert isinstance(line, str)
        return original(line)

    monkeypatch.setattr(grbl_proxy_module, "parse_status_line", wrapped)
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        await proxy.serial.inject_rx(b"<Idle|MPos:1.000,2.000,3.000|FS:0,0>\r\n")
        await _wait_for(lambda: len(calls) == 1)
        snapshot = await state.snapshot()
        assert snapshot.machine.state == MachineState.IDLE
        assert calls == ["<Idle|MPos:1.000,2.000,3.000|FS:0,0>"]
    finally:
        await proxy.stop()


async def test_serial_multiple_lines_and_partial_read_are_reconstructed():
    state, _, proxy = await _proxy()
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        await proxy.serial.inject_rx(b"<Run|FS:100,10>\n<Ho")
        await proxy.serial.inject_rx(b"me|FS:0,0>\n")
        await _wait_for_state(state, MachineState.HOME)
        snapshot = await state.snapshot()
        assert snapshot.machine.feed == 0
        assert snapshot.machine.spindle == 0
    finally:
        await proxy.stop()


async def test_serial_bytes_are_forwarded_to_tcp_client():
    _, _, proxy = await _proxy()
    try:
        assert proxy.server is not None
        assert isinstance(proxy.serial, MockSerialEndpoint)
        sock = proxy.server.sockets[0]
        host, port = sock.getsockname()[:2]
        reader, writer = await asyncio.open_connection(host, port)
        await _wait_for(lambda: proxy._client_writer is not None)

        await proxy.serial.inject_rx(b"Grbl 1.1h ['$' for help]\r\nok\r\n")

        assert await reader.readuntil(b"ok\r\n") == b"Grbl 1.1h ['$' for help]\r\nok\r\n"
        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_lightburn_setup_queries_do_not_mark_job_stream_active():
    state, _, proxy = await _proxy()
    try:
        assert proxy.server is not None
        assert isinstance(proxy.serial, MockSerialEndpoint)
        sock = proxy.server.sockets[0]
        host, port = sock.getsockname()[:2]
        _, writer = await asyncio.open_connection(host, port)

        writer.write(b"\x18\n$I\n$G\n$$\n?\n")
        await writer.drain()
        await asyncio.sleep(0.05)

        snapshot = await state.snapshot()
        assert snapshot.lightburn.connected is True
        assert snapshot.lightburn.stream_active is False
        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_laser_off_command_does_not_mark_job_stream_active():
    state, _, proxy = await _proxy()
    try:
        assert proxy.server is not None
        sock = proxy.server.sockets[0]
        host, port = sock.getsockname()[:2]
        _, writer = await asyncio.open_connection(host, port)

        writer.write(b"M5\n")
        await writer.drain()
        await asyncio.sleep(0.05)

        snapshot = await state.snapshot()
        assert snapshot.lightburn.stream_active is False
        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_motion_gcode_marks_job_stream_active():
    state, _, proxy = await _proxy()
    try:
        assert proxy.server is not None
        sock = proxy.server.sockets[0]
        host, port = sock.getsockname()[:2]
        _, writer = await asyncio.open_connection(host, port)

        writer.write(b"G1 X10 Y10 F1000\n")
        await writer.drain()
        await _wait_for_stream_active(state)

        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_homing_sets_homed_only_after_home_to_idle():
    state, _, proxy = await _proxy()
    try:
        assert await proxy.home() is True
        snapshot = await state.snapshot()
        assert snapshot.machine.homed is False
        await proxy.handle_serial_line("<Home|FS:0,0>")
        snapshot = await state.snapshot()
        assert snapshot.machine.homed is False
        await proxy.handle_serial_line("<Idle|FS:0,0>")
        snapshot = await state.snapshot()
        assert snapshot.machine.homed is True
    finally:
        await proxy.stop()


async def test_usb_loss_stops_proxy_and_uses_single_recovery_task():
    state, _, proxy = await _proxy()
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        await proxy.serial.inject_rx(b"")
        await _wait_for(lambda: not proxy.active)
        snapshot = await state.snapshot()
        assert snapshot.machine.laser_usb_connected is False
        assert snapshot.machine.connected_to_grbl is False
        first_task = proxy._recovery_task
        await proxy._handle_serial_loss()
        assert proxy._recovery_task is first_task
    finally:
        await proxy.stop()


async def test_m112_is_intercepted_and_triggers_estop(tmp_path: Path):
    state, gpio, safety, proxy, _ = await _command_proxy(tmp_path)
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        reader, writer = await _open_proxy_client(proxy)

        writer.write(b"M112\n")
        await writer.drain()

        assert await _read_until_custom_response(reader) == b"ok\r\n"
        assert b"M112\n" not in proxy.serial.written
        snapshot = await state.snapshot()
        assert snapshot.safety.software_estop is True
        assert snapshot.machine.state == MachineState.FAULT
        assert snapshot.machine.homed is False
        assert snapshot.physical.k1 is False
        assert gpio.k1 is False
        assert any(event.code.name == "CUSTOM_M112_ESTOP" for event in safety.events)

        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_m113_is_blocked_while_physical_estop_is_active(tmp_path: Path):
    state, gpio, _, proxy, _ = await _command_proxy(tmp_path)
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        gpio.estop_sense = True
        await proxy.safety.refresh_physical_inputs()
        reader, writer = await _open_proxy_client(proxy)

        writer.write(b"M113\n")
        await writer.drain()

        assert await reader.readline() == b"error:112\r\n"
        assert b"M113\n" not in proxy.serial.written
        assert b"$H\n" not in proxy.serial.written
        snapshot = await state.snapshot()
        assert snapshot.physical.estop_sense is True
        assert snapshot.machine.homed is False

        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_m113_recovers_restores_k1_homes_and_acks_after_idle(tmp_path: Path):
    state, gpio, _, proxy, _ = await _command_proxy(tmp_path)
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        await proxy.safety.request_estop(EstopSource.WEB, "test fault")
        reader, writer = await _open_proxy_client(proxy)

        writer.write(b"M113\n")
        await writer.drain()
        await _wait_for(lambda: b"$H\n" in proxy.serial.written)
        assert gpio.k1 is True
        assert (await state.snapshot()).physical.k1 is True

        await proxy.serial.inject_rx(b"<Home|FS:0,0>\n")
        await proxy.serial.inject_rx(b"<Idle|FS:0,0>\n")

        assert await _read_until_custom_response(reader) == b"ok\r\n"
        assert b"M113\n" not in proxy.serial.written
        snapshot = await state.snapshot()
        assert snapshot.safety.software_estop is False
        assert snapshot.machine.homed is True
        assert snapshot.machine.state == MachineState.IDLE
        assert snapshot.lightburn.stream_active is False

        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_m113_reports_failure_if_homing_times_out(tmp_path: Path):
    state, _, _, proxy, _ = await _command_proxy(tmp_path)
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        await proxy.safety.request_estop(EstopSource.WEB, "test fault")
        reader, writer = await _open_proxy_client(proxy)

        writer.write(b"M113\n")
        await writer.drain()

        assert await reader.readline() == b"error:113\r\n"
        snapshot = await state.snapshot()
        assert snapshot.machine.homed is False
        assert snapshot.machine.state == MachineState.RECOVERING

        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_m113_waits_for_grbl_reconnect_before_homing(tmp_path: Path):
    state, _, _, proxy, commands = await _command_proxy(tmp_path)
    try:
        await proxy.stop()
        await state.update(lambda snapshot: setattr(snapshot.lightburn, "stream_active", False))
        await proxy.safety.request_estop(EstopSource.WEB, "test fault")

        recover_task = asyncio.create_task(commands.recover_to_ready())
        await _wait_for(lambda: proxy.serial is not None and b"$H\n" in proxy.serial.written)
        assert proxy.active is True
        assert isinstance(proxy.serial, MockSerialEndpoint)
        await proxy.serial.inject_rx(b"<Home|FS:0,0>\n<Idle|FS:0,0>\n")

        result = await recover_task
        assert result.ok is True
        assert (await state.snapshot()).machine.homed is True
    finally:
        await proxy.stop()


async def test_fragmented_m112_and_multiple_lines_are_intercepted(tmp_path: Path):
    state, _, _, proxy, _ = await _command_proxy(tmp_path)
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        reader, writer = await _open_proxy_client(proxy)

        writer.write(b"G0 X1\nM1")
        await writer.drain()
        writer.write(b"12\n")
        await writer.drain()

        assert await reader.readline() == b"ok\r\n"
        await _wait_for(lambda: b"G0 X1\n" in proxy.serial.written)
        assert b"M112\n" not in proxy.serial.written
        assert (await state.snapshot()).machine.state == MachineState.FAULT

        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def test_normal_gcode_crlf_m1120_comments_and_realtime_forward(tmp_path: Path):
    state, _, _, proxy, _ = await _command_proxy(tmp_path)
    try:
        assert isinstance(proxy.serial, MockSerialEndpoint)
        _, writer = await _open_proxy_client(proxy)

        writer.write(b"G1 X1\r\nM1120\n(contains M112)\n!\n")
        await writer.drain()
        await _wait_for(lambda: REALTIME_PAUSE in proxy.serial.written)

        assert b"G1 X1\r\n" in proxy.serial.written
        assert b"M1120\n" in proxy.serial.written
        assert b"(contains M112)\n" in proxy.serial.written
        assert (await state.snapshot()).machine.state != MachineState.FAULT

        writer.close()
        await writer.wait_closed()
    finally:
        await proxy.stop()


async def _wait_for(predicate, timeout: float = 1.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not met")


async def _read_until_custom_response(reader: asyncio.StreamReader, timeout: float = 1.0) -> bytes:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        line = await asyncio.wait_for(reader.readline(), timeout=deadline - asyncio.get_running_loop().time())
        if line.startswith((b"ok", b"error:")):
            return line
    raise AssertionError("custom command response was not received")


async def _wait_for_stream_active(state: ControllerState, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if (await state.snapshot()).lightburn.stream_active:
            return
        await asyncio.sleep(0.01)
    raise AssertionError("stream did not become active")


async def _wait_for_state(state: ControllerState, expected: MachineState) -> None:
    deadline = asyncio.get_running_loop().time() + 1.0
    while asyncio.get_running_loop().time() < deadline:
        if (await state.snapshot()).machine.state == expected:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"machine state did not become {expected}")
