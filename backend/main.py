from __future__ import annotations

import argparse
import asyncio
import logging
import subprocess
from pathlib import Path

from .camera import CameraAdapter
from .config import AppConfig, load_config
from .command_service import ControllerCommandService
from .diagnostics import DiagnosticsProvider
from .events import ControllerEvent, EventCode, Severity
from .gpio import LinuxGPIOBackend, MockGPIOBackend
from .grbl_proxy import GrblProxy
from .logging_setup import EventLogger, configure_logging
from .mode_manager import ModeManager
from .network_manager import NetworkManager
from .local_api import LocalControllerAPI
from .safety import SafetyController
from .serial_device import open_laser_serial
from .state import ControllerState, LaserMode, MachineState
from .virtualhere import VirtualHereService
from .web_portal import WebPortal

LOGGER = logging.getLogger(__name__)


async def run(config_path: Path | None, mock: bool) -> None:
    config = load_config(config_path)
    configure_logging(config.logging.level)
    event_logger = EventLogger(config.logging.json_file)
    state = ControllerState()
    gpio = MockGPIOBackend() if mock else LinuxGPIOBackend(config.gpio)
    safety = SafetyController(state, gpio, event_sink=event_logger)
    await safety.initialize_safe()

    def apply_config(snapshot):
        snapshot.safety.fire_enabled = config.fire.enabled and config.fire.sensor_enabled
        snapshot.camera.stream_url = config.camera.stream_url
        snapshot.camera.stream_type = config.camera.stream_type
        snapshot.network.tailscale_interface = config.network.tailscale_interface
        snapshot.network.tailscale_ip = config.network.tailscale_ip
        snapshot.network.tailscale_connected = False
        snapshot.network.tailscale_status = (
            "waiting for live Tailscale status"
            if config.network.tailscale_enabled
            else "disabled"
        )
        snapshot.diagnostics.spi_device = config.display.spi_device
        snapshot.diagnostics.i2c_bus = config.touch.i2c_bus
        snapshot.diagnostics.i2c_address = config.touch.i2c_address

    await state.update(apply_config)

    proxy = GrblProxy(
        state,
        safety,
        port=config.laser.tcp_port,
        serial_factory=lambda: open_laser_serial(
            config.laser.usb, config.laser.baud, config.laser.reconnect_timeout_seconds
        ),
        status_poll_interval=config.laser.status_poll_interval_seconds,
    )
    virtualhere = VirtualHereService(
        service_name=config.virtualhere.service_name,
        dry_run=mock,
        backend_controls_service=config.virtualhere.backend_controls_service,
    )
    state_dir = Path(".state") if mock else Path("/var/lib/travel-laser")
    mode_manager = ModeManager(state, proxy, virtualhere, state_dir / "mode.json")
    network = NetworkManager(uplink_interface=config.network.uplink_wifi_interface, dry_run=mock)
    camera = CameraAdapter(
        stream_url=config.camera.stream_url,
        stream_type=config.camera.stream_type,
        identity=config.camera.usb if config.camera.enabled else None,
        device_path=config.camera.device if config.camera.enabled else None,
    )
    diagnostics = DiagnosticsProvider(config, state, gpio, network, camera, virtualhere)
    commands = ControllerCommandService(state, safety, proxy, mode_manager, network, event_sink=event_logger)
    local_api = LocalControllerAPI(state, commands)
    restored_mode = await mode_manager.restore(LaserMode(config.laser.mode))
    web_host = _resolve_web_host(config, allow_unset_tailscale=mock)
    portal = (
        WebPortal(
            state,
            safety,
            proxy,
            static_dir=Path(__file__).resolve().parent.parent / "web",
            host=web_host,
            port=config.web.port,
            commands=commands,
        )
        if web_host
        else None
    )

    await safety.refresh_physical_inputs()
    await local_api.start()
    if portal:
        await portal.start()
    else:
        LOGGER.warning("external web portal disabled because Tailscale address is unavailable")
    proxy_recovery_task = None
    if restored_mode == LaserMode.NETWORK:
        snapshot = await state.snapshot()
        if snapshot.physical.k1:
            try:
                await proxy.start()
            except Exception as exc:
                LOGGER.error("laser proxy is waiting for USB: %s", exc)

                def mark_laser_missing(current):
                    current.machine.state = MachineState.FAULT
                    current.machine.error = "LASER_NOT_FOUND"

                await state.update(mark_laser_missing)
                proxy_recovery_task = asyncio.create_task(_start_proxy_when_safe(state, proxy))
        else:
            LOGGER.warning("laser proxy held stopped because the safety relay is dropped")
            proxy_recovery_task = asyncio.create_task(_start_proxy_when_safe(state, proxy))
    else:
        await virtualhere.start()

    def ready(snapshot):
        snapshot.ready = True

    await state.update(ready)
    LOGGER.info("Travel Laser controller ready in %s mode", restored_mode.value)

    stop_event = asyncio.Event()
    physical_poll_task = asyncio.create_task(_physical_input_loop(safety))
    network_poll_task = asyncio.create_task(_network_input_loop(state, network, config, event_logger))
    camera_poll_task = asyncio.create_task(_camera_input_loop(state, camera, config, event_logger))
    diagnostics_poll_task = asyncio.create_task(_diagnostics_loop(diagnostics))
    try:
        await stop_event.wait()
    finally:
        physical_poll_task.cancel()
        network_poll_task.cancel()
        camera_poll_task.cancel()
        diagnostics_poll_task.cancel()
        await asyncio.gather(
            physical_poll_task,
            network_poll_task,
            camera_poll_task,
            diagnostics_poll_task,
            return_exceptions=True,
        )
        if portal:
            await portal.stop()
        await local_api.stop()
        if proxy_recovery_task:
            proxy_recovery_task.cancel()
            await asyncio.gather(proxy_recovery_task, return_exceptions=True)
        await proxy.stop()
        await virtualhere.stop()
        try:
            await safety.set_k1(False)
        except Exception as exc:
            LOGGER.error("failed to drop K1 during shutdown: %s", exc)
        close_gpio = getattr(gpio, "close", None)
        if close_gpio:
            close_gpio()


