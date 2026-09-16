from __future__ import annotations

from pathlib import Path

from aiohttp import web

from .grbl_proxy import GrblProxy
from .safety import EstopSource, SafetyController
from .state import ControllerState


class WebPortal:
    def __init__(
        self,
        state: ControllerState,
        safety: SafetyController,
        proxy: GrblProxy,
        static_dir: Path,
        host: str,
        port: int,
    ) -> None:
        self.state = state
        self.safety = safety
        self.proxy = proxy
        self.static_dir = static_dir
        self.host = host
        self.port = port
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/api/status", self._status)
        app.router.add_post("/api/home", self._home)
        app.router.add_post("/api/estop", self._estop)
        app.router.add_static("/", self.static_dir, show_index=False, append_version=True)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

    async def stop(self) -> None:
        if self.runner:
            await self.runner.cleanup()
            self.runner = None

    async def _status(self, _: web.Request) -> web.Response:
        return web.json_response(await self.state.to_dict())

    async def _home(self, _: web.Request) -> web.Response:
        accepted = await self.proxy.home()
        if not accepted:
            return web.json_response(
                {"ok": False, "message": "Home is unavailable while the machine is active"},
                status=409,
            )
        return web.json_response({"ok": True})

    async def _estop(self, _: web.Request) -> web.Response:
        await self.safety.request_estop(EstopSource.WEB, "web portal requested E-stop")
        return web.json_response({"ok": True})
