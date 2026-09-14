from __future__ import annotations

from .state import ControllerState


async def health_snapshot(state: ControllerState) -> dict:
    snapshot = await state.to_dict()
    return {"ok": True, "state": snapshot}