async def _physical_input_loop(safety: SafetyController) -> None:
    while True:
        await asyncio.sleep(0.05)
        await safety.refresh_physical_inputs()


async def _network_input_loop(state: ControllerState, network: NetworkManager, config: AppConfig, event_sink: EventLogger | None = None) -> None:
    previous_wifi = None
    previous_ip = None
    while True:
        try:
            ethernet = await network.interface_status(config.network.ethernet_interface)
            wifi = await network.interface_status(config.network.uplink_wifi_interface)
            tailscale = (
                await network.tailscale_status(config.network.tailscale_interface)
                if config.network.tailscale_enabled
                else None
            )

            def mutate(snapshot):
                snapshot.network.ethernet_connected = ethernet.connected
                snapshot.network.ethernet_ip = ethernet.ip_address
                snapshot.network.wifi_connected = wifi.connected
                snapshot.network.wifi_ssid = wifi.ssid
                snapshot.network.wifi_ip = wifi.ip_address
                if tailscale is not None:
                    snapshot.network.tailscale_connected = tailscale.connected
                    snapshot.network.tailscale_ip = tailscale.ip_address
                    snapshot.network.tailscale_status = tailscale.status

            await state.update(mutate)
            current_wifi = (wifi.connected, wifi.ssid)
            current_ip = (ethernet.ip_address, wifi.ip_address, tailscale.ip_address if tailscale else None)
            if event_sink and previous_wifi is not None and current_wifi != previous_wifi:
                if wifi.connected:
                    event_sink.emit(ControllerEvent(EventCode.WIFI_CONNECTED, Severity.INFO, "network", {"ssid": wifi.ssid}))
                else:
                    event_sink.emit(ControllerEvent(EventCode.WIFI_DISCONNECTED, Severity.WARNING, "network"))
                if previous_wifi[1] != wifi.ssid:
                    event_sink.emit(ControllerEvent(EventCode.WIFI_CHANGED, Severity.INFO, "network", {"ssid": wifi.ssid}))
            if event_sink and previous_ip is not None and current_ip != previous_ip:
                event_sink.emit(ControllerEvent(EventCode.IP_CHANGED, Severity.INFO, "network", {"ip": current_ip}))
            previous_wifi = current_wifi
            previous_ip = current_ip
        except Exception as exc:
            LOGGER.warning("network status refresh failed: %s", exc)
        await asyncio.sleep(1.0)


async def _camera_input_loop(state: ControllerState, camera: CameraAdapter, config: AppConfig, event_sink: EventLogger | None = None) -> None:
    previous_connected: bool | None = None
    while True:
        try:
            status = await camera.status()
            connected = bool(status["connected"]) if config.camera.enabled else False

            def mutate(snapshot):
                snapshot.camera.connected = connected
                snapshot.camera.stream_url = status["stream_url"] if isinstance(status["stream_url"], str) else None
                snapshot.camera.stream_type = str(status["stream_type"] or config.camera.stream_type)

            await state.update(mutate)
            if previous_connected is not None and connected != previous_connected and event_sink:
                event_sink.emit(
                    ControllerEvent(
                        EventCode.CAMERA_USB_CONNECTED if connected else EventCode.CAMERA_USB_DISCONNECTED,
                        Severity.INFO if connected else Severity.WARNING,
                        "camera",
                    )
                )
            previous_connected = connected
        except Exception as exc:
            LOGGER.warning("camera status refresh failed: %s", exc)
            if event_sink:
                event_sink.emit(ControllerEvent(EventCode.CAMERA_FAILURE, Severity.WARNING, "camera", {"error": str(exc)}))
        await asyncio.sleep(1.0)


async def _diagnostics_loop(diagnostics: DiagnosticsProvider) -> None:
    while True:
        try:
            await diagnostics.apply()
        except Exception as exc:
            LOGGER.warning("diagnostics refresh failed: %s", exc)
        await asyncio.sleep(5.0)


async def _start_proxy_when_safe(state: ControllerState, proxy: GrblProxy) -> None:
    while True:
        snapshot = await state.snapshot()
        if snapshot.physical.k1 and not proxy.active:
            try:
                await proxy.start()
            except Exception as exc:
                LOGGER.warning("laser proxy startup waiting for USB: %s", exc)
        await asyncio.sleep(1.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Travel Laser controller backend")
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--mock", action="store_true", help="use mock GPIO/serial hardware")
    args = parser.parse_args()
    asyncio.run(run(args.config, args.mock))


def _resolve_web_host(config: AppConfig, allow_unset_tailscale: bool = False) -> str | None:
    if config.web.bind_to_tailscale:
        if allow_unset_tailscale and not config.network.tailscale_ip:
            return "127.0.0.1"
        tailscale_ip = config.network.tailscale_ip or _live_tailscale_ip()
        if not tailscale_ip:
            if allow_unset_tailscale:
                return "127.0.0.1"
            return None
        return tailscale_ip
    return config.web.host or "0.0.0.0"


def _live_tailscale_ip() -> str | None:
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return next((line.strip() for line in result.stdout.splitlines() if line.strip()), None)


if __name__ == "__main__":
    main()
