import importlib.util
from pathlib import Path


PATH = Path(__file__).resolve().parents[1] / "lab" / "h3" / "input.py"


def load_module():
    spec = importlib.util.spec_from_file_location("h3_input", PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_h3_preflight_plan_is_data_only_and_requires_three_updates():
    h3 = load_module()

    plan = h3.build_plan("zz_h3_staff", [101, 102, 103])

    assert plan["live_request"] is False
    assert plan["case_id"] == "H3"
    assert plan["staff_username"] == "zz_h3_staff"
    assert plan["petition_ids"] == [101, 102, 103]
    assert plan["required_updates"] == 3
