#!/usr/bin/env python3
"""Summarise saved S4 portal events without contacting a service.

The input is a copied JSONL evidence file. This module never opens a socket,
starts Docker, or changes Graylog, n8n, portal, account, or ticket state.
"""

import json
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path


WINDOW = timedelta(minutes=10)
REQUIRED_SIGNALS = 6


def _timestamp(event: dict) -> datetime:
    return datetime.fromisoformat(event["timestamp"])


def _status(event: dict):
    return event.get("details", {}).get("status", event.get("status"))


def _signal_kind(event: dict):
    if event.get("event_type") == "auth.login_failed" and _status(event) == 401:
        return "failed"
    if event.get("event_type") == "auth.login_succeeded" and _status(event) == 200:
        return "succeeded"
    return None


def _iso(value):
    return value.isoformat() if value else None


def _first_after(events, event_type, username, after, src_ip=None):
    for event in events:
        if event.get("event_type") != event_type or event.get("username") != username:
            continue
        if src_ip is not None and event.get("src_ip") != src_ip:
            continue
        if _timestamp(event) > after:
            return _timestamp(event)
    return None


def evaluate(events: list[dict]) -> list[dict]:
    """Return S4 rounds found in saved events, ordered by condition time."""
    ordered = sorted(events, key=_timestamp)
    windows = defaultdict(deque)
    rounds = []
    seen = set()

    for event in ordered:
        kind = _signal_kind(event)
        username, src_ip = event.get("username"), event.get("src_ip")
        if not kind or not username or not src_ip:
            continue
        key = (username, src_ip)
        window = windows[key]
        occurred_at = _timestamp(event)
        window.append((occurred_at, kind))
        while occurred_at - window[0][0] > WINDOW:
            window.popleft()
        if key in seen or len(window) < REQUIRED_SIGNALS or {item[1] for item in window} != {"failed", "succeeded"}:
            continue

        seen.add(key)
        lock_at = _first_after(ordered, "auth.account_locked", username, occurred_at)
        reset_at = _first_after(ordered, "auth.password_reset", username, lock_at) if lock_at else None
        restored_at = _first_after(ordered, "auth.login_succeeded", username, reset_at, src_ip) if reset_at else None
        rounds.append({
            "username": username,
            "src_ip": src_ip,
            "condition_at": _iso(occurred_at),
            "lock_at": _iso(lock_at),
            "reset_at": _iso(reset_at),
            "restored_login_at": _iso(restored_at),
            "condition_to_lock_seconds": round((lock_at - occurred_at).total_seconds(), 3) if lock_at else None,
            "reset_to_login_seconds": round((restored_at - reset_at).total_seconds(), 3) if restored_at else None,
        })
    return rounds


def load_jsonl(path: Path) -> list[dict]:
    """Load a local evidence file; blank lines are ignored."""
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Summarise a saved S4 portal-event JSONL file")
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(load_jsonl(args.evidence)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
