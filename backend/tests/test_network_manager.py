from backend.network_manager import _parse_interface_status


def test_parse_interface_status_extracts_ip_and_connection():
    status = _parse_interface_status(
        "wlan1",
        "\n".join(
            [
                "GENERAL.STATE:100 (connected)",
                "GENERAL.CONNECTION:Workshop WiFi",
                "IP4.ADDRESS[1]:192.168.1.42/24",
            ]
        ),
    )

    assert status.interface == "wlan1"
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
