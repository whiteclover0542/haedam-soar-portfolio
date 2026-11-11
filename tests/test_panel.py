import importlib.util
from pathlib import Path


PANEL_PATH = Path(__file__).resolve().parents[1] / "lab" / "panel.py"
SPEC = importlib.util.spec_from_file_location("practice_panel", PANEL_PATH)
panel = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(panel)


def test_state_orders_connected_and_unconnected_cases_without_running_unconnected_cases(monkeypatch):
    monkeypatch.setattr(panel, "timeline", lambda case: {"steps": [], "elapsed": None})

    current = panel.state()

    assert list(current) == ["H1", "H2", "H3", "S1", "S4", "S7", "S8", "S10", "S12"]
    for case in ("H3", "S4", "S7", "S12"):
        assert current[case]["pending"] is True
        assert current[case]["steps"][0]["state"] == "wait"


def test_h1_is_connected_and_expects_posting_refused(monkeypatch):
    monkeypatch.setattr(panel, "timeline", lambda case: {"steps": [], "elapsed": None})

    assert "pending" not in panel.state()["H1"]
    assert panel.EXPECT["H1"][0] == "429" and panel.NORMAL_OK["H1"] == "201"


def test_h2_is_connected_like_h1_and_uses_the_same_reversible_response_path(monkeypatch):
    monkeypatch.setattr(panel, "timeline", lambda case: {"steps": [], "elapsed": None})

    h2 = panel.state()["H2"]

    assert "pending" not in h2
    assert panel.SRC["H2"] == panel.SRC["H1"]
    assert panel.EXPECT["H2"][0] == "403"
    assert panel.NORMAL_OK["H2"] == "200"
