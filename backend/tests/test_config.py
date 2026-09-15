from pathlib import Path

from backend.config import config_from_dict, load_config


def test_example_config_captures_deployment_defaults():
    config = load_config(Path("config/controller.example.yaml"))
    assert config.controller.hostname == "Travel-Laser"
    assert config.laser.baud == 115200
    assert config.camera.stream_type == "webrtc"
    assert config.camera.resolution == "highest_available"
    assert config.gpio.power_input.chip == "gpiochip0"
    assert config.gpio.power_input.line == 78
    assert config.gpio.power_input.board_pin == "PC14"
    assert config.gpio.power_input.active_high is True
    assert config.gpio.estop_input.line == 79
    assert config.gpio.estop_input.board_pin == "PC15"
    assert config.gpio.estop_input.active_high is False
    assert config.gpio.k1_output.line == 69
    assert config.gpio.k2_output.line == 72
    assert config.network.ts1_ap_interface == "wlan0"
    assert config.network.ts1_ap_hidden is True
    assert config.network.ts1_ap_ssid == "TS1PE"
    assert config.network.ts1_ap_password == "AsDfGhJkL13579!"
    assert config.network.ts1_ap_always_enabled is True
    assert config.network.ethernet_interface == "eth0"
    assert config.network.ethernet_metric == 100
    assert config.network.uplink_wifi_interface == "wlan1"
    assert config.network.uplink_wifi_metric == 300
    assert config.fire.enabled is False
    assert config.fire.sensor_enabled is False
    assert config.virtualhere.service_name == "virtualhere"
    assert config.virtualhere.backend_controls_service is False


def test_uppercase_fire_sensor_false_parses_false():
    config = config_from_dict({"FIRE_SENSOR": "FALSE"})
    assert config.fire.sensor_enabled is False
