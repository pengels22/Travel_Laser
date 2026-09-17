from pathlib import Path

from backend.command_service import ControllerCommandService
from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import GrblProxy
from backend.mode_manager import ModeManager
from backend.network_manager import NetworkManager
from backend.safety import EstopSource, SafetyController
from backend.state import ControllerState, LaserMode, MachineState
from backend.virtualhere import VirtualHereService


async def _service(tmp_path: Path):
    state = ControllerState()
    gpio = MockGPIOBackend(power_sense=True)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()
    await safety.refresh_physical_inputs()
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=0, status_poll_interval=60)
    await proxy.start()
    virtualhere = VirtualHereService()
    manager = ModeManager(state, proxy, virtualhere, tmp_path / "mode.json")
    commands = ControllerCommandService(state, safety, proxy, manager, NetworkManager(dry_run=True))
    return state, gpio, proxy, commands


async def test_home_routes_through_proxy_and_blocks_active_stream(tmp_path: Path):
    state, _, proxy, commands = await _service(tmp_path)
    try:
        result = await commands.home()
        assert result.ok is True
        assert b"$H\n" in proxy.serial.written

        await state.update(lambda snapshot: setattr(snapshot.lightburn, "stream_active", True))
        result = await commands.home()
        assert result.ok is False
        assert result.code == "MACHINE_BUSY"
    finally:
        await proxy.stop()


async def test_estop_is_always_routed_to_safety(tmp_path: Path):
    state, gpio, proxy, commands = await _service(tmp_path)
    try:
        result = await commands.estop(EstopSource.LOCAL_UI)
        assert result.ok is True
        assert gpio.k1 is False
        assert (await state.snapshot()).machine.homed is False
    finally:
        await proxy.stop()


async def test_mode_change_rejects_fault(tmp_path: Path):
    state, _, proxy, commands = await _service(tmp_path)
    try:
        await state.update(lambda snapshot: setattr(snapshot.machine, "state", MachineState.FAULT))
        result = await commands.mode_change(LaserMode.VIRTUALHERE.value)
        assert result.ok is False
        assert result.code == "MODE_CHANGE_BLOCKED"
    finally:
        await proxy.stop()


async def test_wifi_scan_returns_structured_result(tmp_path: Path):
    _, _, proxy, commands = await _service(tmp_path)
    try:
        result = await commands.network_scan()
        assert result.ok is True
        assert result.data == {"networks": []}
    finally:
        await proxy.stop()
