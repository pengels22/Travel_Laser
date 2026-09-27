from backend.camera import CameraAdapter
from backend.config import USBIdentity
from backend.usb import USBDevice, USBDeviceManager, device_from_pyudev, matches_identity


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


async def test_camera_status_uses_configured_device_path(tmp_path):
    device = tmp_path / "video-camera"
    device.touch()
    camera = CameraAdapter(device_path=str(device), identity=USBIdentity(serial="MISSING"), device_provider=lambda: [])

    status = await camera.status()

    assert status["connected"] is True
    assert status["device_path"] == str(device)


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


def test_usb_device_from_pyudev_prefers_nearest_parent_properties():
    class FakeDevice:
        def __init__(self, properties, parent=None):
            self.properties = properties
            self.parent = parent

    root_hub = FakeDevice(
        {
            "ID_VENDOR_ID": "1d6b",
            "ID_MODEL_ID": "0001",
            "ID_SERIAL_SHORT": "root",
            "ID_MODEL": "root hub",
        }
    )
    usb_device = FakeDevice(
        {
            "ID_VENDOR_ID": "1a86",
            "ID_MODEL_ID": "7523",
            "ID_SERIAL_SHORT": "LASER1",
            "ID_MODEL": "USB_Serial",
        },
        root_hub,
    )
    tty = FakeDevice({"SUBSYSTEM": "tty"}, usb_device)

    device = device_from_pyudev("/dev/ttyUSB0", tty)

    assert device.vid == "1a86"
    assert device.pid == "7523"
    assert device.serial == "LASER1"
    assert device.description == "USB_Serial"


def test_usb_device_description_combines_database_and_model_names():
    class FakeDevice:
        def __init__(self, properties, parent=None):
            self.properties = properties
            self.parent = parent

    device = device_from_pyudev(
        "/dev/ttyUSB0",
        FakeDevice(
            {
                "ID_VENDOR_ID": "1a86",
                "ID_MODEL_ID": "7523",
                "ID_MODEL_FROM_DATABASE": "CH340 serial converter",
                "ID_MODEL": "USB_Serial",
            }
        ),
    )

    assert device.description == "CH340 serial converter USB_Serial"


def test_usb_identity_match_tolerates_numeric_pid():
    device = USBDevice(path="/dev/ttyUSB0", vid="1a86", pid="7523", description="USB_Serial")

    assert matches_identity(device, USBIdentity(pid=7523))
