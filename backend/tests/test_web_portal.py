from pathlib import Path

from backend.gpio import MockGPIOBackend
from backend.grbl_proxy import GrblProxy
from backend.safety import SafetyController
from backend.state import ControllerState
from backend.web_portal import WebPortal


async def test_web_portal_root_serves_index(tmp_path: Path) -> None:
    static_dir = tmp_path / "web"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html></html>")
    state = ControllerState()
    safety = SafetyController(state, MockGPIOBackend())
    portal = WebPortal(
        state,
        safety,
        GrblProxy(state, safety, port=0),
        static_dir,
        "127.0.0.1",
        0,
    )

    response = await portal._index(None)

    assert response._path == static_dir / "index.html"
