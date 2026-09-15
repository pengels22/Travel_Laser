from __future__ import annotations

import json
import logging
from pathlib import Path

from .events import ControllerEvent


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


class EventLogger:
    def __init__(self, path: str | None = None) -> None:
        self.logger = logging.getLogger("travel_laser.events")
        self.path = Path(path) if path else None
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: ControllerEvent) -> None:
        data = event.as_log_dict()
        self.logger.log(getattr(logging, event.severity.value, logging.INFO), "%s", data)
        if self.path:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(data, sort_keys=True) + "\n")
