#!/usr/bin/env python3
"""Run one H4 (staff bulk petition lookup) round on the local portal and append it to docs/tickets/H4/runs.jsonl.

python lab/h4/live.py [--baseline]
Round: a fresh zz_ staff account opens 25 different petition details (Graylog: more than 19 in 10 minutes)
→ n8n haedam-38 → ticket → account lock (sessions revoked) → the staff login is refused, a citizen still reads
their own petition → the administrator unlocks after review → haedam-50 closes the ticket (restored).
--baseline opens 8 details (a normal working pace): no ticket may appear.
Graylog must be in live mode: python infra/graylog/bootstrap.py --live
Passwords stay in memory; nothing secret is printed.
"""
import argparse
import json
import secrets
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.h3.live import Portal, must, new_ticket, settings  # noqa: E402
from lab.run_ticket import RESPONSE_ACTIONS, TICKETS, mttd, release, ts, unauth_release_code  # noqa: E402

VIEWS = {False: 25, True: 8}  # detection: more than 19 in 10 minutes


def assess(run):
    eff, rest = run.get("effect") or {}, run.get("restore") or {}
    locked = any(a[1] == "lock" and a[2] in ("applied", "already_applied") for a in run.get("actions") or [])
    return "pass" if (locked and eff.get("attacker") == "401" and eff.get("normal") == "200"
                      and rest.get("attacker_after") == "200" and rest.get("status_after") == "restored"
                      and rest.get("permission_enforced")) else "fail"


def visible(staff_client):
    """Petition ids this staff may open (unassigned or their own), newest first, up to 100."""
    ids = []
    for page in (1, 2):
        code, listing = staff_client.call("GET", f"/petitions?page={page}&page_size=50")
        must(code, 200, "staff list")
        ids += [p["id"] for p in listing["data"]["items"]]
    return ids


def filler(admin, username):
    """One citizen files 4 petitions: enough lookup targets, below H1's 5-posts-in-10-minutes condition."""
    pw = secrets.token_urlsafe(18)
    code, _ = admin.call("POST", "/admin/users", {"username": username, "display_name": "H4 filler", "password": pw, "role": "citizen"})
    must(code, 201, "filler create")
    citizen = Portal()
    must(citizen.login(username, pw), 200, "filler login")
    for i in range(4):
        code, _ = citizen.call("POST", "/petitions", {"title": f"H4 lookup target {i + 1}", "category": "기타",
                                                      "content": "Isolated confidentiality response verification petition."})
        must(code, 201, "filler petition")


