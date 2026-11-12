import importlib.util
from pathlib import Path


PANEL_PATH = Path(__file__).resolve().parents[1] / "lab" / "panel.py"
SPEC = importlib.util.spec_from_file_location("practice_panel", PANEL_PATH)
panel = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(panel)


def test_state_orders_connected_cases_including_s7(monkeypatch):
    monkeypatch.setattr(panel, "timeline", lambda case: {"steps": [], "elapsed": None})

    current = panel.state()

    assert list(current) == ["H1", "H2", "H3", "H4", "S1", "S4", "S7", "S8", "S10", "S12"]
    assert "pending" not in current["H3"] and panel.EXPECT["H3"][0] == "401"
    assert "pending" not in current["S4"] and panel.EXPECT["S4"][0] == "401"
    assert "pending" not in current["S12"] and panel.EXPECT["S12"][0] == "403"
    s7 = current["S7"]
    assert "pending" not in s7
    assert s7["src"] == "haedam-portal:/app/dist"


def test_s7_timeline_starts_with_the_same_six_panel_steps():
    panel.RUNS.pop("S7", None)

    current = panel.s7_timeline()

    assert [step["name"] for step in current["steps"]] == [
        "① 기준 파일 변조", "② Wazuh FIM 경보", "③ Graylog 전달·분류",
        "④ 탐지·자동 복구 (n8n → Wazuh AR)", "⑤ 효과: 원본 해시로 복구", "⑥ 기준 해시 전체 검증",
    ]
    assert {step["state"] for step in current["steps"]} == {"idle"}


def test_s7_verify_reads_the_json_line_before_a_plain_status(monkeypatch):
    monkeypatch.setattr(panel.s7, "sh", lambda *args, **kw: '{"action":"verify","result":"ok"}\nok')

    assert panel.s7.verify() == "ok"


def test_s7_assess_needs_restore_hash_portal_and_permission():
    run = {"actions": [("wazuh-ar", "restore", "applied", "2026-11-11T17:51:50Z")],
           "effect": {"attacker": "baseline_hash", "normal": "200"},
           "restore": {"attacker_after": "200", "verify": "ok", "permission_enforced": True}}
    assert panel.s7.assess(run) == "pass"
    assert panel.s7.assess({**run, "effect": {"attacker": "tampered", "normal": "200"}}) == "fail"
    assert panel.s7.assess({**run, "actions": [("wazuh-ar", "restore", "failed", None)]}) == "fail"
    assert panel.s7.assess({**run, "restore": {**run["restore"], "permission_enforced": False}}) == "fail"


def test_h1_is_connected_and_expects_posting_refused(monkeypatch):
    monkeypatch.setattr(panel, "timeline", lambda case: {"steps": [], "elapsed": None})

    assert "pending" not in panel.state()["H1"]
    assert panel.EXPECT["H1"][0] == "429" and panel.NORMAL_OK["H1"] == "201"


def test_h2_is_connected_like_h1_and_uses_the_same_reversible_response_path(monkeypatch):
    monkeypatch.setattr(panel, "timeline", lambda case: {"steps": [], "elapsed": None})

    h2 = panel.state()["H2"]

    assert "pending" not in h2
    assert panel.SRC["H2"] != panel.SRC["H1"]   # own source, so H1 runs never eat H2's login budget
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


def test_h4_assess_needs_lock_refusal_citizen_restore_and_permission():
    run = {"actions": [("portal", "lock", "applied", "2026-11-11T18:45:31Z")],
           "effect": {"attacker": "401", "normal": "200"},
           "restore": {"attacker_after": "200", "status_after": "restored", "permission_enforced": True}}
    assert panel.h4.assess(run) == "pass"
    assert panel.h4.assess({**run, "actions": []}) == "fail"  # locked but not recorded (the pre-fix run)
    assert panel.h4.assess({**run, "effect": {"attacker": "200", "normal": "200"}}) == "fail"
    assert panel.h4.assess({**run, "restore": {**run["restore"], "status_after": "open"}}) == "fail"


def test_s7_release_marks_open_restores_verified_only_after_the_hash_check_passes(monkeypatch):
    # S7 has nothing to unblock: once the web root matches the baseline, the open S7 tickets get the effect
    # record (status verified) so a person can close them; a mismatch must not mark anything.
    tickets = {"T-1": {"ticket_id": "T-1", "case_id": "S7", "actions": [
        {"via": "wazuh-ar", "action": "restore", "result": "applied", "effect_verified": None},
        {"via": "wazuh-ar", "action": "restore", "result": "applied", "effect_verified": True}]}}
    monkeypatch.setattr(panel, "get", lambda url: {"items": [{"ticket_id": "T-1", "case_id": "S7"}, {"ticket_id": "T-2", "case_id": "H1"}]}
                        if "status=" in url else {"ticket": tickets[url.rsplit("/", 1)[1]]})
    sent = []
    monkeypatch.setattr(panel, "s7_record_verified", lambda t, a: sent.append(t["ticket_id"]) or "201")

    monkeypatch.setattr(panel.s7, "verify", lambda: "mismatch")
    assert len(panel.s7_release()) == 1 and sent == []
    monkeypatch.setattr(panel.s7, "verify", lambda: "ok")
    assert [x["result"] for x in panel.s7_release()] == ["ok", "201"] and sent == ["T-1"]
