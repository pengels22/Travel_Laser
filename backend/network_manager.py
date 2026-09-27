from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass


@dataclass
class WifiNetwork:
    ssid: str
    signal: int | None = None
    security: str | None = None
    connected: bool = False
    saved: bool = False


@dataclass
class NetworkInterfaceStatus:
    interface: str
    connected: bool = False
    ip_address: str | None = None
    ssid: str | None = None


@dataclass
class TailscaleStatus:
    connected: bool = False
    ip_address: str | None = None
    status: str = "unavailable"


class NetworkManager:
    def __init__(self, uplink_interface: str = "wlan0", dry_run: bool = False) -> None:
        self.uplink_interface = uplink_interface
        self.dry_run = dry_run
        self.actions: list[tuple[str, str, str | None]] = []

    async def scan_wifi(self, interface: str | None = None) -> list[WifiNetwork]:
        interface = interface or self.uplink_interface
        self.actions.append(("scan", interface, None))
        if self.dry_run:
            await asyncio.sleep(0)
            return []
        output = await self._run_nmcli("-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", interface)
        networks: list[WifiNetwork] = []
        for line in output.splitlines():
            if not line:
                continue
            fields = line.split(":", 2)
            ssid = fields[0]
            if ssid:
                signal = fields[1] if len(fields) > 1 else ""
                security = fields[2] if len(fields) > 2 and fields[2] else "open"
                networks.append(WifiNetwork(ssid=ssid, signal=int(signal) if signal.isdigit() else None, security=security))
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

    async def interface_status(self, interface: str) -> NetworkInterfaceStatus:
        self.actions.append(("status", interface, None))
        if self.dry_run:
            await asyncio.sleep(0)
            return NetworkInterfaceStatus(interface=interface)
        output = await self._run_nmcli("-t", "-f", "GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS", "device", "show", interface)
        return _parse_interface_status(interface, output)

    async def tailscale_status(self, interface: str = "tailscale0") -> TailscaleStatus:
        if self.dry_run:
            await asyncio.sleep(0)
            return TailscaleStatus(status="dry-run")
        try:
            output = await self._run_command("tailscale", "status", "--json")
            parsed = json.loads(output)
            ips = parsed.get("Self", {}).get("TailscaleIPs", []) or []
            ipv4 = next((ip for ip in ips if "." in ip), None)
            backend_state = str(parsed.get("BackendState") or "").lower()
            connected = bool(ipv4 and backend_state == "running")
            return TailscaleStatus(
                connected=connected,
                ip_address=ipv4,
                status="connected" if connected else backend_state or "not connected",
            )
        except Exception:
            try:
                status = await self.interface_status(interface)
                return TailscaleStatus(
                    connected=status.connected and bool(status.ip_address),
                    ip_address=status.ip_address,
                    status="connected" if status.connected and status.ip_address else "interface unavailable",
                )
            except Exception as exc:
                return TailscaleStatus(status=str(exc) or "unavailable")

    async def _run_nmcli(self, *args: str) -> str:
        return await self._run_command("nmcli", *args)

    async def _run_command(self, *args: str) -> str:
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode().strip() or f"nmcli failed with exit {process.returncode}")
        return stdout.decode()


def _parse_interface_status(interface: str, output: str) -> NetworkInterfaceStatus:
    fields: dict[str, list[str]] = {}
    for line in output.splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        fields.setdefault(key, []).append(value)
    state = fields.get("GENERAL.STATE", [""])[0].lower()
    connection = fields.get("GENERAL.CONNECTION", [None])[0]
    ip_value = fields.get("IP4.ADDRESS[1]", fields.get("IP4.ADDRESS", [None]))[0]
    ip_address = ip_value.split("/", 1)[0] if ip_value else None
    return NetworkInterfaceStatus(
        interface=interface,
        connected=state.startswith("100") or "(connected)" in state,
        ip_address=ip_address,
        ssid=connection if connection and connection != "--" else None,
    )
