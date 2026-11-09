"""Run one ticket end to end on the single-PC stack and append the result to docs/tickets/<ID>/runs.jsonl.

python lab/run_ticket.py {S1|S8|S10} [--restore]
Steps: precheck → input from haedam-attacker → wait for the ticket (≤180 s) → effect (attacker blocked, normal 200)
→ with --restore: release via n8n haedam-50 (pfSense first, then portal) → attacker 200 again.
Graylog must be in live mode: python infra/graylog/bootstrap.py --live
"""
import argparse
import json
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = {"S1": "203.0.113.11", "S8": "203.0.113.21", "S10": "203.0.113.22", "H1": "203.0.113.11"}
WINDOW_MIN = {"S1": 30, "S8": 15, "S10": 15, "H1": 10}
SEAT = {"S1": "A", "S8": "B", "S10": "B", "H1": "A"}
H1_POSTS = 8  # 탐지 기준 N=5보다 넉넉히(초안). 기준선은 --baseline
RESPONSE_ACTIONS = ("block", "fw_block", "restrict_posting")
NORMAL = "203.0.113.100"
TICKETS = "http://127.0.0.1:8089/api/v1/tickets"


def window_blocked(last_run, now, minutes):
    """Seconds left before the same source may run again (detection windows must not overlap), else None."""
    if last_run is None:
        return None
    left = minutes * 60 - (now - last_run).total_seconds()
    return round(left) if left > 0 else None


def precheck(blocked_ips, pf_table, src):
    return ([f"portal_block_left:{src}"] if src in blocked_ips else []) + \
           ([f"pf_block_left:{src}"] if src in pf_table else [])


def mttd(condition_met_at, detected_at):
    return round((detected_at - condition_met_at).total_seconds(), 3)


