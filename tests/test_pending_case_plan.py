import importlib.util
from pathlib import Path


PLAN_PATH = Path(__file__).resolve().parents[1] / "lab" / "pending_case_plan.py"
SPEC = importlib.util.spec_from_file_location("pending_case_plan", PLAN_PATH)
plans = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(plans)


def test_remaining_cases_have_non_executing_plans_with_required_inputs():
    expected = {
        "H3": {"staff_username", "petition_ids"},
        "S4": {"username", "source_ip"},
        "S7": {"asset_id", "file_key"},
        "S12": {"source_ip", "duration_seconds"},
    }

    for case_id, required in expected.items():
        plan = plans.build_plan(case_id)
        assert plan["case_id"] == case_id
        assert plan["execution"] is False
        assert set(plan["required_inputs"]) == required
        assert plan["preconditions"]
