from __future__ import annotations

import re
from dataclasses import dataclass

from .state import MachineState


_STATUS_RE = re.compile(r"^<([^|>]+)(?:\|([^>]*))?>$")


@dataclass(frozen=True)
class GrblStatus:
    state: MachineState
    mpos: tuple[float, ...] | None = None
    wpos: tuple[float, ...] | None = None
    feed: float | None = None
    spindle: float | None = None


def parse_status_line(line: str) -> GrblStatus | None:
    match = _STATUS_RE.match(line.strip())
    if not match:
        return None
    state_text = match.group(1).split(":", 1)[0].lower()
    state = _state_from_text(state_text)
    fields = _parse_fields(match.group(2) or "")
    return GrblStatus(
        state=state,
        mpos=_float_tuple(fields.get("MPos")),
        wpos=_float_tuple(fields.get("WPos")),
        feed=_fs_value(fields.get("FS"), 0),
        spindle=_fs_value(fields.get("FS"), 1),
    )


def parse_error_line(line: str) -> str | None:
    stripped = line.strip()
    if stripped.lower().startswith("error:") or stripped.lower().startswith("alarm:"):
        return stripped
    return None


def _state_from_text(text: str) -> MachineState:
    mapping = {
        "idle": MachineState.IDLE,
        "run": MachineState.RUN,
        "hold": MachineState.HOLD,
        "jog": MachineState.JOG,
        "alarm": MachineState.ALARM,
        "home": MachineState.HOME,
        "check": MachineState.CHECK,
        "door": MachineState.DOOR,
        "sleep": MachineState.SLEEP,
    }
    return mapping.get(text, MachineState.OFFLINE)


def _parse_fields(raw: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for chunk in raw.split("|"):
        if ":" in chunk:
            key, value = chunk.split(":", 1)
            fields[key] = value
    return fields


def _float_tuple(value: str | None) -> tuple[float, ...] | None:
    if not value:
        return None
    try:
        return tuple(float(part) for part in value.split(","))
    except ValueError:
        return None


def _fs_value(value: str | None, index: int) -> float | None:
    parsed = _float_tuple(value)
    if parsed is None or len(parsed) <= index:
        return None
    return parsed[index]

