from backend.camera import CameraAdapter
from backend.config import AppConfig, USBIdentity
from backend.diagnostics import DiagnosticsProvider
from backend.gpio import MockGPIOBackend
from backend.network_manager import NetworkInterfaceStatus, NetworkManager, TailscaleStatus
from backend.state import ControllerState
from backend.usb import USBDevice
from backend.virtualhere import VirtualHereService


class MockNetwork(NetworkManager):
    async def interface_status(self, interface: str) -> NetworkInterfaceStatus:
        return NetworkInterfaceStatus(interface=interface, connected=True, ip_address="192.0.2.10")

    async def tailscale_status(self, interface: str = "tailscale0") -> TailscaleStatus:
        return TailscaleStatus(True, "100.64.1.2", "connected")


def _devices():
    return [
        USBDevice(path="/dev/ttyACM0", vid="1a86", pid="7523", serial="LASER1", description="GRBL"),
        USBDevice(path="/dev/video0", vid="046d", pid="0825", serial="CAM1", description="USB Camera"),
    ]


async def test_diagnostics_provider_maps_runtime_state_and_usb_devices():
    config = AppConfig()
    config.laser.usb = USBIdentity(serial="LASER1")
    config.camera.usb = USBIdentity(serial="CAM1")
    state = ControllerState()
    gpio = MockGPIOBackend(power_sense=True)
    camera = CameraAdapter(identity=config.camera.usb, device_provider=_devices)
    provider = DiagnosticsProvider(
        config,
        state,
        gpio,
        MockNetwork(dry_run=True),
        camera,
        VirtualHereService(dry_run=True),
        device_provider=_devices,
    )

    await provider.apply()
    snapshot = await state.snapshot()

    assert snapshot.diagnostics.gpio_status == "initialized"
    assert snapshot.diagnostics.laser_usb["serial"] == "LASER1"
    assert snapshot.diagnostics.camera_usb["serial"] == "CAM1"
    assert snapshot.diagnostics.network["tailscale"]["ip_address"] == "100.64.1.2"


async def test_diagnostics_uses_configured_camera_device_path(tmp_path):
    camera_node = tmp_path / "video1"
    camera_node.touch()
    by_id = tmp_path / "usb-camera-video-index0"
    by_id.symlink_to(camera_node)

    config = AppConfig()
    config.camera.device = str(by_id)
    config.camera.usb = USBIdentity(vid="0c45", pid="6366")
    state = ControllerState()
    gpio = MockGPIOBackend(power_sense=True)

    def devices():
        return [
            USBDevice(path=str(camera_node), vid="0c45", pid="6366", serial="SN0001", description="USB Camera"),
            USBDevice(path=str(tmp_path / "video2"), vid="0c45", pid="6366", serial="SN0001", description="USB Camera"),
        ]

    provider = DiagnosticsProvider(
        config,
        state,
        gpio,
        MockNetwork(dry_run=True),
        CameraAdapter(device_path=str(by_id), identity=config.camera.usb, device_provider=devices),
        VirtualHereService(dry_run=True),
        device_provider=devices,
    )

    diagnostics = await provider.collect()

    assert diagnostics["camera_usb"]["path"] == str(camera_node)
