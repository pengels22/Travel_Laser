from pathlib import Path

from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import GrblProxy
from backend.mode_manager import ModeManager
from backend.safety import SafetyController
from backend.state import ControllerState
from backend.virtualhere import VirtualHereService
from backend.websocket_api import WebSocketAPI


async def test_ts1_hello_and_estop_ack(tmp_path: Path):
    state = ControllerState()
    gpio = MockGPIOBackend(power_switch=True)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()
    await safety.refresh_physical_inputs()
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=0, status_poll_interval=60)
    virtualhere = VirtualHereService()
    mode_manager = ModeManager(state, proxy, virtualhere, tmp_path / "mode.json")
    api = WebSocketAPI(state, safety, proxy, mode_manager, "127.0.0.1", 0, "secret")

    hello = await api.handle_packet({"type": "hello", "device": "ts1", "protocol": 1, "token": "secret"})
    assert hello == {"type": "hello", "device": "laserpi", "protocol": 1}

    ack = await api.handle_packet({"type": "stop", "id": 3, "action": "estop"})
    assert ack == {"type": "ack", "id": 3, "ok": True}
    snapshot = await state.snapshot()
    assert snapshot.physical.k2 is False

