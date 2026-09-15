from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from .config import load_config
from .gpio import LinuxGPIOBackend, MockGPIOBackend
from .grbl_proxy import GrblProxy
from .logging_setup import EventLogger, configure_logging
from .mode_manager import ModeManager
from .safety import SafetyController
from .state import ControllerState, LaserMode
from .virtualhere import VirtualHereService
from .web_portal import WebPortal
from .websocket_api import WebSocketAPI

LOGGER = logging.getLogger(__name__)


async def run(config_path: Path | None, mock: bool) -> None:
    config = load_config(config_path)
    configure_logging(config.logging.level)
    event_logger = EventLogger(config.logging.json_file)
    state = ControllerState()
    gpio = MockGPIOBackend() if mock else LinuxGPIOBackend()
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()

    def apply_config(snapshot):
        snapshot.safety.fire_enabled = config.fire.enabled and config.fire.sensor_enabled
        snapshot.camera.stream_url = config.camera.stream_url

    await state.update(apply_config)

    proxy = GrblProxy(
        state,
        safety,
        port=config.laser.tcp_port,
        status_poll_interval=config.laser.status_poll_interval_seconds,
    )
    virtualhere = VirtualHereService()
    state_dir = Path(".state") if mock else Path("/var/lib/ts1-controller")
    mode_manager = ModeManager(state, proxy, virtualhere, state_dir / "mode.json")
    restored_mode = await mode_manager.restore(LaserMode(config.laser.mode))
    ws_api = WebSocketAPI(
        state,
        safety,
        proxy,
        mode_manager,
        host=config.websocket.host,
        port=config.websocket.port,
        token=config.websocket.shared_token,
    )
    portal = WebPortal(
        state,
        safety,
        proxy,
        static_dir=Path(__file__).resolve().parent.parent / "web",
        host=config.web.host,
        port=config.web.port,
    )

    await safety.refresh_physical_inputs()
    await ws_api.start()
    await portal.start()
    if restored_mode == LaserMode.NETWORK:
        await proxy.start()
    else:
        await virtualhere.start()

    def ready(snapshot):
        snapshot.ready = True

    await state.update(ready)
    for event in safety.events:
        event_logger.emit(event)
    LOGGER.info("TS1 controller ready in %s mode", restored_mode.value)

    stop_event = asyncio.Event()
    try:
        await stop_event.wait()
    finally:
        await portal.stop()
        await ws_api.stop()
        await proxy.stop()
        await virtualhere.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="TS1 laser controller backend")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--mock", action="store_true", help="use mock GPIO/serial hardware")
    args = parser.parse_args()
    asyncio.run(run(args.config, args.mock))


if __name__ == "__main__":
    main()
