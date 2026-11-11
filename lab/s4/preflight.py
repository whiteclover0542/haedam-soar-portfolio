#!/usr/bin/env python3
"""Check the S4 blueprint without contacting Docker, Graylog, n8n, or the portal."""

import ast
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = ROOT / "lab" / "s4" / "input.py"
DEFINITION_PATH = ROOT / "lab" / "s1s4" / "graylog" / "s4-fail-then-success.json"
WORKFLOW_PATH = ROOT / "infra" / "n8n" / "workflows" / "haedam-31-s4-main.json"
BOOTSTRAP_PATH = ROOT / "infra" / "graylog" / "bootstrap.py"
N8N_LOAD_PATH = ROOT / "infra" / "n8n" / "load.py"


def _load_input():
    spec = importlib.util.spec_from_file_location("s4_input_preflight", INPUT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in statement.targets
        ):
            return ast.literal_eval(statement.value)
    raise ValueError(f"{name} assignment not found in {path}")


def review() -> dict:
    """Return the S4 static readiness report without making a live request."""
    plan = _load_input().build_plan("zz_s4_preflight", "203.0.113.22")
    definition = json.loads(DEFINITION_PATH.read_text(encoding="utf-8"))
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))[0]
    workflow_code = "\n".join(node.get("parameters", {}).get("jsCode", "") for node in workflow["nodes"])
    definitions = _literal_assignment(BOOTSTRAP_PATH, "DEFINITIONS")
    scope = _literal_assignment(N8N_LOAD_PATH, "SCOPE")

    checks = {
        "offline_input": plan["live_request"] is False and len(plan["events"]) == 6,
        "graylog_definition": (
            definition["key_spec"] == ["username", "src_ip"]
            and definition["config"]["search_within_ms"] == 600000
            and definition["config"]["conditions"]["expression"]["expr"] == "&&"
        ),
        "workflow_inactive": workflow["active"] is False,
        "workflow_dry_run": "dry_run: true" in workflow_code,
        "graylog_not_bootstrapped": str(DEFINITION_PATH.relative_to(ROOT)).replace("\\", "/") not in definitions,
        "n8n_not_loaded": workflow["id"] not in scope,
    }
    return {
        "case_id": "S4",
        "execution": False,
        "checks": checks,
        "ready_for_live_import": all(checks.values()) and not (
            checks["graylog_not_bootstrapped"] or checks["n8n_not_loaded"]
        ),
    }


if __name__ == "__main__":
    print(json.dumps(review(), ensure_ascii=False, indent=2))
