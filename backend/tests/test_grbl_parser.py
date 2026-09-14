from backend.grbl_parser import parse_error_line, parse_status_line
from backend.state import MachineState


def test_parse_grbl_status_line():
    status = parse_status_line("<Run|MPos:1.000,2.000,0.000|FS:1200,255>")
    assert status is not None
    assert status.state == MachineState.RUN
    assert status.mpos == (1.0, 2.0, 0.0)
    assert status.feed == 1200
    assert status.spindle == 255


def test_parse_grbl_error_line():
    assert parse_error_line("error:9") == "error:9"
    assert parse_error_line("ok") is None

