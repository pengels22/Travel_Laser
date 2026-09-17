from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path


class USBLogExporter:
    def __init__(self, log_source: str = "/var/log/travel-laser") -> None:
        self.log_source = Path(log_source)

    async def export(self) -> str:
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
