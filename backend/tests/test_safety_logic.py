from backend.gpio import MockGPIOBackend
from backend.safety import EstopSource, SafetyController
from backend.state import ControllerState


async def _safety(power_sense: bool = True):
    state = ControllerState()
    gpio = MockGPIOBackend(power_sense=power_sense)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()
    await safety.refresh_physical_inputs()
    return state, gpio, safety


async def test_physical_estop_causes_k1_off():
    state, gpio, safety = await _safety()
    assert gpio.k1 is True
    gpio.estop_sense = True
    await safety.refresh_physical_inputs()
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False


async def test_local_ui_estop_causes_k1_off():
    state, _, safety = await _safety()
    await safety.request_estop(EstopSource.LOCAL_UI)
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False
    assert snapshot.machine.homed is False


async def test_web_estop_causes_k1_off():
    state, _, safety = await _safety()
    await safety.request_estop(EstopSource.WEB)
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False


async def test_software_estop_requires_physical_estop_cycle_to_clear():
    state, gpio, safety = await _safety()
    await safety.request_estop(EstopSource.WEB)
    await safety.refresh_physical_inputs()
    snapshot = await state.snapshot()
    assert snapshot.safety.software_estop is True
    assert snapshot.physical.k1 is False

    gpio.estop_sense = True
    await safety.refresh_physical_inputs()
    snapshot = await state.snapshot()
    assert snapshot.safety.software_estop is True
    assert snapshot.physical.k1 is False

    gpio.estop_sense = False
    await safety.refresh_physical_inputs()
    snapshot = await state.snapshot()
    assert snapshot.safety.software_estop is False
    assert snapshot.physical.k1 is True


async def test_fire_does_nothing_when_disabled():
    state, _, safety = await _safety()

    def mutate(snapshot):
        snapshot.safety.fire_enabled = False
        snapshot.safety.fire_active = True

    await state.update(mutate)
    await safety.evaluate_outputs()
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is True


async def test_fire_drops_k1_when_enabled():
    state, _, safety = await _safety()

    def mutate(snapshot):
        snapshot.safety.fire_enabled = True
        snapshot.safety.fire_active = True

    await state.update(mutate)
    await safety.evaluate_outputs()
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False


async def test_fire_estop_request_is_blocked_when_fire_sensor_disabled():
    state, _, safety = await _safety()
    await safety.request_estop(EstopSource.FIRE)
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is True
    assert snapshot.safety.fire_active is False


async def test_k1_drops_during_non_fire_estop():
    state, _, safety = await _safety()
    await safety.request_estop(EstopSource.WEB)
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False


async def test_lightburn_disconnect_idle_does_not_estop():
    state, _, safety = await _safety()

    def mutate(snapshot):
        snapshot.lightburn.connected = True
        snapshot.lightburn.stream_active = False

    await state.update(mutate)
    await safety.handle_lightburn_disconnect()
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is True


async def test_lightburn_disconnect_active_stream_drops_k1():
    state, _, safety = await _safety()

    def mutate(snapshot):
        snapshot.lightburn.connected = True
        snapshot.lightburn.stream_active = True

    await state.update(mutate)
    await safety.handle_lightburn_disconnect()
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False


async def test_laser_usb_disappearance_while_k1_on_drops_k1():
    state, _, safety = await _safety()
    await safety.handle_laser_usb_disconnected()
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False


async def test_laser_usb_disappearance_while_k1_off_is_expected():
    state, _, safety = await _safety()
    await safety.set_k1(False)
    await safety.handle_laser_usb_disconnected()
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False
    assert snapshot.safety.software_estop is False


async def test_camera_disconnect_does_not_affect_relays():
    state, _, safety = await _safety()
    before = await state.snapshot()
    await safety.handle_camera_disconnected()
    after = await state.snapshot()
    assert after.physical.k1 == before.physical.k1
