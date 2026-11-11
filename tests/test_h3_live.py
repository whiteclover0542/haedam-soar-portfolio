import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "lab" / "h3" / "live.py"


def load_module():
    spec = importlib.util.spec_from_file_location("h3_live", PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_h3_run_passes_only_when_lock_snapshot_restore_and_manual_unlock_all_verify():
    h3 = load_module()

    result = h3.assess({"actions": [{"action": "lock", "result": "applied"}]}, {
        "restored_status": "received",
        "owner_detail": 200,
        "locked_staff_login": 401,
        "unlocked_staff_login": 200,
    })

    assert result == "pass"


def test_h3_run_fails_when_the_ticket_has_no_applied_lock():
    h3 = load_module()

    result = h3.assess({"actions": []}, {
        "restored_status": "received",
        "owner_detail": 200,
        "locked_staff_login": 401,
        "unlocked_staff_login": 200,
    })

    assert result == "fail"
