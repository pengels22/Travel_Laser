from backend.camera import CameraAdapter
from backend.config import USBIdentity
from backend.usb import USBDevice, USBDeviceManager, device_from_pyudev


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


def test_usb_device_from_pyudev_walks_parent_properties():
    class FakeDevice:
        def __init__(self, properties, parent=None):
            self.properties = properties
            self.parent = parent

    parent = FakeDevice(
        {
            "ID_VENDOR_ID": "1a86",
            "ID_MODEL_ID": "7523",
            "ID_MODEL": "USB_Serial",
            "ID_SERIAL_SHORT": "LASER1",
        }
    )
    child = FakeDevice({"SUBSYSTEM": "tty"}, parent)

    device = device_from_pyudev("/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0", child)

    assert device.vid == "1a86"
    assert device.pid == "7523"
    assert device.serial == "LASER1"
    assert device.description == "USB_Serial"
