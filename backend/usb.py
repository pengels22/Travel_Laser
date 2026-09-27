from __future__ import annotations

import asyncio
from dataclasses import dataclass
from collections.abc import Callable

from .config import USBIdentity


@dataclass(frozen=True)
class USBDevice:
    path: str
    vid: str | None = None
    pid: str | None = None
    serial: str | None = None
    description: str | None = None


class USBDeviceManager:
    def __init__(
        self,
        laser_identity: USBIdentity,
        camera_identity: USBIdentity,
        device_provider: Callable[[], list[USBDevice]] | None = None,
        poll_interval: float = 1.0,
    ) -> None:
        self.laser_identity = laser_identity
        self.camera_identity = camera_identity
        self.device_provider = device_provider or enumerate_usb_devices
        self.poll_interval = poll_interval
        self._laser: USBDevice | None = None
        self._camera: USBDevice | None = None
        self._stopped = asyncio.Event()

    async def wait_for_laser(self, timeout: float | None = None) -> USBDevice | None:
        return await self._wait(lambda: self._laser, timeout)

    async def wait_for_camera(self, timeout: float | None = None) -> USBDevice | None:
        return await self._wait(lambda: self._camera, timeout)

    def current_laser_device(self) -> USBDevice | None:
        return self._laser

    def current_camera_device(self) -> USBDevice | None:
        return self._camera

    async def refresh(self) -> None:
        devices = await asyncio.to_thread(self.device_provider)
        laser_matches = [device for device in devices if matches_identity(device, self.laser_identity)]
        camera_matches = [device for device in devices if matches_identity(device, self.camera_identity)]
        self._laser = laser_matches[0] if len(laser_matches) == 1 else None
        self._camera = camera_matches[0] if len(camera_matches) == 1 else None

    async def watch(self):
        self._stopped.clear()
        while not self._stopped.is_set():
            await self.refresh()
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=self.poll_interval)
            except TimeoutError:
                pass

    async def stop(self) -> None:
        self._stopped.set()

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


def enumerate_usb_devices() -> list[USBDevice]:
    try:
        import pyudev
    except ImportError:
        return []

    context = pyudev.Context()
    devices: list[USBDevice] = []
    for device in context.list_devices(subsystem="tty"):
        node = device.device_node
        if not node:
            continue
        devices.append(device_from_pyudev(node, device))
    for device in context.list_devices(subsystem="video4linux"):
        node = device.device_node
        if not node:
            continue
        devices.append(device_from_pyudev(node, device))
    return devices


def device_from_pyudev(path: str, device) -> USBDevice:
    properties = _merged_device_properties(device)
    return USBDevice(
        path=path,
        vid=properties.get("ID_VENDOR_ID"),
        pid=properties.get("ID_MODEL_ID"),
        serial=properties.get("ID_SERIAL_SHORT"),
        description=properties.get("ID_MODEL_FROM_DATABASE")
        or properties.get("ID_MODEL")
        or properties.get("ID_MODEL_ENC")
        or properties.get("ID_SERIAL")
        or properties.get("ID_V4L_PRODUCT"),
    )


def _merged_device_properties(device) -> dict[str, str]:
    merged: dict[str, str] = {}
    current = device
    while current is not None:
        merged.update({key: str(value) for key, value in dict(current.properties).items()})
        current = getattr(current, "parent", None)
    return merged
