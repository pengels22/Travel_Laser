from pathlib import Path

from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import GrblProxy
from backend.mode_manager import ModeManager
from backend.network_manager import NetworkManager
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
    network_manager = NetworkManager("wlan1", dry_run=True)
    api = WebSocketAPI(state, safety, proxy, mode_manager, network_manager, "127.0.0.1", 0, "secret")

    hello = await api.handle_packet({"type": "hello", "device": "ts1", "protocol": 1, "token": "secret"})
    assert hello == {"type": "hello", "device": "laserpi", "protocol": 1}

    ack = await api.handle_packet({"type": "stop", "id": 3, "action": "estop"})
    assert ack == {"type": "ack", "id": 3, "ok": True}
    snapshot = await state.snapshot()
    assert snapshot.physical.k1 is False


async def test_ts1_wifi_settings_apply_to_wlan1(tmp_path: Path):
    state = ControllerState()
    gpio = MockGPIOBackend(power_switch=True)
    safety = SafetyController(state, gpio)
    proxy = GrblProxy(state, safety, host="127.0.0.1", port=0, status_poll_interval=60)
    virtualhere = VirtualHereService()
    mode_manager = ModeManager(state, proxy, virtualhere, tmp_path / "mode.json")
    network_manager = NetworkManager("wlan1", dry_run=True)
    api = WebSocketAPI(state, safety, proxy, mode_manager, network_manager, "127.0.0.1", 0, "secret")

    scan = await api.handle_packet({"type": "settings", "id": 1, "action": "wifi_scan"})
    connect = await api.handle_packet(
        {"type": "settings", "id": 2, "action": "wifi_connect", "ssid": "ShopWiFi", "password": "secret"}
    )
    forget = await api.handle_packet({"type": "settings", "id": 3, "action": "wifi_forget", "ssid": "ShopWiFi"})

    assert scan == {"type": "ack", "id": 1, "ok": True, "networks": [], "interface": "wlan1"}
    assert connect == {"type": "ack", "id": 2, "ok": True}
    assert forget == {"type": "ack", "id": 3, "ok": True}
    assert network_manager.actions == [
        ("scan", "wlan1", None),
        ("connect", "wlan1", "ShopWiFi"),
        ("forget", "wlan1", "ShopWiFi"),
    ]
