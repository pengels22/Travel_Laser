from __future__ import annotations

import asyncio
from dataclasses import dataclass
from collections.abc import Awaitable, Callable


SystemctlRunner = Callable[[str, str], Awaitable[bool]]


@dataclass
class VirtualHereService:
    service_name: str = "virtualhere"
    dry_run: bool = False
    backend_controls_service: bool = False
    active: bool = False
    runner: SystemctlRunner | None = None

    async def start(self) -> bool:
        if not self.backend_controls_service:
            self.active = await self.is_active()
            if not self.active:
                raise RuntimeError(
                    f"VirtualHere service {self.service_name!r} is not active and backend control is disabled"
                )
            return self.active
        if self.dry_run:
            await asyncio.sleep(0)
            self.active = True
            return True
        await self._systemctl("start")
        self.active = await self.is_active()
        if not self.active:
            raise RuntimeError(f"VirtualHere service {self.service_name!r} did not become active")
        return True

    async def stop(self) -> bool:
        if not self.backend_controls_service:
            await asyncio.sleep(0)
            self.active = await self.is_active()
            return True
        if self.dry_run:
            await asyncio.sleep(0)
            self.active = False
            return True
        await self._systemctl("stop")
        self.active = await self.is_active()
        if self.active:
            raise RuntimeError(f"VirtualHere service {self.service_name!r} did not stop")
        return True

    async def is_active(self) -> bool:
        if self.runner:
            self.active = await self.runner("is-active", self.service_name)
            return self.active
        if self.dry_run:
            await asyncio.sleep(0)
            return self.active
        try:
            process = await asyncio.create_subprocess_exec(
                "systemctl",
                "is-active",
                "--quiet",
                self.service_name,
            )
        except OSError:
            self.active = False
            return False
        return await process.wait() == 0

    async def _systemctl(self, action: str) -> None:
        if self.runner:
            ok = await self.runner(action, self.service_name)
            if not ok:
                raise RuntimeError(f"systemctl {action} {self.service_name} failed")
            return
        process = await asyncio.create_subprocess_exec(
            "systemctl",
            action,
            self.service_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode().strip() or f"systemctl {action} {self.service_name} failed")
