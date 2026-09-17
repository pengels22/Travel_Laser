from __future__ import annotations

from aiohttp import web

from .command_service import ControllerCommandService
from .safety import EstopSource
from .state import ControllerState


class LocalControllerAPI:
    """Loopback-only API used by the SPI touchscreen process."""

    def __init__(self, state: ControllerState, commands: ControllerCommandService, host: str = "127.0.0.1", port: int = 8081) -> None:
        self.state = state
        self.commands = commands
        self.host = host
        self.port = port
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/state", self._state)
        app.router.add_get("/health", self._health)
        app.router.add_get("/diagnostics", self._diagnostics)
        app.router.add_post("/commands/home", self._home)
        app.router.add_post("/commands/stop", self._stop)
        app.router.add_post("/commands/estop", self._estop)
        app.router.add_get("/network/scan", self._network_scan)
        app.router.add_post("/network/connect", self._wifi_connect)
        app.router.add_post("/network/forget", self._wifi_forget)
        app.router.add_post("/mode", self._mode)
        app.router.add_post("/logs/export", self._log_export)
        app.router.add_post("/system/restart", self._restart)
        app.router.add_post("/system/reboot", self._reboot)
        app.router.add_post("/system/shutdown", self._shutdown)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", self.port)
        await self.site.start()

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()
            self.runner = None

    async def _state(self, _: web.Request) -> web.Response:
        payload = await self.state.to_dict()
        payload["controller_online"] = True
        return web.json_response(payload)

    async def _health(self, _: web.Request) -> web.Response:
        snapshot = await self.state.snapshot()
        return web.json_response({"ok": True, "ready": snapshot.ready})

    async def _diagnostics(self, _: web.Request) -> web.Response:
        payload = await self.state.to_dict()
        return web.json_response(payload.get("diagnostics", {}))

    async def _home(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.home())

    async def _stop(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.stop())

    async def _estop(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.estop(EstopSource.LOCAL_UI, "local touchscreen requested E-stop"))

    async def _network_scan(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.network_scan())

    async def _wifi_connect(self, request: web.Request) -> web.Response:
        body = await self._json(request)
        return await self._result(self.commands.wifi_connect(str(body.get("ssid", "")), str(body.get("password", ""))))

    async def _wifi_forget(self, request: web.Request) -> web.Response:
        body = await self._json(request)
        return await self._result(self.commands.wifi_forget(str(body.get("ssid", ""))))

    async def _mode(self, request: web.Request) -> web.Response:
        body = await self._json(request)
        return await self._result(self.commands.mode_change(str(body.get("mode", ""))))

    async def _log_export(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.log_export())

    async def _restart(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.service_restart())

    async def _reboot(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.reboot())

    async def _shutdown(self, _: web.Request) -> web.Response:
        return await self._result(self.commands.shutdown())

    async def _result(self, result) -> web.Response:
        result = await result
        return web.json_response(result.as_dict(), status=200 if result.ok else 409)

    async def _json(self, request: web.Request) -> dict:
        try:
            body = await request.json()
        except (ValueError, TypeError):
            return {}
        return body if isinstance(body, dict) else {}
