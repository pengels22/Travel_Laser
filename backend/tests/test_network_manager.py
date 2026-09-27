from backend.network_manager import _parse_interface_status
from backend.network_manager import NetworkManager


def test_parse_interface_status_extracts_ip_and_connection():
    status = _parse_interface_status(
        "wlan0",
        "\n".join(
            [
                "GENERAL.STATE:100 (connected)",
                "GENERAL.CONNECTION:Workshop WiFi",
                "IP4.ADDRESS[1]:192.168.1.42/24",
            ]
        ),
    )

    assert status.interface == "wlan0"
    assert status.connected is True
    assert status.ssid == "Workshop WiFi"
    assert status.ip_address == "192.168.1.42"


def test_parse_interface_status_handles_disconnected_interface():
    status = _parse_interface_status(
        "eth0",
        "\n".join(
            [
                "GENERAL.STATE:30 (disconnected)",
                "GENERAL.CONNECTION:--",
            ]
        ),
    )

    assert status.connected is False
    assert status.ssid is None
    assert status.ip_address is None


async def test_tailscale_status_uses_live_json(monkeypatch):
    manager = NetworkManager()

    async def fake_run(*args: str) -> str:
        assert args == ("tailscale", "status", "--json")
        return '{"BackendState":"Running","Self":{"TailscaleIPs":["100.64.1.2","fd7a::1"]}}'

    monkeypatch.setattr(manager, "_run_command", fake_run)

    status = await manager.tailscale_status()

    assert status.connected is True
    assert status.ip_address == "100.64.1.2"
    assert status.status == "connected"
