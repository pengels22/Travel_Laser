from __future__ import annotations

import asyncio
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .camera import CameraAdapter
from .config import AppConfig
from .gpio import GPIOBackend
from .network_manager import NetworkManager
from .state import ControllerState
from .usb import USBDevice, enumerate_usb_devices, matches_identity
from .virtualhere import VirtualHereService


@dataclass(frozen=True)
class ServiceStatus:
    name: str
    active: bool
    status: str


class DiagnosticsProvider:
    def __init__(
        self,
        config: AppConfig,
        state: ControllerState,
        gpio: GPIOBackend,
        network: NetworkManager,
        camera: CameraAdapter,
        virtualhere: VirtualHereService,
        device_provider=enumerate_usb_devices,
    ) -> None:
        self.config = config
        self.state = state
        self.gpio = gpio
        self.network = network
        self.camera = camera
        self.virtualhere = virtualhere
        self.device_provider = device_provider

    async def collect(self) -> dict[str, Any]:
        snapshot = await self.state.snapshot()
        devices = await asyncio.to_thread(self.device_provider)
        laser = _single_match(devices, self.config.laser.usb)
        camera = _single_match(devices, self.config.camera.usb) if self.config.camera.enabled else None
        services = await self._service_statuses()
        ethernet = await self.network.interface_status(self.config.network.ethernet_interface)
        wifi = await self.network.interface_status(self.config.network.uplink_wifi_interface)
        tailscale = await self.network.tailscale_status(self.config.network.tailscale_interface)
        gpio_initialized = bool(getattr(self.gpio, "_requests", None)) or self.gpio.__class__.__name__ == "MockGPIOBackend"

        return {
            "gpio_status": "initialized" if gpio_initialized else "not initialized",
            "gpio": {
                "chip": self.config.gpio.k1_output.chip,
                "power_line": self.config.gpio.power_input.line,
                "estop_line": self.config.gpio.estop_input.line,
                "k1_line": self.config.gpio.k1_output.line,
                "power_sense": snapshot.physical.power_sense,
                "estop_sense": snapshot.physical.estop_sense,
                "k1": snapshot.physical.k1,
            },
            "spi_device": self.config.display.spi_device,
            "spi_status": _path_status(self.config.display.spi_device),
            "display_status": "configured" if self.config.display.spi_device else "not configured",
            "i2c_bus": self.config.touch.i2c_bus,
            "i2c_address": self.config.touch.i2c_address,
            "i2c_status": _path_status(f"/dev/i2c-{self.config.touch.i2c_bus}") if self.config.touch.i2c_bus is not None else "not configured",
            "touch_status": "configured" if self.config.touch.i2c_bus is not None else "not configured",
            "usb_devices": [asdict(device) for device in devices],
            "laser_usb": asdict(laser) if laser else None,
            "camera_usb": asdict(camera) if camera else None,
            "services": [asdict(service) for service in services],
            "network": {
                "ethernet": asdict(ethernet),
                "wifi": asdict(wifi),
                "tailscale": asdict(tailscale),
            },
        }

    async def apply(self) -> None:
        diagnostics = await self.collect()

        def mutate(snapshot):
            snapshot.diagnostics.gpio_status = diagnostics["gpio_status"]
            snapshot.diagnostics.spi_device = diagnostics["spi_device"]
            snapshot.diagnostics.spi_status = diagnostics["spi_status"]
            snapshot.diagnostics.i2c_bus = diagnostics["i2c_bus"]
            snapshot.diagnostics.i2c_address = diagnostics["i2c_address"]
            snapshot.diagnostics.i2c_status = diagnostics["i2c_status"]
            snapshot.diagnostics.display_status = diagnostics["display_status"]
            snapshot.diagnostics.touch_status = diagnostics["touch_status"]
            snapshot.diagnostics.usb_devices = diagnostics["usb_devices"]
            snapshot.diagnostics.gpio = diagnostics["gpio"]
            snapshot.diagnostics.laser_usb = diagnostics["laser_usb"]
            snapshot.diagnostics.camera_usb = diagnostics["camera_usb"]
            snapshot.diagnostics.services = diagnostics["services"]
            snapshot.diagnostics.network = diagnostics["network"]

        await self.state.update(mutate)

    async def _service_statuses(self) -> list[ServiceStatus]:
        names = [
            "travel-laser-controller.service",
            "travel-laser-ui.service",
            "travel-laser-camera.service",
            "mediamtx.service",
            "tailscaled.service",
        ]
        if self.config.virtualhere.service_name:
            names.append(self.config.virtualhere.service_name)
        return await asyncio.gather(*(_service_status(name) for name in names))


async def _service_status(name: str) -> ServiceStatus:
    try:
        process = await asyncio.create_subprocess_exec(
            "systemctl",
            "is-active",
            name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
    except OSError as exc:
        return ServiceStatus(name, False, str(exc))
    status = stdout.decode().strip() or stderr.decode().strip() or "unknown"
    return ServiceStatus(name, process.returncode == 0 and status == "active", status)


def _path_status(path: str | None) -> str:
    if not path:
        return "not configured"
    candidate = Path(path)
    if not candidate.exists():
        return "missing"
    if os.access(candidate, os.R_OK | os.W_OK):
        return "accessible"
    if os.access(candidate, os.R_OK):
        return "read-only"
    return "present but inaccessible"


def _single_match(devices: list[USBDevice], identity) -> USBDevice | None:
    matches = [device for device in devices if matches_identity(device, identity)]
    return matches[0] if len(matches) == 1 else None
