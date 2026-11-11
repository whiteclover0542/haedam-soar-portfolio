#!/usr/bin/env python3
"""Run one isolated H3 integrity-response verification on the local portal.

It creates only timestamped zz_ accounts and their petitions.  It never prints
passwords, cookies, response keys, or request bodies.  A failed live round
attempts an administrator unlock so a test staff account is not left locked.
"""

import argparse
import sys
import http.cookiejar
import json
import secrets
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.run_ticket import RESPONSE_ACTIONS, mttd, ts  # noqa: E402
PORTAL = "http://127.0.0.1:8080/api/v1"
TICKETS = "http://127.0.0.1:8089/api/v1/tickets"


def assess(ticket: dict, checks: dict) -> str:
    """Classify a round only when every H3 protection and recovery proof exists."""
    locked = any(action.get("action") == "lock" and action.get("result") in {"applied", "already_applied"}
                 for action in ticket.get("actions", []))
    return "pass" if locked and checks == {
        "restored_status": "received", "owner_detail": 200,
        "locked_staff_login": 401, "unlocked_staff_login": 200,
    } else "fail"


def settings() -> dict:
    pairs = (line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
             if "=" in line and not line.lstrip().startswith("#"))
    return {key.strip(): value.strip() for key, value in pairs}


class Portal:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.csrf = None

    def call(self, method: str, path: str, data=None):
        payload = None if data is None else json.dumps(data).encode()
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        if self.csrf:
            headers["X-CSRF-Token"] = self.csrf
        request = urllib.request.Request(PORTAL + path, data=payload, method=method, headers=headers)
        try:
            with self.opener.open(request, timeout=15) as response:
                code, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            code, raw = error.code, error.read()
        body = json.loads(raw) if raw else {}
        if code < 400 and isinstance(body.get("data"), dict) and body["data"].get("csrf_token"):
            self.csrf = body["data"]["csrf_token"]
        return code, body

    def login(self, username: str, password: str) -> int:
        self.call("GET", "/auth/me")
        code, _ = self.call("POST", "/auth/login", {"username": username, "password": password})
        return code


def must(code, expected, label):
    if code != expected:
        raise RuntimeError(f"{label}: expected {expected}, got {code}")


def new_ticket(username: str, before: set[str], timeout=390):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        with urllib.request.urlopen(f"{TICKETS}?limit=200", timeout=10) as response:
            tickets = json.loads(response.read())["items"]
        for item in tickets:
            if item.get("group_key") == username and item["ticket_id"] not in before:
                with urllib.request.urlopen(f"{TICKETS}/{item['ticket_id']}", timeout=10) as response:
                    return json.loads(response.read())["ticket"]
        time.sleep(5)
    return None


def manipulate(updates: int = 3) -> dict:
    """Create fresh zz_ staff/owner accounts and three petitions; the staff changes the first `updates` of them."""
    now = datetime.now(timezone.utc).strftime("%m%d%H%M%S")
    staff_name, owner_name = f"zz_h3_staff_{now}", f"zz_h3_owner_{now}"
    staff_password, owner_password = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
    config = settings()
    admin = Portal()
    must(admin.login(config["PORTAL_ADMIN_USERNAME"], config["PORTAL_ADMIN_PASSWORD"]), 200, "admin login")
    code, staff = admin.call("POST", "/admin/users", {
        "username": staff_name, "display_name": "H3 test staff", "password": staff_password,
        "role": "staff", "department": "민원행정과",
    })
    must(code, 201, "staff create")
    code, _ = admin.call("POST", "/admin/users", {
        "username": owner_name, "display_name": "H3 test owner", "password": owner_password, "role": "citizen",
    })
    must(code, 201, "owner create")
    owner = Portal()
    must(owner.login(owner_name, owner_password), 200, "owner login")
    petition_ids = []
    for number in range(1, 4):
        code, body = owner.call("POST", "/petitions", {
            "title": f"H3 test petition {number}", "content": "Isolated integrity response verification petition.", "category": "기타",
        })
        must(code, 201, "petition create")
        petition_ids.append(body["data"]["id"])
    staff_client = Portal()
    must(staff_client.login(staff_name, staff_password), 200, "staff login")
    with urllib.request.urlopen(f"{TICKETS}?limit=200", timeout=10) as response:
        before = {item["ticket_id"] for item in json.loads(response.read())["items"] if item.get("group_key") == staff_name}
    input_at = datetime.now(timezone.utc).isoformat()
    statuses = []
    for petition_id in petition_ids[:updates]:
        code, body = staff_client.call("PATCH", f"/petitions/{petition_id}/assignment", {})
        must(code, 200, "petition assignment")
        code, body = staff_client.call("PATCH", f"/petitions/{petition_id}/status", {
            "status": "in_progress", "version": body["data"]["version"],
        })
        must(code, 200, "petition update")
        statuses.append(body["data"]["status"])
    return {"run_id": now, "admin": admin, "owner": owner, "staff_id": staff["data"]["id"],
            "staff_name": staff_name, "staff_password": staff_password, "petition_ids": petition_ids,
            "before": before, "input_at": input_at, "statuses": statuses}


