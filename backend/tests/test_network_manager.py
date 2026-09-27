from backend.network_manager import _parse_interface_status, _parse_iw_scan
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


def test_parse_iw_scan_extracts_visible_networks():
    networks = _parse_iw_scan(
        "\n".join(
            [
                "BSS b4:18:d1:e1:d5:16(on wlan0) -- associated",
                "\tsignal: -65.00 dBm",
                "\tSSID: Lab 42",
                "\tRSN:",
                "\t * Version: 1",
                "BSS 8c:0f:6f:0e:04:e0(on wlan0)",
                "\tsignal: -69.00 dBm",
                "\tSSID: Chat",
                "\tcapability: ESS Privacy ShortSlotTime (0x0411)",
                "\tWPA:",
                "BSS 00:11:22:33:44:55(on wlan0)",
                "\tsignal: -80.00 dBm",
                "\tSSID: Guest",
            ]
        )
    )

    assert [network.ssid for network in networks] == ["Lab 42", "Chat", "Guest"]
    assert networks[0].connected is True
    assert networks[0].security == "WPA/WPA2"
    assert networks[2].security == "open"


async def test_scan_wifi_falls_back_to_iw_scan():
    manager = NetworkManager()
    calls = []

    async def fake_run(*args: str) -> str:
        calls.append(args)
        if args[0] == "nmcli":
            return ""
        assert args == ("/usr/sbin/iw", "dev", "wlan0", "scan")
        return "\n".join(["BSS b4:18:d1:e1:d5:16(on wlan0)", "\tsignal: -65.00 dBm", "\tSSID: Lab 42", "\tRSN:"])

    manager._run_command = fake_run

    networks = await manager.scan_wifi()

    assert calls[0][:4] == ("nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY")
    assert networks[0].ssid == "Lab 42"
