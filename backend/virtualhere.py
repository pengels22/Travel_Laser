from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class VirtualHereService:
    service_name: str = "virtualhere"
    dry_run: bool = False
    backend_controls_service: bool = False
    active: bool = False

    async def start(self) -> bool:
        if not self.backend_controls_service:
            await asyncio.sleep(0)
            self.active = True
            return True
        if self.dry_run:
            await asyncio.sleep(0)
            self.active = True
            return True
        await self._systemctl("start")
        self.active = True
        return True

    async def stop(self) -> bool:
        if not self.backend_controls_service:
            await asyncio.sleep(0)
            self.active = False
            return True
        if self.dry_run:
            await asyncio.sleep(0)
            self.active = False
            return True
        await self._systemctl("stop")
        self.active = False
        return True

    async def is_active(self) -> bool:
        if not self.backend_controls_service or self.dry_run:
            await asyncio.sleep(0)
            return self.active
        process = await asyncio.create_subprocess_exec(
            "systemctl",
            "is-active",
            "--quiet",
            self.service_name,
        )
        return await process.wait() == 0

    async def _systemctl(self, action: str) -> None:
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
