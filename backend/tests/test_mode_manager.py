from pathlib import Path

from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import GrblProxy
from backend.mode_manager import ModeManager
from backend.safety import SafetyController
from backend.state import ControllerState, LaserMode
from backend.virtualhere import VirtualHereService


async def test_network_virtualhere_mode_persists(tmp_path: Path):
    state = ControllerState()
    gpio = MockGPIOBackend()
    safety = SafetyController(state, gpio)
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=0, status_poll_interval=60)
    virtualhere = VirtualHereService()
    manager = ModeManager(state, proxy, virtualhere, tmp_path / "mode.json")

    ok, reason = await manager.switch(LaserMode.VIRTUALHERE)
    assert ok, reason
    assert (tmp_path / "mode.json").read_text()
    restored = await manager.restore()
    assert restored == LaserMode.VIRTUALHERE
    assert virtualhere.active is True
    assert proxy.active is False


async def test_proxy_and_virtualhere_cannot_both_be_active(tmp_path: Path):
    state = ControllerState()
    gpio = MockGPIOBackend()
    safety = SafetyController(state, gpio)
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=0, status_poll_interval=60)
    virtualhere = VirtualHereService()
    manager = ModeManager(state, proxy, virtualhere, tmp_path / "mode.json")
    ok, reason = await manager.switch(LaserMode.NETWORK)
    assert ok, reason
    assert proxy.active is True
    assert virtualhere.active is False
    ok, reason = await manager.switch(LaserMode.VIRTUALHERE)
    assert ok, reason
    assert proxy.active is False
    assert virtualhere.active is True
    await proxy.stop()
    await virtualhere.stop()

