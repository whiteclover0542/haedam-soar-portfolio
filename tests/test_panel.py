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
    assert "pending" not in current["H3"] and panel.EXPECT["H3"][0] == "401"
    assert "pending" not in current["S4"] and panel.EXPECT["S4"][0] == "401"
    assert "pending" not in current["S12"] and panel.EXPECT["S12"][0] == "403"
    for case in ("S7",):
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


def test_h2_effect_checks_victim_petition_with_portal_view_contract(monkeypatch):
    panel.USERS["H2"] = {
        "user": "attacker", "pw": "pw-a", "victim": "victim", "victim_pw": "pw-v", "foreign_ids": [41],
    }
    calls = []

    def portal(container, source, mode, username, *values, pw=None):
        calls.append((container, source, mode, username, values))
        return {"statuses": [200]}

    monkeypatch.setattr(panel, "portal_login", portal)
    monkeypatch.setattr(panel, "http_code", lambda *_: "403")

    result = panel.h2_effect()

    assert result[0]["result"] == "403"
    assert result[1]["result"] == "200"
    assert ("haedam-normal", panel.NORMAL, "view", "victim", ("--ids=41",)) in calls


def test_h2_release_resets_the_locked_account_before_releasing_again(monkeypatch):
    panel.USERS["H2"] = {"user": "attacker", "pw": "old", "user_id": 7, "foreign_ids": [41]}
    verdicts = iter([{"verdict": "released", "manual_required": ["111:portal:lock:attacker"]},
                     {"verdict": "released", "steps": [{"step": 2, "result": "released"}]}])
    resets = []
    monkeypatch.setattr(panel, "latest_ticket", lambda case: {"case_id": "H2"})
    monkeypatch.setattr(panel, "release_webhook", lambda case, case_id: next(verdicts))
    monkeypatch.setattr(panel, "portal_reset", lambda e, user_id, pw: resets.append(user_id) or "200")
    monkeypatch.setattr(panel, "env", lambda: {})
    monkeypatch.setattr(panel, "http_code", lambda *_: "200")
    monkeypatch.setattr(panel, "portal_login", lambda *a, pw=None: {"statuses": [403]})

    log = panel.release("H2")

    assert resets == [7] and panel.USERS["H2"]["pw"] != "old"
    assert [x["result"] for x in log] == [["111:portal:lock:attacker"], "200", ["포털 released"], "200", [403]]


def test_h1_and_h3_release_close_the_ticket_through_the_release_webhook(monkeypatch):
    # Without haedam-50 the block lifts but the ticket stays responding and no restore card goes out.
    panel.USERS["H1"] = {"user": "zz_a_h1_x", "pw": "pw"}
    panel.USERS["H3"] = {"user": "zz_h3_staff_x"}
    order = []
    monkeypatch.setattr(panel, "latest_ticket", lambda case: {"case_id": case})
    monkeypatch.setattr(panel, "release_webhook", lambda case, case_id: order.append(("webhook", case)) or {"verdict": "released"})
    monkeypatch.setattr(panel.h3, "unlock", lambda run: order.append(("unlock", "H3")) or 200)
    monkeypatch.setattr(panel, "portal_login", lambda *a, pw=None: {"statuses": [201]})

    assert panel.release("H1")[0]["result"] == "released"
    assert panel.release("H3")[1]["result"] == "released"
    assert order == [("webhook", "H1"), ("unlock", "H3"), ("webhook", "H3")]   # H3: unlock first, or the webhook holds
    assert panel.SEAT["H3"] == "C"
