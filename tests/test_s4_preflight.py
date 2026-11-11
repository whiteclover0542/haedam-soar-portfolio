import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = ROOT / "lab" / "s4" / "preflight.py"


def load_preflight_module():
    spec = importlib.util.spec_from_file_location("s4_preflight", PREFLIGHT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_s4_preflight_keeps_the_case_offline_until_both_live_imports_are_explicitly_enabled():
    preflight = load_preflight_module()

    report = preflight.review()

    assert report["case_id"] == "S4"
    assert report["execution"] is False
    assert report["ready_for_live_import"] is False
    assert report["checks"] == {
        "offline_input": True,
        "graylog_definition": True,
        "workflow_inactive": True,
        "workflow_dry_run": True,
        "graylog_not_bootstrapped": True,
        "n8n_not_loaded": True,
    }