def prepare(views):
    """Fresh staff + citizen; the citizen files one petition (stays far below H1's 5-post condition)."""
    stamp = datetime.now(timezone.utc).strftime("%m%d%H%M%S")
    config = settings()
    staff_name, owner_name = f"zz_h4_staff_{stamp}", f"zz_h4_owner_{stamp}"
    staff_pw, owner_pw = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
    admin = Portal()
    must(admin.login(config["PORTAL_ADMIN_USERNAME"], config["PORTAL_ADMIN_PASSWORD"]), 200, "admin login")
    code, staff = admin.call("POST", "/admin/users", {"username": staff_name, "display_name": "H4 test staff",
                                                      "password": staff_pw, "role": "staff", "department": "민원행정과"})
    must(code, 201, "staff create")
    code, _ = admin.call("POST", "/admin/users", {"username": owner_name, "display_name": "H4 test owner",
                                                  "password": owner_pw, "role": "citizen"})
    must(code, 201, "owner create")
    owner = Portal()
    must(owner.login(owner_name, owner_pw), 200, "owner login")
    code, body = owner.call("POST", "/petitions", {"title": "H4 test petition", "category": "기타",
                                                   "content": "Isolated confidentiality response verification petition."})
    must(code, 201, "petition create")
    staff_client = Portal()
    must(staff_client.login(staff_name, staff_pw), 200, "staff login")
    ids = visible(staff_client)
    for n in range(-(-(views - len(ids)) // 4) if len(ids) < views else 0):  # a fresh DB: add citizens' petitions
        filler(admin, f"zz_h4_cit{n}_{stamp}")
    ids = visible(staff_client)
    if len(ids) < views:
        raise RuntimeError(f"only {len(ids)} petitions visible to staff, need {views}")
    with urllib.request.urlopen(f"{TICKETS}?limit=200", timeout=10) as r:
        before = {t["ticket_id"] for t in json.loads(r.read())["items"] if t.get("group_key") == staff_name}
    return {"run_id": stamp, "admin": admin, "owner": owner, "own_id": body["data"]["id"], "staff": staff_client,
            "staff_id": staff["data"]["id"], "staff_name": staff_name, "staff_pw": staff_pw, "ids": ids[:views],
            "before": before}


def view_all(run):
    run["input_at"] = datetime.now(timezone.utc).isoformat()
    return [run["staff"].call("GET", f"/petitions/{pid}")[0] for pid in run["ids"]]


def unlock(run):
    code, _ = run["admin"].call("POST", f"/admin/users/{run['staff_id']}/unlock", {"reason_code": "false_positive"})
    must(code, 200, "administrator unlock")


def run_round(baseline):
    run = prepare(VIEWS[baseline])
    statuses = view_all(run)
    row = {"case": "H4", "src": "staff", "run_id": run["run_id"], "baseline": baseline or None, "input_at": run["input_at"],
           "staff_username": run["staff_name"], "input": {"views": len(statuses), "status_200": statuses.count(200)}}
    ticket = new_ticket(run["staff_name"], run["before"], timeout=150 if baseline else 240)
    if baseline:
        if ticket:
            unlock(run)  # do not leave the test staff locked
        row.update(ticket_id=ticket and ticket["ticket_id"], result="fail" if ticket else "pass",
                   reason="false positive: ticket for a normal pace" if ticket else None)
        return row
    if not ticket:
        row.update(result="fail", reason="no H4 ticket within 240 s")
        return row
    try:
        for _ in range(20):  # the lock lands a moment after the ticket
            ticket = json.loads(urllib.request.urlopen(f"{TICKETS}/{ticket['ticket_id']}", timeout=10).read())["ticket"]
            if any(a["action"] == "lock" for a in ticket.get("actions", [])):
                break
            time.sleep(2)
        acts = [(x["via"], x["action"], x["result"], x.get("finished_at")) for x in ticket.get("actions", [])]
        done = [x for x in acts if x[1] in RESPONSE_ACTIONS and x[2] in ("applied", "already_applied") and x[3]]
        det = ts(ticket.get("detected_at"))
        session_code = run["staff"].call("GET", f"/petitions/{run['ids'][0]}")[0]  # the staff's live session
        row.update(ticket_id=ticket["ticket_id"], status=ticket["status"], actions=acts,
                   mttd_s=mttd(ts(ticket["condition_met_at"]), det) if ticket.get("condition_met_at") and det else None,
                   detect_to_block_s=round(max((ts(x[3]) - det).total_seconds() for x in done), 3) if done and det else None,
                   input_to_block_s=round(max((ts(x[3]) - ts(run["input_at"])).total_seconds() for x in done), 3) if done else None,
                   # attacker = the staff's new login; normal = a citizen reading their own petition
                   effect={"attacker": str(Portal().login(run["staff_name"], run["staff_pw"])),
                           "session_after_lock": session_code,
                           "normal": str(run["owner"].call("GET", f"/petitions/{run['own_id']}")[0])})
    finally:
        unlock(run)
    rel = release(settings(), "H4", "H4", run["staff_name"])
    row["restore"] = {"verdict": rel.get("verdict"), "attacker_after": str(Portal().login(run["staff_name"], run["staff_pw"])),
                      "status_after": json.loads(urllib.request.urlopen(f"{TICKETS}/{ticket['ticket_id']}", timeout=10).read())["ticket"]["status"],
                      "unauth_release": unauth_release_code("H4")}
    row["restore"]["permission_enforced"] = row["restore"]["unauth_release"] in ("401", "403")
    row["result"] = assess(row)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", action="store_true", help="8 views at a normal pace; pass = no ticket")
    row = run_round(ap.parse_args().baseline)
    out = ROOT / "docs/tickets/H4/runs.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False, indent=1))
    return 0 if row["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
