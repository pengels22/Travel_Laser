from pathlib import Path

from backend.log_export import USBLogExporter, _usb_partition_candidates_from_lsblk


class MockExporter(USBLogExporter):
    def __init__(self, mount: Path, source: Path) -> None:
        super().__init__(str(source))
        self.mount = mount

    async def _find_usb_mount(self) -> Path | None:
        return self.mount


async def test_log_export_creates_unique_directory_and_copies_available_logs(tmp_path: Path) -> None:
    source = tmp_path / "logs"
    source.mkdir()
    (source / "events.jsonl").write_text("event\n", encoding="utf-8")
    mount = tmp_path / "usb"
    mount.mkdir()

    destination = Path(await MockExporter(mount, source).export())

    assert destination.parent == mount
    assert destination.name.startswith("Travel_Laser_Logs_")
    assert (destination / "events.jsonl").read_text(encoding="utf-8") == "event\n"
    assert (destination / "system-info.txt").exists()


async def test_log_export_reports_missing_drive(tmp_path: Path) -> None:
    exporter = MockExporter(tmp_path, tmp_path / "missing")
    exporter.mount = None

    try:
        await exporter.export()
    except RuntimeError as exc:
        assert "No writable USB" in str(exc)
    else:
        raise AssertionError("expected missing USB export to fail")


def test_usb_partition_detection_accepts_usb_parent_transport() -> None:
    output = "\n".join(
        [
            'NAME="sda" TYPE="disk" TRAN="usb" SIZE="8053063680" PKNAME=""',
            'NAME="sda1" TYPE="part" TRAN="" SIZE="8052015104" PKNAME="sda"',
            'NAME="mmcblk0" TYPE="disk" TRAN="" SIZE="31914983424" PKNAME=""',
            'NAME="mmcblk0p1" TYPE="part" TRAN="" SIZE="31800000000" PKNAME="mmcblk0"',
        ]
    )

    assert _usb_partition_candidates_from_lsblk(output) == ["sda1"]


def test_usb_partition_detection_rejects_small_usb_partitions() -> None:
    output = "\n".join(
        [
            'NAME="sda" TYPE="disk" TRAN="usb" SIZE="100000000" PKNAME=""',
            'NAME="sda1" TYPE="part" TRAN="" SIZE="100000000" PKNAME="sda"',
        ]
    )

    assert _usb_partition_candidates_from_lsblk(output) == []
