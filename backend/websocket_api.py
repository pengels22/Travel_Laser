from __future__ import annotations

import asyncio
import json
from typing import Any

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

from .grbl_proxy import GrblProxy
from .mode_manager import ModeManager
from .safety import EstopSource, SafetyController
from .state import ControllerState, LaserMode, utc_now_iso


class WebSocketAPI:
    def __init__(
        self,
        state: ControllerState,
        safety: SafetyController,
        proxy: GrblProxy,
        mode_manager: ModeManager,
        host: str,
        port: int,
        token: str,
    ) -> None:
        self.state = state
        self.safety = safety
        self.proxy = proxy
        self.mode_manager = mode_manager
        self.host = host
        self.port = port
        self.token = token
        self.server = None
        self._seq = 0

    async def start(self) -> None:
        self.server = await serve(self._handler, self.host, self.port)

    async def stop(self) -> None:
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

    async def handle_packet(self, packet: dict[str, Any]) -> dict[str, Any] | None:
        packet_type = packet.get("type")
        if packet_type == "hello":
            if packet.get("token") != self.token:
                return {"type": "error", "reason": "invalid token"}

            def mutate(snapshot):
                snapshot.ts1.connected = True
                snapshot.ts1.last_seen = utc_now_iso()

            await self.state.update(mutate)
            return {"type": "hello", "device": "laserpi", "protocol": 1}
        if packet_type == "stop":
            return await self._handle_stop(packet)
        if packet_type == "command":
            return await self._handle_command(packet)
        if packet_type == "settings":
            return await self._handle_settings(packet)
        if packet_type == "status":
            return await self.status_packet()
        return {"type": "error", "reason": "unknown packet type"}

    async def status_packet(self) -> dict[str, Any]:
        self._seq += 1
        state = await self.state.to_dict()
        return {
            "type": "status",
            "seq": self._seq,
            "machine": {
                "state": state["machine"]["state"],
                "homed": state["machine"]["homed"],
                "error": state["machine"]["error"],
            },
            "hardware": {
                "power_switch": state["physical"]["power_switch"],
                "estop_switch": state["physical"]["estop_switch"],
                "k1": state["physical"]["k1"],
                "k2": state["physical"]["k2"],
                "laser_usb": state["machine"]["laser_usb_connected"],
                "camera_usb": state["camera"]["connected"],
            },
            "lightburn": state["lightburn"],
            "network": {
                "uplink": "ethernet" if state["network"]["ethernet_connected"] else "wifi",
                "ssid": state["network"]["wifi_ssid"],
                "ip": state["network"]["ip_address"],
                "tailscale_ip": state["network"]["tailscale_ip"],
            },
            "laser_connection": {"mode": state["mode"]["laser_mode"]},
        }

    async def _handler(self, websocket) -> None:
        status_task = asyncio.create_task(self._status_loop(websocket))
        try:
            async for raw in websocket:
                try:
                    packet = json.loads(raw)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"type": "error", "reason": "invalid json"}))
                    continue
                response = await self.handle_packet(packet)
                if response is not None:
                    await websocket.send(json.dumps(response))
        except ConnectionClosed:
            pass
        finally:
            status_task.cancel()
            await asyncio.gather(status_task, return_exceptions=True)
            await self.safety.handle_ts1_disconnected()

    async def _status_loop(self, websocket) -> None:
        while True:
            await asyncio.sleep(1)
            await websocket.send(json.dumps(await self.status_packet()))

    async def _handle_stop(self, packet: dict[str, Any]) -> dict[str, Any]:
        action = packet.get("action")
        ok = True
        reason = None
        if action == "pause":
            await self.proxy.pause()
        elif action == "resume":
            await self.proxy.resume()
        elif action == "stop":
            await self.proxy.stop_job()
        elif action == "estop":
            await self.safety.request_estop(EstopSource.TS1, "TS1 requested E-stop")
        else:
            ok = False
            reason = "unknown stop action"
        return self._ack(packet, ok, reason)

    async def _handle_command(self, packet: dict[str, Any]) -> dict[str, Any]:
        action = packet.get("action")
        if action == "home":
            ok = await self.proxy.home()
            return self._ack(packet, ok, None if ok else "home rejected while job is active")
        if action == "jog":
            ok = await self.proxy.jog(str(packet.get("axis", "")), float(packet.get("distance", 0)))
            return self._ack(packet, ok, None if ok else "jog rejected while job is active")
        return self._ack(packet, False, "unknown command action")

    async def _handle_settings(self, packet: dict[str, Any]) -> dict[str, Any]:
        action = packet.get("action")
        if action == "set_laser_mode":
            try:
                mode = LaserMode(str(packet.get("mode")))
            except ValueError:
                return self._ack(packet, False, "unknown laser mode")
            ok, reason = await self.mode_manager.switch(mode)
            return self._ack(packet, ok, reason)
        if action in {"wifi_scan", "wifi_connect", "wifi_forget"}:
            return self._ack(packet, True)
        return self._ack(packet, False, "unknown settings action")

    def _ack(self, packet: dict[str, Any], ok: bool, reason: str | None = None) -> dict[str, Any]:
        response: dict[str, Any] = {"type": "ack", "id": packet.get("id"), "ok": ok}
        if reason:
            response["reason"] = reason
        return response

