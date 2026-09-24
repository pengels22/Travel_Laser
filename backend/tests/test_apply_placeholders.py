from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


SCRIPT = Path("scripts/apply-placeholders.py")


def test_apply_placeholders_updates_controller_config(tmp_path: Path) -> None:
    env_path = tmp_path / "deployment.env"
    config_path = tmp_path / "controller.yaml"
    env_path.write_text(
        "\n".join(
            (
                "TRAVEL_LASER_TAILSCALE_IP=100.64.12.34",
                "LASER_USB_DESCRIPTION=CH340",
                "CAMERA_DEVICE=/dev/v4l/by-id/test-camera",
                "CAMERA_STREAM_URL=http://travel-laser:8889/cam",
                "DISPLAY_SPI_DEVICE=/dev/spidev1.1",
                "TOUCH_I2C_BUS=2",
                "VIRTUALHERE_BACKEND_CONTROLS_SERVICE=false",
            )
        )
    )
    config_path.write_text(
        yaml.safe_dump(
            {
                "network": {"tailscale": {"ip_address": None}},
                "laser": {"usb": {"description_contains": None}},
                "camera": {"stream_url": None},
                "display": {"spi_device": None},
                "touch": {"i2c_bus": None},
                "virtualhere": {"backend_controls_service": True},
            },
            sort_keys=False,
        )
    )

    subprocess.run(
        [sys.executable, str(SCRIPT), "--env", str(env_path), "--config", str(config_path)],
        check=True,
    )

    config = yaml.safe_load(config_path.read_text())
    assert config["network"]["tailscale"]["ip_address"] == "100.64.12.34"
    assert config["laser"]["usb"]["description_contains"] == "CH340"
    assert config["camera"]["stream_url"] == "http://travel-laser:8889/cam"
    assert config["display"]["spi_device"] == "/dev/spidev1.1"
    assert config["touch"]["i2c_bus"] == 2
    assert config["virtualhere"]["backend_controls_service"] is False


def test_apply_placeholders_blocks_missing_required_values(tmp_path: Path) -> None:
    env_path = tmp_path / "deployment.env"
    config_path = tmp_path / "controller.yaml"
    env_path.write_text("TRAVEL_LASER_TAILSCALE_IP=\nCAMERA_DEVICE=\n")
    config_path.write_text("{}\n")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--env", str(env_path), "--config", str(config_path)],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 2
    assert "Missing deployment values" in result.stdout
    assert "Tailscale IP" in result.stdout
    assert "TRAVEL_LASER_TAILSCALE_IP" in result.stdout
    assert "Camera device" in result.stdout
    assert "CAMERA_DEVICE" in result.stdout
    assert "Laser USB identity" in result.stdout
