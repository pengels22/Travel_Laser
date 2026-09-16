from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from .config import AppConfig, load_config
from .gpio import LinuxGPIOBackend, MockGPIOBackend
from .grbl_proxy import GrblProxy
from .logging_setup import EventLogger, configure_logging
from .mode_manager import ModeManager
from .safety import SafetyController
from .serial_device import open_laser_serial
from .state import ControllerState, LaserMode
from .virtualhere import VirtualHereService
from .web_portal import WebPortal

LOGGER = logging.getLogger(__name__)


async def run(config_path: Path | None, mock: bool) -> None:
    config = load_config(config_path)
    configure_logging(config.logging.level)
    event_logger = EventLogger(config.logging.json_file)
    state = ControllerState()
    gpio = MockGPIOBackend() if mock else LinuxGPIOBackend(config.gpio)
    safety = SafetyController(state, gpio)
    await safety.initialize_safe()

    def apply_config(snapshot):
        snapshot.safety.fire_enabled = config.fire.enabled and config.fire.sensor_enabled
        snapshot.camera.stream_url = config.camera.stream_url
        snapshot.camera.stream_type = config.camera.stream_type
        snapshot.network.tailscale_interface = config.network.tailscale_interface
        snapshot.network.tailscale_ip = config.network.tailscale_ip
        snapshot.network.tailscale_connected = bool(config.network.tailscale_enabled and config.network.tailscale_ip)
        snapshot.network.tailscale_status = (
            "connected"
            if snapshot.network.tailscale_connected
            else "waiting for Tailscale IP"
            if config.network.tailscale_enabled
            else "disabled"
        )

    await state.update(apply_config)

    proxy = GrblProxy(
        state,
        safety,
        port=config.laser.tcp_port,
        serial_factory=lambda: open_laser_serial(config.laser.usb, config.laser.baud),
        status_poll_interval=config.laser.status_poll_interval_seconds,
    )
    virtualhere = VirtualHereService(
        service_name=config.virtualhere.service_name,
        dry_run=mock,
        backend_controls_service=config.virtualhere.backend_controls_service,
    )
    state_dir = Path(".state") if mock else Path("/var/lib/travel-laser")
    mode_manager = ModeManager(state, proxy, virtualhere, state_dir / "mode.json")
    restored_mode = await mode_manager.restore(LaserMode(config.laser.mode))
    portal = WebPortal(
        state,
        safety,
        proxy,
        static_dir=Path(__file__).resolve().parent.parent / "web",
        host=_resolve_web_host(config, allow_unset_tailscale=mock),
        port=config.web.port,
    )

    await safety.refresh_physical_inputs()
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
    LOGGER.info("Travel Laser controller ready in %s mode", restored_mode.value)

    stop_event = asyncio.Event()
    physical_poll_task = asyncio.create_task(_physical_input_loop(safety))
    try:
        await stop_event.wait()
    finally:
        physical_poll_task.cancel()
        await asyncio.gather(physical_poll_task, return_exceptions=True)
        await portal.stop()
        await proxy.stop()
        await virtualhere.stop()


async def _physical_input_loop(safety: SafetyController) -> None:
    while True:
        await asyncio.sleep(0.05)
        await safety.refresh_physical_inputs()


def main() -> None:
    parser = argparse.ArgumentParser(description="Travel Laser controller backend")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--mock", action="store_true", help="use mock GPIO/serial hardware")
    args = parser.parse_args()
    asyncio.run(run(args.config, args.mock))


def _resolve_web_host(config: AppConfig, allow_unset_tailscale: bool = False) -> str:
    if config.web.bind_to_tailscale:
        if not config.network.tailscale_ip:
            if allow_unset_tailscale:
                return "127.0.0.1"
            raise RuntimeError(
                "web.bind_to_tailscale is enabled but network.tailscale.ip_address is not set; "
                "fill it in after the device joins Tailscale"
            )
        return config.network.tailscale_ip
    return config.web.host or "0.0.0.0"


if __name__ == "__main__":
    main()
