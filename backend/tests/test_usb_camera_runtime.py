from backend.camera import CameraAdapter
from backend.config import USBIdentity
from backend.usb import USBDevice, USBDeviceManager


def _devices():
    return [
        USBDevice(path="/dev/ttyACM-laser", vid="1a86", pid="7523", serial="LASER1", description="GRBL"),
        USBDevice(path="/dev/video-camera", vid="046d", pid="0825", serial="CAM1", description="USB Camera"),
    ]


async def test_usb_manager_enumerates_laser_and_camera_by_identity():
    manager = USBDeviceManager(
        USBIdentity(vid="1a86", serial="LASER1"),
        USBIdentity(description_contains="camera"),
        device_provider=_devices,
    )

    await manager.refresh()

    assert manager.current_laser_device().path == "/dev/ttyACM-laser"
    assert manager.current_camera_device().path == "/dev/video-camera"


async def test_camera_status_uses_configured_identity_without_crashing_when_absent():
    camera = CameraAdapter(
        stream_url="http://127.0.0.1:8889/cam",
        identity=USBIdentity(serial="MISSING"),
        device_provider=_devices,
    )

    status = await camera.status()

    assert status["connected"] is False
    assert status["stream_url"] == "http://127.0.0.1:8889/cam"


async def test_camera_status_reports_present_device():
    camera = CameraAdapter(identity=USBIdentity(serial="CAM1"), device_provider=_devices)

    status = await camera.status()

    assert status["connected"] is True
    assert status["device_path"] == "/dev/video-camera"
