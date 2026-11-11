import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "lab" / "s4" / "evidence.py"


def load_evidence_module():
    spec = importlib.util.spec_from_file_location("s4_evidence", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def event(timestamp, event_type, username, src_ip, status=200):
    return {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "username": username,
        "src_ip": src_ip,
        "details": {"status": status},
    }


def test_s4_evidence_marks_the_sixth_eligible_signal_and_ignores_429():
    evidence = load_evidence_module()
    start = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
    events = [
        *(event(start + timedelta(minutes=index), "auth.login_failed", "zz_s4", "203.0.113.24", 401)
          for index in range(5)),
        event(start + timedelta(minutes=4, seconds=30), "auth.login_failed", "zz_s4", "203.0.113.24", 429),
        event(start + timedelta(minutes=5), "auth.login_succeeded", "zz_s4", "203.0.113.24"),
        event(start + timedelta(minutes=5, seconds=7), "auth.account_locked", "zz_s4", "10.250.0.100"),
        event(start + timedelta(minutes=8), "auth.password_reset", "zz_s4", "10.250.0.200"),
        event(start + timedelta(minutes=9), "auth.login_succeeded", "zz_s4", "203.0.113.24"),
    ]

    report = evidence.evaluate(events)

    assert report == [{
        "username": "zz_s4",
        "src_ip": "203.0.113.24",
        "condition_at": "2026-11-11T01:05:00+00:00",
        "lock_at": "2026-11-11T01:05:07+00:00",
        "reset_at": "2026-11-11T01:08:00+00:00",
        "restored_login_at": "2026-11-11T01:09:00+00:00",
        "condition_to_lock_seconds": 7.0,
        "reset_to_login_seconds": 60.0,
    }]


def test_s4_evidence_rejects_five_or_fewer_eligible_signals_inside_the_window():
    evidence = load_evidence_module()
    start = datetime(2026, 11, 11, 1, 0, tzinfo=timezone.utc)
    events = [
        *(event(start + timedelta(minutes=index), "auth.login_failed", "zz_boundary", "203.0.113.25", 401)
          for index in range(4)),
        event(start + timedelta(minutes=4), "auth.login_succeeded", "zz_boundary", "203.0.113.25"),
    ]

    assert evidence.evaluate(events) == []
