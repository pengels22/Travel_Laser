from __future__ import annotations

import asyncio
import json
import re
import shlex
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
                "lsblk", "-b", "-P", "-nr", "-o", "NAME,TYPE,TRAN,SIZE,PKNAME",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError:
            return None
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None
        candidates = _usb_partition_candidates_from_lsblk(stdout.decode())
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
            "lsblk", "-b", "-P", "-nr", "-o", "NAME,TYPE,TRAN,SIZE,MOUNTPOINT,PKNAME",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        if process.returncode != 0:
            return None
        rows = _parse_lsblk_pairs(stdout.decode())
        transport_by_name = {row.get("NAME", ""): row.get("TRAN", "") for row in rows}
        for row in rows:
            if row.get("TYPE") != "part" or not _row_is_usb(row, transport_by_name):
                continue
            try:
                size_bytes = int(row.get("SIZE", "0"))
            except ValueError:
                continue
            mountpoint = row.get("MOUNTPOINT", "")
            if not mountpoint:
                continue
            mount = Path(mountpoint)
            if size_bytes >= 200 * 1024 * 1024 and mount.is_dir() and _writable(mount):
                return mount
        return None


def _writable(path: Path) -> bool:
    return path.exists() and path.is_dir() and bool(path.stat().st_mode & 0o222)


def _valid_device_name(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value)) and ".." not in value


def _usb_partition_candidates_from_lsblk(output: str, min_bytes: int = 200 * 1024 * 1024) -> list[str]:
    rows = _parse_lsblk_pairs(output)
    transport_by_name = {row.get("NAME", ""): row.get("TRAN", "") for row in rows}
    candidates: list[str] = []
    for row in rows:
        name = row.get("NAME", "")
        if row.get("TYPE") != "part" or not _row_is_usb(row, transport_by_name) or not _valid_device_name(name):
            continue
        try:
            size_bytes = int(row.get("SIZE", "0"))
        except ValueError:
            continue
        if size_bytes >= min_bytes:
            candidates.append(name)
    return candidates


def _row_is_usb(row: dict[str, str], transport_by_name: dict[str, str]) -> bool:
    if row.get("TRAN") == "usb":
        return True
    parent = row.get("PKNAME", "")
    return bool(parent and transport_by_name.get(parent) == "usb")


def _parse_lsblk_pairs(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        fields: dict[str, str] = {}
        for token in shlex.split(line):
            key, separator, value = token.partition("=")
            if separator:
                fields[key] = value
        if fields:
            rows.append(fields)
    return rows