def observe(run: dict) -> dict:
    """Owner sees every petition back in its pre-change status; the staff account is refused."""
    details = [run["owner"].call("GET", f"/petitions/{petition_id}") for petition_id in run["petition_ids"]]
    statuses = {detail.get("data", {}).get("status") for _, detail in details}
    return {"restored_status": statuses.pop() if len(statuses) == 1 else None,
            "owner_detail": max(code for code, _ in details),
            "locked_staff_login": Portal().login(run["staff_name"], run["staff_password"])}


def unlock(run: dict) -> int:
    """Administrator's human release, then the staff signs in again."""
    code, _ = run["admin"].call("POST", f"/admin/users/{run['staff_id']}/unlock", {"reason_code": "false_positive"})
    must(code, 200, "administrator unlock")
    return Portal().login(run["staff_name"], run["staff_password"])


def record(run: dict, ticket: dict, seen: dict, unlocked: int) -> dict:
    """Same shape as lab/run_ticket.py rows so tools/summarize_runs.py can count H3.
    attacker = the locked staff login (401 refused), normal = the owner's petitions (200 when all are back to received)."""
    acts = [(x["via"], x["action"], x["result"], x.get("finished_at")) for x in ticket.get("actions", [])]
    done = [x for x in acts if x[1] in RESPONSE_ACTIONS and x[2] in ("applied", "already_applied") and x[3]]
    det = ts(ticket.get("detected_at"))
    normal = "200" if seen["owner_detail"] == 200 and seen["restored_status"] == "received" else         f"{seen['owner_detail']} {seen['restored_status']}"
    return {"case": "H3", "src": "staff", "run_id": run["run_id"], "baseline": None, "input_at": run["input_at"],
            "staff_username": run["staff_name"], "petition_ids": run["petition_ids"], "input": run["statuses"],
            "ticket_id": ticket["ticket_id"], "status": ticket["status"], "actions": acts,
            "mttd_s": mttd(ts(ticket["condition_met_at"]), det) if ticket.get("condition_met_at") and det else None,
            "detect_to_block_s": round(max((ts(x[3]) - det).total_seconds() for x in done), 3) if done and det else None,
            "input_to_block_s": round(max((ts(x[3]) - ts(run["input_at"])).total_seconds() for x in done), 3) if done else None,
            "effect": {"attacker": str(seen["locked_staff_login"]), "normal": normal},
            "restore": {"verdict": "unlocked_by_admin", "attacker_after": str(unlocked)}}


def run_round(baseline: bool = False) -> dict:
    run = manipulate(2 if baseline else 3)
    if baseline:  # normal pace: two changes stay below the 3-in-5-minutes condition, so no ticket may appear
        ticket = new_ticket(run["staff_name"], run["before"])
        if ticket:
            unlock(run)  # do not leave the test staff locked
        return {"case": "H3", "src": "staff", "run_id": run["run_id"], "baseline": True, "input_at": run["input_at"],
                "staff_username": run["staff_name"], "input": run["statuses"],
                "ticket_id": ticket and ticket["ticket_id"], "result": "fail" if ticket else "pass",
                "reason": "false positive: ticket for normal pace" if ticket else None}
    locked = False
    try:
        ticket = new_ticket(run["staff_name"], run["before"])
        if not ticket:
            raise RuntimeError("no H3 ticket within 390 seconds")
        locked = True
        for _ in range(20):
            seen = observe(run)
            if seen["restored_status"] == "received" and seen["locked_staff_login"] == 401:
                break
            time.sleep(2)
        ticket = json.loads(urllib.request.urlopen(f"{TICKETS}/{ticket['ticket_id']}", timeout=10).read())["ticket"]
        unlocked = unlock(run)
        result = record(run, ticket, seen, unlocked)
        result["result"] = assess(ticket, {**seen, "unlocked_staff_login": unlocked})
        return result
    except Exception:
        if locked:
            run["admin"].call("POST", f"/admin/users/{run['staff_id']}/unlock", {"reason_code": "false_positive"})
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", action="store_true", help="two changes at normal pace; pass = no ticket")
    result = run_round(parser.parse_args().baseline)
    path = ROOT / "docs" / "tickets" / "H3" / "runs.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(json.dumps({key: result[key] for key in ("case", "run_id", "ticket_id", "result")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
