from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class WifiNetwork:
    ssid: str
    signal: int | None = None


class NetworkManager:
    def __init__(self, uplink_interface: str = "wlan1", dry_run: bool = False) -> None:
        self.uplink_interface = uplink_interface
        self.dry_run = dry_run
        self.actions: list[tuple[str, str, str | None]] = []

    async def scan_wifi(self, interface: str | None = None) -> list[WifiNetwork]:
        interface = interface or self.uplink_interface
        self.actions.append(("scan", interface, None))
        if self.dry_run:
            await asyncio.sleep(0)
            return []
        output = await self._run_nmcli("-t", "-f", "SSID,SIGNAL", "device", "wifi", "list", "ifname", interface)
        networks: list[WifiNetwork] = []
        for line in output.splitlines():
            if not line:
                continue
            ssid, _, signal = line.partition(":")
            if ssid:
                networks.append(WifiNetwork(ssid=ssid, signal=int(signal) if signal.isdigit() else None))
        return networks

    async def connect_wifi(self, ssid: str, password: str, interface: str | None = None) -> bool:
        interface = interface or self.uplink_interface
        self.actions.append(("connect", interface, ssid))
        if self.dry_run:
            await asyncio.sleep(0)
            return True
        await self._run_nmcli("device", "wifi", "connect", ssid, "password", password, "ifname", interface)
        return True

    async def forget_wifi(self, ssid: str, interface: str | None = None) -> bool:
        interface = interface or self.uplink_interface
        self.actions.append(("forget", interface, ssid))
        if self.dry_run:
            await asyncio.sleep(0)
            return True
        await self._run_nmcli("connection", "delete", ssid)
        return True

    async def _run_nmcli(self, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            "nmcli",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode().strip() or f"nmcli failed with exit {process.returncode}")
        return stdout.decode()
