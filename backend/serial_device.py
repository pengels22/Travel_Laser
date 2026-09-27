from __future__ import annotations

import glob
import os
import asyncio

from .config import USBIdentity
from .usb import USBDevice, device_from_pyudev, matches_identity


class AsyncSerialEndpoint:
    def __init__(self, reader, writer) -> None:
        self.reader = reader
        self.writer = writer

    async def write(self, data: bytes) -> None:
        self.writer.write(data)
        await self.writer.drain()

    async def read(self, n: int = 4096) -> bytes:
        return await self.reader.read(n)

    async def close(self) -> None:
        self.writer.close()
        await self.writer.wait_closed()


def discover_serial_device(identity: USBIdentity) -> str:
    """Find the laser through stable serial-by-id paths and udev metadata."""
    candidates: list[USBDevice] = []
    for link in sorted(glob.glob("/dev/serial/by-id/*")):
        device_node = os.path.realpath(link)
        device = _udev_device(link, device_node)
        if matches_identity(device, identity):
            candidates.append(device)

    if len(candidates) != 1:
        raise RuntimeError(
            "expected exactly one laser USB device matching configured identity; "
            f"found {len(candidates)}"
        )
    return candidates[0].path


async def open_laser_serial(identity: USBIdentity, baud: int, timeout: float = 10.0) -> AsyncSerialEndpoint:
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        try:
            path = discover_serial_device(identity)
            break
        except RuntimeError:
            if asyncio.get_running_loop().time() >= deadline:
                raise RuntimeError("LASER_NOT_FOUND: laser USB did not enumerate before timeout")
            await asyncio.sleep(0.25)
    try:
        import serial_asyncio
    except ImportError as exc:
        raise RuntimeError("pyserial-asyncio is required for the real laser serial connection") from exc

    reader, writer = await serial_asyncio.open_serial_connection(url=path, baudrate=baud)
    return AsyncSerialEndpoint(reader, writer)


def _udev_device(path: str, device_node: str) -> USBDevice:
    try:
        import pyudev
    except ImportError:
        return USBDevice(path=path)
    context = pyudev.Context()
    device = pyudev.Devices.from_device_file(context, device_node)
    discovered = device_from_pyudev(path, device)
    return USBDevice(
        path=path,
        vid=discovered.vid,
        pid=discovered.pid,
        serial=discovered.serial,
        description=discovered.description,
    )
