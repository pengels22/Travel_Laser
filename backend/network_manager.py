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
        networks: list[WifiNetwork] = []
        try:
            output = await self._run_nmcli("-t", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list", "ifname", interface)
            networks = _parse_nmcli_wifi_list(output)
        except Exception:
            networks = []
        if networks:
            return networks
        output = await self._run_iw_scan(interface)
        return _parse_iw_scan(output)

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

    async def _run_iw_scan(self, interface: str) -> str:
        last_error: Exception | None = None
        for iw_path in ("/usr/sbin/iw", "/sbin/iw", "iw"):
            try:
                return await self._run_command(iw_path, "dev", interface, "scan")
            except Exception as exc:
                last_error = exc
        raise RuntimeError(f"iw scan failed: {last_error}")

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


def _parse_nmcli_wifi_list(output: str) -> list[WifiNetwork]:
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


def _parse_iw_scan(output: str) -> list[WifiNetwork]:
    networks_by_ssid: dict[str, WifiNetwork] = {}
    block: list[str] = []
    for line in output.splitlines():
        if line.startswith("BSS "):
            _add_iw_network(networks_by_ssid, block)
            block = [line]
        elif block:
            block.append(line)
    _add_iw_network(networks_by_ssid, block)
    return sorted(
        networks_by_ssid.values(),
        key=lambda network: (network.signal is None, -(network.signal or 0), network.ssid.lower()),
    )


def _add_iw_network(networks_by_ssid: dict[str, WifiNetwork], block: list[str]) -> None:
    if not block:
        return
    ssid: str | None = None
    signal: int | None = None
    has_privacy = "Privacy" in block[0]
    has_wpa = False
    connected = "(on " in block[0] and "-- associated" in block[0]

    for raw_line in block[1:]:
        line = raw_line.strip()
        if line.startswith("SSID:"):
            ssid = line.partition(":")[2].strip()
        elif line.startswith("signal:"):
            signal = _signal_dbm_to_percent(line.partition(":")[2].strip())
        elif line.startswith("capability:") and "Privacy" in line:
            has_privacy = True
        elif line.startswith("RSN:") or line.startswith("WPA:"):
            has_wpa = True

    if not ssid:
        return
    security = "WPA/WPA2" if has_wpa else "WEP" if has_privacy else "open"
    network = WifiNetwork(ssid=ssid, signal=signal, security=security, connected=connected)
    existing = networks_by_ssid.get(ssid)
    if existing is None or (network.signal or 0) > (existing.signal or 0):
        networks_by_ssid[ssid] = network


def _signal_dbm_to_percent(value: str) -> int | None:
    try:
        dbm = float(value.split()[0])
    except (ValueError, IndexError):
        return None
    return max(0, min(100, int(round(2 * (dbm + 100)))))
