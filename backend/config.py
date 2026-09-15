from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class USBIdentity:
    vid: str | None = None
    pid: str | None = None
    serial: str | None = None
    description_contains: str | None = None


@dataclass
class LaserConfig:
    tcp_port: int = 23
    baud: int = 115200
    mode: str = "network"
    usb: USBIdentity = field(default_factory=USBIdentity)
    reconnect_timeout_seconds: int = 10
    status_poll_interval_seconds: float = 0.25


@dataclass
class CameraConfig:
    enabled: bool = True
    usb: USBIdentity = field(default_factory=USBIdentity)
    stream_url: str | None = None
    stream_type: str = "webrtc"
    resolution: str = "highest_available"


@dataclass
class DisplayHardwareConfig:
    controller: str = "ST7796U"
    width: int = 480
    height: int = 320
    rotation: int = 90
    spi_device: str | None = None
    spi_speed_hz: int = 24_000_000
    dc_gpio_chip: str | None = None
    dc_gpio_line: int | None = None
    reset_gpio_chip: str | None = None
    reset_gpio_line: int | None = None
    backlight_gpio_chip: str | None = None
    backlight_gpio_line: int | None = None


@dataclass
class TouchHardwareConfig:
    controller: str = "FT6336U"
    i2c_bus: int | None = None
    i2c_address: int = 0x38
    interrupt_gpio_chip: str | None = None
    interrupt_gpio_line: int | None = None
    rotation: int = 90


@dataclass
class GPIOLineConfig:
    chip: str | None = None
    line: int | None = None
    board_pin: str | None = None
    active_high: bool = True
    bias: str = "none"


@dataclass
class GPIOConfig:
    power_input: GPIOLineConfig = field(default_factory=GPIOLineConfig)
    estop_input: GPIOLineConfig = field(default_factory=GPIOLineConfig)
    k1_output: GPIOLineConfig = field(default_factory=GPIOLineConfig)


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class FireConfig:
    enabled: bool = False
    sensor_enabled: bool = False
    active: bool = False
    drop_k1: bool = True
    stop_duration_ms: int = 1000
    auto_reenergize: bool = False
    auto_home: bool = False


@dataclass
class VirtualHereConfig:
    service_name: str = "virtualhere"
    backend_controls_service: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    json_file: str | None = None


@dataclass
class NetworkConfig:
    uplink_wifi_interface: str = "wlan1"
    ethernet_interface: str = "eth0"
    ethernet_metric: int = 100
    uplink_wifi_metric: int = 300
    ethernet_preferred: bool = True


@dataclass
class ControllerConfig:
    hostname: str = "Travel-Laser"


