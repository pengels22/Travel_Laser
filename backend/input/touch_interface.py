from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class TouchPoint:
    id: int
    x: int
    y: int


@dataclass(frozen=True)
class TouchEvent:
    kind: str
    points: tuple[TouchPoint, ...]


class TouchInput(Protocol):
    async def initialize(self) -> None: ...
    async def read_event(self) -> TouchEvent | None: ...
    async def close(self) -> None: ...

