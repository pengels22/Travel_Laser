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


@dataclass
class WebSocketConfig:
    host: str = "10.42.0.1"
    port: int = 8765
    path: str = "/ws"
    shared_token: str = "CHANGE_ME"


@dataclass
class WebConfig:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class FireConfig:
    enabled: bool = False
    sensor_enabled: bool = False
    active: bool = False
    drop_k2: bool = True
    stop_duration_ms: int = 1000
    auto_reenergize: bool = False
    auto_home: bool = False


@dataclass
class LoggingConfig:
    level: str = "INFO"
    json_file: str | None = None


@dataclass
class NetworkConfig:
    ts1_ap_interface: str = "wlan0"
    ts1_ap_hidden: bool = True
    ts1_ap_ssid: str = "TS1PE"
    ts1_ap_password: str = "AsDfGhJkL13579!"
    ts1_ap_always_enabled: bool = True
    ethernet_preferred: bool = True


@dataclass
class ControllerConfig:
    hostname: str = "laserpi"


@dataclass
class AppConfig:
    controller: ControllerConfig = field(default_factory=ControllerConfig)
    laser: LaserConfig = field(default_factory=LaserConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    web: WebConfig = field(default_factory=WebConfig)
    fire: FireConfig = field(default_factory=FireConfig)
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
    websocket = raw.get("websocket", {})
    web = raw.get("web", {})
    fire = raw.get("fire", {})
    network = raw.get("network", {})
    private_ts1_ap = network.get("private_ts1_ap", {})
    logging = raw.get("logging", {})
    controller = raw.get("controller", {})

    return AppConfig(
        controller=ControllerConfig(hostname=controller.get("hostname", "laserpi")),
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
        ),
        websocket=WebSocketConfig(
            host=str(websocket.get("host", "10.42.0.1")),
            port=int(websocket.get("port", 8765)),
            path=str(websocket.get("path", "/ws")),
            shared_token=str(websocket.get("shared_token", "CHANGE_ME")),
        ),
        web=WebConfig(host=str(web.get("host", "0.0.0.0")), port=int(web.get("port", 8080))),
        fire=FireConfig(
            enabled=_as_bool(fire.get("enabled", False)),
            sensor_enabled=_as_bool(fire.get("sensor_enabled", raw.get("FIRE_SENSOR", False))),
            active=_as_bool(fire.get("active", False)),
            drop_k2=_as_bool(fire.get("drop_k2", True)),
            stop_duration_ms=int(fire.get("stop_duration_ms", 1000)),
            auto_reenergize=_as_bool(fire.get("auto_reenergize", False)),
            auto_home=_as_bool(fire.get("auto_home", False)),
        ),
        network=NetworkConfig(
            ts1_ap_interface=str(private_ts1_ap.get("interface", "wlan0")),
            ts1_ap_hidden=_as_bool(private_ts1_ap.get("hidden", True)),
            ts1_ap_ssid=str(private_ts1_ap.get("ssid", "TS1PE")),
            ts1_ap_password=str(private_ts1_ap.get("password", "AsDfGhJkL13579!")),
            ts1_ap_always_enabled=_as_bool(private_ts1_ap.get("always_enabled", True)),
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


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
