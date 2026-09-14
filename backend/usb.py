from __future__ import annotations

import asyncio
from dataclasses import dataclass

from .config import USBIdentity


@dataclass(frozen=True)
class USBDevice:
    path: str
    vid: str | None = None
    pid: str | None = None
    serial: str | None = None
    description: str | None = None


class USBDeviceManager:
    def __init__(self, laser_identity: USBIdentity, camera_identity: USBIdentity) -> None:
        self.laser_identity = laser_identity
        self.camera_identity = camera_identity
        self._laser: USBDevice | None = None
        self._camera: USBDevice | None = None

    def set_mock_laser(self, device: USBDevice | None) -> None:
        self._laser = device

    def set_mock_camera(self, device: USBDevice | None) -> None:
        self._camera = device

    async def wait_for_laser(self, timeout: float | None = None) -> USBDevice | None:
        return await self._wait(lambda: self._laser, timeout)

    async def wait_for_camera(self, timeout: float | None = None) -> USBDevice | None:
        return await self._wait(lambda: self._camera, timeout)

    def current_laser_device(self) -> USBDevice | None:
        return self._laser

    def current_camera_device(self) -> USBDevice | None:
        return self._camera

    async def watch(self):
        while True:
            await asyncio.sleep(1)

    async def _wait(self, getter, timeout: float | None) -> USBDevice | None:
        deadline = None if timeout is None else asyncio.get_running_loop().time() + timeout
        while True:
            device = getter()
            if device:
                return device
            if deadline is not None and asyncio.get_running_loop().time() >= deadline:
                return None
            await asyncio.sleep(0.1)


def matches_identity(device: USBDevice, identity: USBIdentity) -> bool:
    checks: list[bool] = []
    if identity.vid:
        checks.append((device.vid or "").lower() == identity.vid.lower())
    if identity.pid:
        checks.append((device.pid or "").lower() == identity.pid.lower())
    if identity.serial:
        checks.append(device.serial == identity.serial)
    if identity.description_contains:
        checks.append(identity.description_contains.lower() in (device.description or "").lower())
    return all(checks) if checks else True

