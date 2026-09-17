from pathlib import Path


def test_clickable_walkthrough_tracks_primary_touchscreen_workflows() -> None:
    walkthrough = Path("dev/touchscreen-walkthrough.html").read_text(encoding="utf-8")

    for label in ("Home", "Status", "Net", "Mode", "System", "HOME", "STOP", "E-stop"):
        assert label.lower() in walkthrough.lower()
    for workflow in ("keyboard", "network/connect", "network/forget", "mode", "system:"):
        assert workflow in walkthrough
