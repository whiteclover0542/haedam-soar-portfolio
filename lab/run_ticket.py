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
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = {"S1": "203.0.113.11", "S8": "203.0.113.21", "S10": "203.0.113.22"}
WINDOW_MIN = {"S1": 30, "S8": 15, "S10": 15}
SEAT = {"S1": "A", "S8": "B", "S10": "B"}
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
    f = ROOT / f"docs/tickets/{case}/runs.jsonl"
    lines = f.read_text("utf-8").splitlines() if f.exists() else []
    return ts(json.loads(lines[-1])["input_at"]) if lines else None


def find_ticket(case, group_key, since, timeout=180):
    end = time.time() + timeout
    while time.time() < end:
        for t in get(f"{TICKETS}?case_id={case}&limit=50")["items"]:
            if t["group_key"] == group_key and ts(t["updated_at"]) >= since:
                return get(f"{TICKETS}/{t['ticket_id']}")["ticket"], t
        time.sleep(5)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case", choices=SRC)
    ap.add_argument("--restore", action="store_true")
    a = ap.parse_args()
    case, src, e = a.case, SRC[a.case], env()
    now = datetime.now(timezone.utc)
    left = window_blocked(last_run(case), now, WINDOW_MIN[case])
    if left:
        raise SystemExit(f"{case}: same-source window still open, wait {left}s")
    problems = precheck(portal_blocked(e), pf_table() if case == "S10" else [], src)
    if problems:
        raise SystemExit("precheck: " + ", ".join(problems))

    run = {"case": case, "src": src, "run_id": now.strftime("%m%d%H%M%S")}
    if case == "S1":
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
    print("input", run["input"], flush=True)

    ticket, row = find_ticket(case, group_key, ts(run["input_at"]))
    if not ticket:
        run.update(result="fail", reason="no ticket within 180s")
    else:
        time.sleep(5)  # let the response actions land
        ticket = get(f"{TICKETS}/{ticket['ticket_id']}")["ticket"]
        acts = [(x["via"], x["action"], x["result"], x.get("finished_at")) for x in ticket.get("actions", [])]
        blocked = [x for x in acts if x[1] in ("block", "fw_block") and x[2] in ("applied", "already_applied")]
        det = ts(ticket.get("detected_at"))
        run.update(ticket_id=ticket["ticket_id"], status=ticket["status"], actions=acts,
                   mttd_s=mttd(ts(ticket["condition_met_at"]), det) if ticket.get("condition_met_at") and det else None,
                   detect_to_block_s=round(max((ts(x[3]) - det).total_seconds() for x in blocked), 3) if blocked and det else None,
                   # Graylog evaluates every 60 s, so this (input → last block applied) is the end-to-end number.
                   input_to_block_s=round(max((ts(x[3]) - ts(run["input_at"])).total_seconds() for x in blocked), 3) if blocked else None,
                   effect={"attacker": http_code("haedam-attacker", src), "normal": http_code("haedam-normal", NORMAL)})
        if case == "S1":
            run["effect"]["normal_login_same_user"] = portal_login("haedam-normal", NORMAL, "login", group_key, pw=pw)["statuses"]
        if a.restore:
            body = json.dumps({"seat": SEAT[case], "case_id": case, "group_key": group_key, "approver": "run_ticket",
                               "dry_run": False, "reason": "lab run restore"}).encode()
            req = urllib.request.Request("http://127.0.0.1:5678/webhook/haedam-release", data=body, method="POST",
                                         headers={"Content-Type": "application/json", "X-Haedam-Key": e["N8N_WEBHOOK_KEY"]})
            with urllib.request.urlopen(req, timeout=120) as r:
                rel = json.loads(r.read())
            rel = rel[0] if isinstance(rel, list) else rel
            run["restore"] = {"verdict": rel.get("verdict"), "steps": [(s.get("step"), s.get("result")) for s in rel.get("steps") or []],
                              "attacker_after": http_code("haedam-attacker", src),
                              "status_after": get(f"{TICKETS}/{ticket['ticket_id']}")["ticket"]["status"]}
        ok = bool(blocked) and run["effect"]["attacker"] in ("403", "000") and run["effect"]["normal"] == "200"
        if a.restore:
            ok = ok and run["restore"]["attacker_after"] == "200"
        run["result"] = "pass" if ok else "fail"
    out = ROOT / f"docs/tickets/{case}/runs.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")
    print(json.dumps(run, ensure_ascii=False, indent=1))
    return 0 if run["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
