from __future__ import annotations

import json
from pathlib import Path

from .events import ControllerEvent, EventCode
from .grbl_proxy import GrblProxy
from .state import ControllerState, LaserMode
from .virtualhere import VirtualHereService


class ModeManager:
    def __init__(
        self,
        state: ControllerState,
        proxy: GrblProxy,
        virtualhere: VirtualHereService,
        state_file: Path,
    ) -> None:
        self.state = state
        self.proxy = proxy
        self.virtualhere = virtualhere
        self.state_file = state_file
        self.events: list[ControllerEvent] = []

    async def restore(self, default: LaserMode = LaserMode.NETWORK) -> LaserMode:
        mode = default
        if self.state_file.exists():
            try:
                mode = LaserMode(json.loads(self.state_file.read_text()).get("laser_mode", default.value))
            except (ValueError, json.JSONDecodeError):
                mode = default
        await self._set_state_mode(mode)
        return mode

    async def switch(self, target: LaserMode) -> tuple[bool, str | None]:
        snapshot = await self.state.snapshot()
        if snapshot.mode.laser_mode == target:
            if target == LaserMode.NETWORK and not self.proxy.active:
                await self.virtualhere.stop()
                await self.proxy.start()
            elif target == LaserMode.VIRTUALHERE and not await self.virtualhere.is_active():
                await self.proxy.stop()
                await self.virtualhere.start()
            return True, None
        if snapshot.lightburn.stream_active:
            return False, "cannot switch laser mode while a job stream is active"

        await self.proxy.stop()
        await self.virtualhere.stop()

        if target == LaserMode.NETWORK:
            if await self.virtualhere.is_active():
                return False, "VirtualHere is still active"
            await self.proxy.start()
        else:
            if self.proxy.active:
                return False, "GRBL proxy is still active"
            await self.virtualhere.start()

        await self._set_state_mode(target)
        self._persist(target)
        self.events.append(ControllerEvent(EventCode.MODE_CHANGED, details={"mode": target.value}))
        return True, None

    async def _set_state_mode(self, mode: LaserMode) -> None:
        def mutate(snapshot):
            snapshot.mode.laser_mode = mode

        await self.state.update(mutate)

    def _persist(self, mode: LaserMode) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({"laser_mode": mode.value}, indent=2) + "\n")
