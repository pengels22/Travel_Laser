from backend.gpio import MockGPIOBackend
from backend.safety import EstopSource, SafetyController
from backend.state import ControllerState


async def _safety(power_switch: bool = True):
    state = ControllerState()
    gpio = MockGPIOBackend(power_switch=power_switch)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()
    await safety.refresh_physical_inputs()
    return state, gpio, safety


async def test_physical_estop_causes_k2_off():
    state, gpio, safety = await _safety()
    assert gpio.k2 is True
    gpio.estop_switch = True
    await safety.refresh_physical_inputs()
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is False


async def test_ts1_estop_causes_k2_off():
    state, _, safety = await _safety()
    await safety.request_estop(EstopSource.TS1)
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is False
    assert snapshot.machine.homed is False


async def test_web_estop_causes_k2_off():
    state, _, safety = await _safety()
    await safety.request_estop(EstopSource.WEB)
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is False


async def test_fire_does_nothing_when_disabled():
    state, _, safety = await _safety()

    def mutate(snapshot):
        snapshot.safety.fire_enabled = False
        snapshot.safety.fire_active = True

    await state.update(mutate)
    await safety.evaluate_outputs()
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is True


async def test_lightburn_disconnect_idle_does_not_estop():
    state, _, safety = await _safety()

    def mutate(snapshot):
        snapshot.lightburn.connected = True
        snapshot.lightburn.stream_active = False

    await state.update(mutate)
    await safety.handle_lightburn_disconnect()
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is True


async def test_lightburn_disconnect_active_stream_drops_k2():
    state, _, safety = await _safety()

    def mutate(snapshot):
        snapshot.lightburn.connected = True
        snapshot.lightburn.stream_active = True

    await state.update(mutate)
    await safety.handle_lightburn_disconnect()
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is False


async def test_laser_usb_disappearance_while_k2_on_drops_k2():
    state, _, safety = await _safety()
    await safety.handle_laser_usb_disconnected()
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is False


async def test_laser_usb_disappearance_while_k2_off_is_expected():
    state, _, safety = await _safety()
    await safety.set_k2(False)
    await safety.handle_laser_usb_disconnected()
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is False
    assert snapshot.safety.software_estop is False


async def test_camera_disconnect_does_not_affect_relays():
    state, _, safety = await _safety()
    before = await state.snapshot()
    await safety.handle_camera_disconnected()
    after = await state.snapshot()
    assert after.physical.k1 == before.physical.k1
    assert after.physical.k2 == before.physical.k2


async def test_ts1_disconnect_does_not_affect_relays():
    state, _, safety = await _safety()
    before = await state.snapshot()
    await safety.handle_ts1_disconnected()
    after = await state.snapshot()
    assert after.physical.k1 == before.physical.k1
    assert after.physical.k2 == before.physical.k2