@dataclass
class AppConfig:
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    laser: LaserConfig = field(default_factory=LaserConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    display: DisplayHardwareConfig = field(default_factory=DisplayHardwareConfig)
    touch: TouchHardwareConfig = field(default_factory=TouchHardwareConfig)
    gpio: GPIOConfig = field(default_factory=GPIOConfig)
    web: WebConfig = field(default_factory=WebConfig)
    fire: FireConfig = field(default_factory=FireConfig)
    virtualhere: VirtualHereConfig = field(default_factory=VirtualHereConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    state_dir: Path = Path(".state")


def load_config(path: Path | None = None) -> AppConfig:
    if path is None:
        return AppConfig()
    if not path.exists():
        raise FileNotFoundError(path)
    raw = yaml.safe_load(path.read_text()) or {}
    return config_from_dict(raw)


def config_from_dict(raw: dict[str, Any]) -> AppConfig:
    laser = raw.get("laser", {})
    camera = raw.get("camera", {})
    display = raw.get("display", {})
    touch = raw.get("touch", {})
    gpio = raw.get("gpio", {})
    web = raw.get("web", {})
    fire = raw.get("fire", {})
    virtualhere = raw.get("virtualhere", {})
    network = raw.get("network", {})
    logging = raw.get("logging", {})
    controller = raw.get("controller", {})

    return AppConfig(
        controller=ControllerConfig(hostname=controller.get("hostname", "Travel-Laser")),
        laser=LaserConfig(
            tcp_port=int(laser.get("tcp_port", 23)),
            baud=int(laser.get("baud", 115200)),
            mode=str(laser.get("mode", "network")),
            usb=_usb_identity(laser.get("usb", {})),
            reconnect_timeout_seconds=int(laser.get("reconnect_timeout_seconds", 10)),
            status_poll_interval_seconds=float(laser.get("status_poll_interval_seconds", 0.25)),
        ),
        camera=CameraConfig(
            enabled=bool(camera.get("enabled", True)),
            usb=_usb_identity(camera.get("usb", {})),
            stream_url=camera.get("stream_url"),
            stream_type=str(camera.get("stream_type", "webrtc")),
            resolution=str(camera.get("resolution", "highest_available")),
        ),
        display=DisplayHardwareConfig(
            controller=str(display.get("controller", "ST7796U")),
            width=int(display.get("width", 480)),
            height=int(display.get("height", 320)),
            rotation=int(display.get("rotation", 90)),
            spi_device=display.get("spi_device"),
            spi_speed_hz=int(display.get("spi_speed_hz", 24_000_000)),
            dc_gpio_chip=display.get("dc_gpio_chip"),
            dc_gpio_line=_optional_int(display.get("dc_gpio_line")),
            reset_gpio_chip=display.get("reset_gpio_chip"),
            reset_gpio_line=_optional_int(display.get("reset_gpio_line")),
            backlight_gpio_chip=display.get("backlight_gpio_chip"),
            backlight_gpio_line=_optional_int(display.get("backlight_gpio_line")),
        ),
        touch=TouchHardwareConfig(
            controller=str(touch.get("controller", "FT6336U")),
            i2c_bus=_optional_int(touch.get("i2c_bus")),
            i2c_address=int(str(touch.get("i2c_address", "0x38")), 0),
            interrupt_gpio_chip=touch.get("interrupt_gpio_chip"),
            interrupt_gpio_line=_optional_int(touch.get("interrupt_gpio_line")),
            rotation=int(touch.get("rotation", display.get("rotation", 90))),
        ),
        gpio=GPIOConfig(
            power_input=_gpio_line(gpio.get("power_input", {})),
            estop_input=_gpio_line(gpio.get("estop_input", {})),
            k1_output=_gpio_line(gpio.get("k1_output", {})),
        ),
        web=WebConfig(host=str(web.get("host", "0.0.0.0")), port=int(web.get("port", 8080))),
        fire=FireConfig(
            enabled=_as_bool(fire.get("enabled", False)),
            sensor_enabled=_as_bool(fire.get("sensor_enabled", raw.get("FIRE_SENSOR", False))),
            active=_as_bool(fire.get("active", False)),
            drop_k1=_as_bool(fire.get("drop_k1", True)),
            stop_duration_ms=int(fire.get("stop_duration_ms", 1000)),
            auto_reenergize=_as_bool(fire.get("auto_reenergize", False)),
            auto_home=_as_bool(fire.get("auto_home", False)),
        ),
        virtualhere=VirtualHereConfig(
            service_name=str(virtualhere.get("service_name", "virtualhere")),
            backend_controls_service=_as_bool(virtualhere.get("backend_controls_service", False)),
        ),
        network=NetworkConfig(
            uplink_wifi_interface=str(network.get("uplink_wifi", {}).get("interface", "wlan1")),
            ethernet_interface=str(network.get("ethernet", {}).get("interface", "eth0")),
            ethernet_metric=int(network.get("ethernet", {}).get("metric", 100)),
            uplink_wifi_metric=int(network.get("uplink_wifi", {}).get("metric", 300)),
            ethernet_preferred=_as_bool(network.get("ethernet_preferred", True)),
        ),
        logging=LoggingConfig(level=str(logging.get("level", "INFO")), json_file=logging.get("json_file")),
    )


def _usb_identity(raw: dict[str, Any]) -> USBIdentity:
    return USBIdentity(
        vid=raw.get("vid"),
        pid=raw.get("pid"),
        serial=raw.get("serial"),
        description_contains=raw.get("description_contains"),
    )


def _gpio_line(raw: dict[str, Any]) -> GPIOLineConfig:
    line = raw.get("line")
    return GPIOLineConfig(
        chip=raw.get("chip"),
        line=None if line is None else int(line),
        board_pin=raw.get("board_pin"),
        active_high=_as_bool(raw.get("active_high", True)),
        bias=str(raw.get("bias", "none")),
    )


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(str(value), 0)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
