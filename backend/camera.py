from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CameraAdapter:
    stream_url: str | None = None
    connected: bool = False

    async def status(self) -> dict[str, str | bool | None]:
        return {"connected": self.connected, "stream_url": self.stream_url}

