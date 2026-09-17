from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass
class UIBackendState:
    raw: dict[str, Any]
    online: bool = True

    @property
    def machine_state(self) -> str:
        return str(self.raw.get("machine", {}).get("state", "offline"))


class LocalAPIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8081", timeout: float = 1.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, *_args) -> None:
        await self.close()

    async def close(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None

    async def state(self) -> UIBackendState:
        try:
            payload = await self._request("GET", "/state")
            return UIBackendState(payload)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError):
            return UIBackendState({}, online=False)

    async def command(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            return await self._request("POST", path, payload)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
            return {"ok": False, "status": "error", "code": "CONTROLLER_OFFLINE", "message": str(exc), "data": {}}

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.session is None:
            raise RuntimeError("LocalAPIClient must be used as an async context manager")
        async with self.session.request(method, self.base_url + path, json=payload) as response:
            body = await response.json()
            if response.status >= 400:
                return body
            return body
