#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


CONFIG_MAP = {
    "TRAVEL_LASER_TAILSCALE_IP": ("network", "tailscale", "ip_address"),
    "LASER_USB_VID": ("laser", "usb", "vid"),
    "LASER_USB_PID": ("laser", "usb", "pid"),
    "LASER_USB_SERIAL": ("laser", "usb", "serial"),
    "LASER_USB_DESCRIPTION": ("laser", "usb", "description_contains"),
    "CAMERA_USB_VID": ("camera", "usb", "vid"),
    "CAMERA_USB_PID": ("camera", "usb", "pid"),
    "CAMERA_USB_SERIAL": ("camera", "usb", "serial"),
    "CAMERA_USB_DESCRIPTION": ("camera", "usb", "description_contains"),
    "CAMERA_STREAM_URL": ("camera", "stream_url"),
    "DISPLAY_SPI_DEVICE": ("display", "spi_device"),
    "TOUCH_I2C_BUS": ("touch", "i2c_bus"),
    "BACKLIGHT_GPIO_CHIP": ("display", "backlight_gpio_chip"),
    "BACKLIGHT_GPIO_LINE": ("display", "backlight_gpio_line"),
    "VIRTUALHERE_SERVICE_NAME": ("virtualhere", "service_name"),
    "VIRTUALHERE_BACKEND_CONTROLS_SERVICE": ("virtualhere", "backend_controls_service"),
}

REQUIRED_ITEMS = (
    (
        "Tailscale IP",
        ("TRAVEL_LASER_TAILSCALE_IP",),
        "auto-filled by deploy when `tailscale ip -4` works; otherwise run Tailscale setup first",
    ),
    (
        "Camera device",
        ("CAMERA_DEVICE",),
        "auto-filled only when exactly one `/dev/v4l/by-id/*` camera is present; otherwise choose manually",
    ),
    (
        "Laser USB identity",
        ("LASER_USB_VID", "LASER_USB_PID", "LASER_USB_SERIAL", "LASER_USB_DESCRIPTION"),
        "auto-filled only when exactly one serial USB device is present; otherwise choose the laser controller manually",
    ),
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Travel-Laser deployment placeholders")
    parser.add_argument("--env", type=Path, default=Path("/etc/travel-laser/deployment.env"))
    parser.add_argument("--config", type=Path, default=Path("/etc/travel-laser/controller.yaml"))
    parser.add_argument("--check", action="store_true", help="validate only; do not write config")
    args = parser.parse_args()

    values = read_env(args.env)
    missing = [
        (label, keys, hint)
        for label, keys, hint in REQUIRED_ITEMS
        if not any(values.get(key) for key in keys)
    ]
    if missing:
        print("Missing deployment values:")
        for label, keys, hint in missing:
            print(f"  - {label}: {', '.join(keys)}")
            print(f"    {hint}")
        raise SystemExit(2)

    config = yaml.safe_load(args.config.read_text()) or {}
    for env_key, path in CONFIG_MAP.items():
        value = values.get(env_key)
        if value in (None, ""):
            continue
        set_nested(config, path, coerce_value(value))

    if not args.check:
        args.config.write_text(yaml.safe_dump(config, sort_keys=False))
    print(f"{'Checked' if args.check else 'Updated'} {args.config} from {args.env}")


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def set_nested(config: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    target = config
    for key in path[:-1]:
        child = target.get(key)
        if not isinstance(child, dict):
            child = {}
            target[key] = child
        target = child
    target[path[-1]] = value


def coerce_value(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered.isdigit():
        return int(lowered)
    return value


if __name__ == "__main__":
    main()
