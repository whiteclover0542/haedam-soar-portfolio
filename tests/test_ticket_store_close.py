import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/ticket-store"))
from ticket_store import core, db  # noqa: E402

T0, T1, T2 = "2026-11-12T01:00:00+00:00", "2026-11-12T01:00:05+00:00", "2026-11-12T01:05:00+00:00"


def action(name, via, bot, target, result="applied", effect=None, effect_at=None):
    return {"bot": bot, "target": target, "via": via, "action": name, "result": result, "applied_verified": None,
            "effect_verified": effect, "requested_at": T0, "finished_at": T1, "effect_verified_at": effect_at,
            "n8n_execution_id": "1"}


def record(conn, case, group, stage, act, key, seat="C"):
    body = {"seat": seat, "case_id": case, "group_key": group, "stage": stage, "title": case, "asset_id": "haedam-portal",
            "src_ip": None, "username": None, "event_ids": [key], "action": act}
    return core.record(conn, body, key)[1]


def test_s7_restore_is_one_shot_so_a_hash_verified_ticket_can_close():
    # The Wazuh restore is the fix itself; nothing is left to undo, so it must not hold the ticket open forever.
    conn = db.connect(":memory:")
    tid = record(conn, "S7", "haedam-portal:index.html", "applied", action("restore", "wazuh-ar", "117", "index.html"),
                 "s7-applied-1")["ticket_id"]
    record(conn, "S7", "haedam-portal:index.html", "effect",
           action("restore", "wazuh-ar", "117", "index.html", effect=True, effect_at=T2), "s7-effect-1")
    assert db.get_ticket(conn, tid)["status"] == "verified"
    assert not db.dashboard_has_active(conn, tid)
    assert db.close_ticket(conn, tid, "hash verified")["status"] == "closed"


def test_a_live_block_still_keeps_a_verified_ticket_open():
    conn = db.connect(":memory:")
    tid = record(conn, "H2", "zz_a_h2", "applied", action("lock", "portal", "111", "zz_a_h2"), "h2-applied-1")["ticket_id"]
    record(conn, "H2", "zz_a_h2", "effect", action("lock", "portal", "111", "zz_a_h2", effect=True, effect_at=T2), "h2-effect-1")
    assert db.dashboard_has_active(conn, tid)
    with pytest.raises(db.InvalidTransition):
        db.close_ticket(conn, tid, "should refuse")