def ts(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def env():
    pairs = (l.split("=", 1) for l in (ROOT / ".env").read_text("utf-8").splitlines() if "=" in l and not l.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def sh(*cmd, env_vars=None, check=True):
    extra = [x for k in (env_vars or {}) for x in ("-e", k)]
    full = list(cmd)
    if full[:2] == ["docker", "exec"] and extra:
        full[2:2] = extra
    r = subprocess.run(full, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240,
                       env=None if not env_vars else {**__import__("os").environ, **env_vars})
    if check and r.returncode:
        raise SystemExit(f"{cmd[:4]} failed: {(r.stderr or r.stdout)[-300:]}")
    return r.stdout.strip()


def get(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read())


def http_code(container, src, path="/api/v1/health"):
    return sh("docker", "exec", container, "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--interface", src,
              "--max-time", "5", "http://203.0.113.1" + path, check=False) or "000"


def portal_posting(e, username, restricted):
    """Person's release for H1 (and cleanup): the response API from n8n's address, like the workflows call it."""
    js = ("fetch('http://10.250.0.2:5000/api/v1/response/accounts/posting',{method:'POST',headers:{'X-Response-Key':process.env.K,"
          "'Idempotency-Key':process.env.I,'Content-Type':'application/json'},body:JSON.stringify({username:process.env.U,restricted:"
          + ("true" if restricted else "false") + "})}).then(r=>console.log(r.status))")
    return sh("docker", "exec", "haedam-n8n", "node", "-e", js,
              env_vars={"K": e["PORTAL_RESPONSE_KEY"], "I": f"run-ticket-{username}-{int(restricted)}", "U": username})


def portal_blocked(e):
    js = ("fetch('http://10.250.0.2:5000/api/v1/response/ips',{headers:{'X-Response-Key':process.env.K}})"
          ".then(r=>r.json()).then(j=>console.log(JSON.stringify(j.data.items.map(i=>i.ip))))")
    return json.loads(sh("docker", "exec", "haedam-n8n", "node", "-e", js, env_vars={"K": e["PORTAL_RESPONSE_KEY"]}))


def pf_table():
    """haedam-03 → haedam-14 status for 203.0.113.22 (the only target the pfSense tool accepts)."""
    out = sh("docker", "exec", "-e", "N8N_RUNNERS_BROKER_PORT=5690", "-e", "N8N_PORT=5691", "haedam-n8n",
             "n8n", "execute", "--id=haedamPfStatusCheck01", "--rawOutput")
    d = json.loads(out[out.index("{"):])
    res = d["data"]["resultData"]["runData"]["haedam-14 (pfSense status)"][0]["data"]["main"][0][0]["json"]
    state = res.get("tool_state") or {}
    return ["203.0.113.22"] if state.get("configured") or state.get("table_present") else []


def portal_login(container, src, *args, pw=None):
    sh("docker", "cp", str(ROOT / "lab/portal_login.py"), f"{container}:/lab/portal_login.py")
    return json.loads(sh("docker", "exec", container, "python", "/lab/portal_login.py", "--source", src, *args,
                         env_vars={"PW": pw} if pw else None))


def last_run(case):
    """Newest real attack input time; baseline runs use the normal source, so they don't consume the attack window."""
    f = ROOT / f"docs/tickets/{case}/runs.jsonl"
    lines = f.read_text("utf-8").splitlines() if f.exists() else []
    for line in reversed(lines):
        r = json.loads(line)
        if not r.get("baseline"):
            return ts(r["input_at"])
    return None


def unauth_release_code(case):
    """A release attempt WITHOUT the key must be rejected — authorization stays enforced after the incident."""
    if case == "H1":
        js = ("fetch('http://10.250.0.2:5000/api/v1/response/accounts/posting',{method:'POST',headers:{'Content-Type':"
              "'application/json'},body:JSON.stringify({username:'zz',restricted:false})}).then(r=>console.log(r.status))")
        return sh("docker", "exec", "haedam-n8n", "node", "-e", js)
    body = json.dumps({"seat": SEAT[case], "case_id": case, "group_key": "zz", "approver": "noauth", "dry_run": True}).encode()
    req = urllib.request.Request("http://127.0.0.1:5678/webhook/haedam-release", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return str(r.status)
    except urllib.error.HTTPError as ex:
        return str(ex.code)


def tickets_for(group_key):
    return {t["ticket_id"]: t for t in get(f"{TICKETS}?limit=200")["items"] if t["group_key"] == group_key}


def find_ticket(case, group_key, before, timeout=180):
    """A ticket for this source that did not exist before the input. S8 and S10 share one seat-B ticket per
    source (the S10 input also fires S8), so match on group_key, not case_id. S10 waits for its pfSense action."""
    end = time.time() + timeout
    while time.time() < end:
        for tid in tickets_for(group_key).keys() - before:
            t = get(f"{TICKETS}/{tid}")["ticket"]
            if case != "S10" or any(a["via"] == "pfsense" for a in t.get("actions", [])):
                return t
        time.sleep(5)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=SRC)
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--baseline", action="store_true", help="H1: normal citizen pace (3 posts, 2 min apart); expects no ticket")
    a = ap.parse_args()
    case, src, e = a.case, SRC[a.case], env()
    now = datetime.now(timezone.utc)
    left = window_blocked(last_run(case), now, WINDOW_MIN[case])
    if left and not a.baseline:
        raise SystemExit(f"{case}: same-source window still open, wait {left}s")
    problems = precheck(portal_blocked(e), pf_table() if case == "S10" else [], src)
    if problems:
        raise SystemExit("precheck: " + ", ".join(problems))

    run = {"case": case, "src": src, "run_id": now.strftime("%m%d%H%M%S")}
    if a.baseline and case != "H1":
        # Normal citizen from the normal source: 3 wrong passwords then a success — below every S1/S8/S10 threshold.
        user, pw = f"zz_base_{case.lower()}_{run['run_id']}", secrets.token_urlsafe(12)
        run["src"], run["baseline"] = NORMAL, True
        run["register"] = portal_login("haedam-normal", NORMAL, "register", user, pw=pw)["statuses"]
        run["input_at"] = datetime.now(timezone.utc).isoformat()
        run["input"] = portal_login("haedam-normal", NORMAL, "fail", user, "3")["statuses"]
        run["input"].append(portal_login("haedam-normal", NORMAL, "login", user, pw=pw)["statuses"][0])
        group_key = user if case == "S1" else NORMAL  # S1 keys on username+src_ip; S8/S10 on src_ip
    elif case == "H1":
        user, pw = f"zz_a_h1_{run['run_id']}", secrets.token_urlsafe(12)
        who, at = ("haedam-normal", NORMAL) if a.baseline else ("haedam-attacker", src)
        run["src"], run["baseline"] = at, a.baseline or None
        run["register"] = portal_login(who, at, "register", user, pw=pw)["statuses"]
        run["input_at"] = datetime.now(timezone.utc).isoformat()
        if a.baseline:
            run["input"] = []
            for i in range(3):  # a busy but normal citizen: 3 petitions, 2 minutes apart
                run["input"].append(portal_login(who, at, "post", user, "1", pw=pw)["statuses"][0])
                if i < 2:
                    time.sleep(120)
        else:
            run["input"] = portal_login(who, at, "post", user, str(H1_POSTS), pw=pw)
        group_key = user
    elif case == "S1":
        user, pw = f"zz_a_s1_{run['run_id']}", secrets.token_urlsafe(12)
        run["register"] = portal_login("haedam-normal", NORMAL, "register", user, pw=pw)["statuses"]
        run["input_at"] = datetime.now(timezone.utc).isoformat()
        run["input"] = portal_login("haedam-attacker", src, "fail", user, "9")
        group_key = user
    else:
        sh("docker", "cp", str(ROOT / "tools/s8s10_input.py"), "haedam-attacker:/lab/s8s10_input.py")
        run["input_at"] = datetime.now(timezone.utc).isoformat()
        sh("docker", "exec", "haedam-attacker", "python", "/lab/s8s10_input.py", "--case", case,
           "--run-id", run["run_id"], "--out", f"/tmp/{run['run_id']}.json", "--execute")
        run["input"] = [x["status"] for x in json.loads(sh("docker", "exec", "haedam-attacker", "cat", f"/tmp/{run['run_id']}.json"))["http"]]
        group_key = src
    before = set(tickets_for(group_key))  # tickets already present for this key, so we only count ones our input creates
    print("input", run["input"], flush=True)

    # Baseline waits for any new ticket (no S10 pfSense requirement); a real run keeps the case-specific wait.
    ticket = find_ticket("S1" if a.baseline else case, group_key, before, timeout=150 if a.baseline else 180)
    if a.baseline:  # pass = no ticket for a normal pace (false positive otherwise)
        run.update(ticket_id=ticket["ticket_id"] if ticket else None, result="fail" if ticket else "pass",
                   reason="false positive: ticket for normal pace" if ticket else None)
        if ticket and case == "H1":
            portal_posting(e, group_key, False)  # do not leave the citizen restricted
    elif not ticket:
        run.update(result="fail", reason="no ticket within 180s")
    else:
        time.sleep(5)  # let the response actions land
        ticket = get(f"{TICKETS}/{ticket['ticket_id']}")["ticket"]
        acts = [(x["via"], x["action"], x["result"], x.get("finished_at")) for x in ticket.get("actions", [])]
        blocked = [x for x in acts if x[1] in RESPONSE_ACTIONS and x[2] in ("applied", "already_applied")]
        det = ts(ticket.get("detected_at"))
        run.update(ticket_id=ticket["ticket_id"], status=ticket["status"], actions=acts,
                   mttd_s=mttd(ts(ticket["condition_met_at"]), det) if ticket.get("condition_met_at") and det else None,
                   detect_to_block_s=round(max((ts(x[3]) - det).total_seconds() for x in blocked), 3) if blocked and det else None,
                   # Graylog evaluates every 60 s, so this (input → last block applied) is the end-to-end number.
                   input_to_block_s=round(max((ts(x[3]) - ts(run["input_at"])).total_seconds() for x in blocked), 3) if blocked else None,
                   effect={"attacker": http_code("haedam-attacker", src), "normal": http_code("haedam-normal", NORMAL)})
        if case == "H1":
            again = portal_login("haedam-attacker", src, "post", group_key, "1", pw=pw)
            other, other_pw = f"zz_a_h1n_{run['run_id']}", secrets.token_urlsafe(12)
            portal_login("haedam-normal", NORMAL, "register", other, pw=other_pw)
            run["effect"] = {"attacker": str(again["statuses"][0]), "attacker_login": again["login"], "attacker_list": again["list"],
                             "normal": str(portal_login("haedam-normal", NORMAL, "post", other, "1", pw=other_pw)["statuses"][0])}
        if case == "S1":
            run["effect"]["normal_login_same_user"] = portal_login("haedam-normal", NORMAL, "login", group_key, pw=pw)["statuses"]
        if a.restore and case == "H1":
            run["restore"] = {"verdict": "released_by_person", "steps": [(1, portal_posting(e, group_key, False))],
                              "attacker_after": str(portal_login("haedam-attacker", src, "post", group_key, "1", pw=pw)["statuses"][0]),
                              "status_after": get(f"{TICKETS}/{ticket['ticket_id']}")["ticket"]["status"],
                              "unauth_release": unauth_release_code(case)}
            run["restore"]["permission_enforced"] = run["restore"]["unauth_release"] in ("401", "403")
        elif a.restore:
            body = json.dumps({"seat": SEAT[case], "case_id": ticket["case_id"], "group_key": group_key, "approver": "run_ticket",
                               "dry_run": False, "reason": "lab run restore"}).encode()
            req = urllib.request.Request("http://127.0.0.1:5678/webhook/haedam-release", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "X-Haedam-Key": e["N8N_WEBHOOK_KEY"]})
            with urllib.request.urlopen(req, timeout=120) as r:
                rel = json.loads(r.read())
            rel = rel[0] if isinstance(rel, list) else rel
            run["restore"] = {"verdict": rel.get("verdict"), "steps": [(s.get("step"), s.get("result")) for s in rel.get("steps") or []],
                              "attacker_after": http_code("haedam-attacker", src),
                              "status_after": get(f"{TICKETS}/{ticket['ticket_id']}")["ticket"]["status"],
                              "unauth_release": unauth_release_code(case)}
            run["restore"]["permission_enforced"] = run["restore"]["unauth_release"] in ("401", "403")
        refused, fine = (("429",), "201") if case == "H1" else (("403", "000"), "200")
        ok = bool(blocked) and run["effect"]["attacker"] in refused and run["effect"]["normal"] == fine
        if case == "S10":  # the point of S10 is the perimeter block; a portal-only 403 is not a pass
            ok = ok and any(x[0] == "pfsense" for x in blocked) and run["effect"]["attacker"] == "000"
        if a.restore:
            ok = ok and run["restore"]["attacker_after"] == fine and run["restore"].get("permission_enforced")
        run["result"] = "pass" if ok else "fail"
    out = ROOT / f"docs/tickets/{case}/runs.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")
    print(json.dumps(run, ensure_ascii=False, indent=1))
    return 0 if run["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
