from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path


class USBLogExporter:
    def __init__(
        self,
        log_source: str = "/var/log/travel-laser",
        helper_path: str = "/usr/local/sbin/travel-laser-log-export",
        status_file: str = "/var/log/travel-laser/last-usb-export.json",
    ) -> None:
        self.log_source = Path(log_source)
        self.helper_path = helper_path
        self.status_file = Path(status_file)

    async def export(self) -> str:
        device = await self._find_usb_block_device()
        if device:
            await self._run_helper(device)
            return self._read_status_destination()

        # Development fallback for tests and already-mounted removable media.
        mount = await self._find_usb_mount()
        if mount is None:
            raise RuntimeError("No writable USB drive larger than 200 MB detected")
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        destination = mount / f"Travel_Laser_Logs_{stamp}"
        destination.mkdir(parents=False, exist_ok=False)
        if self.log_source.is_dir():
            for source in self.log_source.iterdir():
                target = destination / source.name
                if source.is_file():
                    target.write_bytes(source.read_bytes())
        (destination / "system-info.txt").write_text(
            "Travel Laser log export\n" + json.dumps({"timestamp": stamp}, indent=2) + "\n",
            encoding="utf-8",
        )
        return str(destination)

    async def _find_usb_block_device(self) -> str | None:
        try:
            process = await asyncio.create_subprocess_exec(
                "lsblk", "-b", "-nr", "-o", "NAME,TYPE,TRAN,SIZE",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError:
            return None
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None
        candidates: list[str] = []
        for line in stdout.decode().splitlines():
            fields = line.split()
            if len(fields) != 4 or fields[1] != "part" or fields[2] != "usb":
                continue
            try:
                size_bytes = int(fields[3])
            except ValueError:
                continue
            if size_bytes >= 200 * 1024 * 1024 and _valid_device_name(fields[0]):
                candidates.append(fields[0])
        if len(candidates) > 1:
            raise RuntimeError("Multiple eligible USB partitions detected; remove extras and retry")
        return candidates[0] if candidates else None

    async def _run_helper(self, device_name: str) -> None:
        if not _valid_device_name(device_name):
            raise RuntimeError("Invalid USB block device name")
        process = await asyncio.create_subprocess_exec(
            "sudo",
            "-n",
            self.helper_path,
            device_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode().strip() or stdout.decode().strip() or "USB log export failed")

    def _read_status_destination(self) -> str:
        try:
            payload = json.loads(self.status_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("USB log export completed but status file was not readable") from exc
        destination = payload.get("destination")
        if not isinstance(destination, str) or not destination:
            raise RuntimeError("USB log export status did not include a destination")
        return destination

    async def _find_usb_mount(self) -> Path | None:
        process = await asyncio.create_subprocess_exec(
            "lsblk", "-b", "-nr", "-o", "TYPE,TRAN,SIZE,MOUNTPOINT",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None
        for line in stdout.decode().splitlines():
            fields = line.split(None, 3)
            if len(fields) != 4 or fields[0] != "part" or fields[1] != "usb":
                continue
            try:
                size_bytes = int(fields[2])
            except ValueError:
                continue
            mount = Path(fields[3])
            if size_bytes >= 200 * 1024 * 1024 and mount.is_dir() and _writable(mount):
                return mount
        return None


def _writable(path: Path) -> bool:
    return path.exists() and path.is_dir() and bool(path.stat().st_mode & 0o222)


def _valid_device_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value)) and ".." not in value
