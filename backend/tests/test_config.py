from pathlib import Path

from backend.config import config_from_dict, load_config


def test_example_config_captures_deployment_defaults():
    config = load_config(Path("config/controller.example.yaml"))
    assert config.controller.hostname == "Travel-Laser"
    assert config.laser.tcp_port == 23
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
    assert config.gpio.k1_output.line == 72
    assert config.gpio.k1_output.board_pin == "PC8"
    assert config.display.controller == "ST7796U"
    assert config.display.width == 480
    assert config.display.height == 320
    assert config.display.spi_device == "/dev/spidev1.0"
    assert config.display.dc_gpio_line == 70
    assert config.display.reset_gpio_line == 73
    assert config.touch.controller == "FT6336U"
    assert config.touch.i2c_address == 0x38
    assert config.touch.i2c_bus == 3
    assert config.touch.reset_gpio_line == 69
    assert config.touch.interrupt_gpio_line == 75
    assert config.network.ethernet_interface == "eth0"
    assert config.network.ethernet_metric == 100
    assert config.network.uplink_wifi_interface == "wlan1"
    assert config.network.uplink_wifi_metric == 300
    assert config.fire.enabled is False
    assert config.fire.sensor_enabled is False
    assert config.fire.drop_k1 is True
    assert config.virtualhere.service_name == "virtualhere"
    assert config.virtualhere.backend_controls_service is False


def test_uppercase_fire_sensor_false_parses_false():
    config = config_from_dict({"FIRE_SENSOR": "FALSE"})
    assert config.fire.sensor_enabled is False


def test_example_config_has_no_gpio_line_overlaps():
    config = load_config(Path("config/controller.example.yaml"))
    assigned = {
        "power_input": (config.gpio.power_input.chip, config.gpio.power_input.line),
        "estop_input": (config.gpio.estop_input.chip, config.gpio.estop_input.line),
        "k1_output": (config.gpio.k1_output.chip, config.gpio.k1_output.line),
        "display_dc": (config.display.dc_gpio_chip, config.display.dc_gpio_line),
        "display_reset": (config.display.reset_gpio_chip, config.display.reset_gpio_line),
        "display_backlight": (config.display.backlight_gpio_chip, config.display.backlight_gpio_line),
        "touch_reset": (config.touch.reset_gpio_chip, config.touch.reset_gpio_line),
        "touch_interrupt": (config.touch.interrupt_gpio_chip, config.touch.interrupt_gpio_line),
    }
    seen: dict[tuple[str, int], str] = {}
    for name, key in assigned.items():
        chip, line = key
        if chip is None or line is None:
            continue
        assert key not in seen, f"{name} overlaps {seen[key]} on {chip}:{line}"
        seen[key] = name
