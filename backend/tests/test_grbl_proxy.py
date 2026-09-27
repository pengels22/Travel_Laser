import asyncio

import backend.grbl_proxy as grbl_proxy_module
from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import REALTIME_PAUSE, REALTIME_RESUME, REALTIME_STOP, GrblProxy, MockSerialEndpoint
from backend.safety import SafetyController
from backend.state import ControllerState, MachineState


async def _proxy(port: int = 0):
    state = ControllerState()
    gpio = MockGPIOBackend(power_sense=True)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()
    await safety.refresh_physical_inputs()
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=port, status_poll_interval=60)
    await proxy.start()
    return state, safety, proxy


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


async def _wait_for(predicate, timeout: float = 1.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not met")


async def _wait_for_state(state: ControllerState, expected: MachineState) -> None:
    deadline = asyncio.get_running_loop().time() + 1.0
    while asyncio.get_running_loop().time() < deadline:
        if (await state.snapshot()).machine.state == expected:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"machine state did not become {expected}")
