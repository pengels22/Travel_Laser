from pathlib import Path

from backend.log_export import USBLogExporter


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
