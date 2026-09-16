import asyncio

from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import REALTIME_PAUSE, REALTIME_RESUME, REALTIME_STOP, GrblProxy
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
