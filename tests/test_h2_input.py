import importlib.util
from pathlib import Path


INPUT_PATH = Path(__file__).resolve().parents[1] / "lab" / "h2" / "input.py"
SPEC = importlib.util.spec_from_file_location("h2_input", INPUT_PATH)
input_tool = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(input_tool)


def test_h2_plan_creates_three_distinct_denied_detail_requests():
    plan = input_tool.build_plan("attacker", [101, 102, 103])

    assert plan["username"] == "attacker"
    assert plan["petition_ids"] == [101, 102, 103]
    assert plan["expected_statuses"] == [403, 403, 403]
    assert [request["path"] for request in plan["requests"]] == [
        "/api/v1/petitions/101",
        "/api/v1/petitions/102",
        "/api/v1/petitions/103",
    ]


def test_run_h2_creates_three_foreign_denials_and_a_self_check():
    calls = []

    def portal(container, source, mode, username, *values, pw=None):
        calls.append((container, source, mode, username, values))
        if mode == "register":
            return {"statuses": [201]}
        if mode == "post" and username == "victim":
            # portal_login.py returns created petition identifiers under ``ids``.
            return {"statuses": [201, 201, 201], "ids": [41, 42, 43]}
        if mode == "post":
            return {"statuses": [201], "ids": [44]}
        if mode == "view":
            assert len(values) == 1
            ids = values[0].removeprefix("--ids=").split(",")
            return {"login": 200, "statuses": [403, 403, 403] if len(ids) == 3 else [200]}
        raise AssertionError(mode)

    run = input_tool.run_h2(
        portal, attacker="attacker", attacker_password="pw-a", victim="victim", victim_password="pw-v"
    )

    assert run["statuses"] == [403, 403, 403]
    assert run["own_status"] == 200
    assert run["victim_petition_ids"] == [41, 42, 43]
    assert ("haedam-attacker", "203.0.113.11", "view", "attacker", ("--ids=41,42,43",)) in calls
