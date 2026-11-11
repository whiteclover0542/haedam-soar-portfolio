import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "lab" / "s4" / "input.py"
WORKFLOW_PATH = ROOT / "infra" / "n8n" / "workflows" / "haedam-31-s4-main.json"


def load_input_module():
    spec = importlib.util.spec_from_file_location("s4_input", INPUT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_s4_offline_plan_has_five_failures_then_one_success_for_one_identity():
    s4 = load_input_module()

    plan = s4.build_plan(username="zz_s4_test", src_ip="203.0.113.22")

    assert plan["live_request"] is False
    assert [(event["rule"], event["status"]) for event in plan["events"]] == [
        ("login-bruteforce", 401),
        ("login-bruteforce", 401),
        ("login-bruteforce", 401),
        ("login-bruteforce", 401),
        ("login-bruteforce", 401),
        ("login-success", 200),
    ]
    assert {(event["username"], event["src_ip"]) for event in plan["events"]} == {
        ("zz_s4_test", "203.0.113.22")
    }


def test_s4_workflow_is_inactive_and_defaults_to_dry_run():
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))[0]
    code = "\n".join(node.get("parameters", {}).get("jsCode", "") for node in workflow["nodes"])
    serialized = json.dumps(workflow, ensure_ascii=False)

    assert workflow["active"] is False
    assert "dry_run: true" in code
    assert "haedamAccountLock01" in serialized
