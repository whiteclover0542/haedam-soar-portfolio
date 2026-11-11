#!/usr/bin/env python3
"""Run one S7 (homepage file tampering) round on the single-PC stack and append it to docs/tickets/S7/runs.jsonl.

python lab/s7/live.py [--file favicon.svg] [--baseline]
Round: verify baseline → append one HTML/CSS/JS comment to a baseline file in haedam-portal:/app/dist (harmless,
but the sha256 changes) → Wazuh FIM 550 → Graylog s7 → n8n haedam-33 → ticket + Wazuh AR restore →
served file hash equals the baseline again, portal 200, s7_restore verify ok, unauthorised requests refused.
--baseline rewrites the file with its own baseline bytes (a "normal redeploy"): no ticket is expected.
Each round uses its own file because haedam-33 reuses an open ticket for the same file (restore is a one-shot action).
Graylog must be in live mode: python infra/graylog/bootstrap.py --live
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab.run_ticket import TICKETS, env, get, mttd, sh, tickets_for, ts  # noqa: E402

PORTAL = "http://127.0.0.1:8080/"
RESTORE = "/opt/haedam-s7/bin/s7_restore.py"
COMMENT = {".html": "\n<!-- s7 lab {rid} -->\n", ".svg": "\n<!-- s7 lab {rid} -->\n", ".css": "\n/* s7 lab {rid} */\n",
           ".js": "\n/* s7 lab {rid} */\n"}
S7_ACTIONS = ("restore", "quarantine")


def manifest():
    """{relative path: baseline sha256} from the portal container."""
    out = sh("docker", "exec", "haedam-portal", "cat", "/opt/haedam-s7/baseline.sha256")
    return {p: h for h, p in (l.split(None, 1) for l in out.splitlines() if l.strip())}


def served_sha(path):
    """sha256 of the file a citizen's browser gets (host port 8080 → portal)."""
    with urllib.request.urlopen(PORTAL + path, timeout=10) as r:
        return r.status, hashlib.sha256(r.read()).hexdigest()


def verify():
    out = sh("docker", "exec", "haedam-portal", "python", RESTORE, "verify", check=False)
    return json.loads(out.splitlines()[0]).get("result") if out.startswith("{") else out[:80]


def code(fn):
    try:
        return str(fn())
    except urllib.error.HTTPError as ex:
        return str(ex.code)


def unauth_webhook(port, path):
    """haedam-33 without X-Haedam-Key must be refused (403)."""
    body = json.dumps({"event_id": "noauth", "asset_id": "haedam-portal", "file_key": path, "dry_run": True}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/webhook/haedam-s7", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    return code(lambda: urllib.request.urlopen(req, timeout=30).status)


def outside_root():
    """The restore tool Wazuh AR calls must refuse a path outside the web root."""
    out = sh("docker", "exec", "haedam-portal", "python", RESTORE, "restore", "../../etc/passwd", "--run-id", "s7-perm",
             check=False)
    return out.splitlines()[-1] if out else ""


def assess(run):
    eff, rest = run.get("effect") or {}, run.get("restore") or {}
    applied = any(a[1] in S7_ACTIONS and a[2] in ("applied", "already_applied") for a in run.get("actions") or [])
    return "pass" if (applied and eff.get("attacker") == "baseline_hash" and eff.get("normal") == "200"
                      and rest.get("attacker_after") == "200" and rest.get("verify") == "ok"
                      and rest.get("permission_enforced")) else "fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="favicon.svg", help="baseline file under /app/dist")
    ap.add_argument("--baseline", action="store_true")
    a = ap.parse_args()
    e, base = env(), manifest()
    if a.file not in base:
        raise SystemExit(f"{a.file} is not in the baseline manifest: {sorted(base)}")
    if verify() != "ok":
        raise SystemExit("precheck: web root differs from the baseline; run s7_restore.py verify")
    now = datetime.now(timezone.utc)
    group_key = f"haedam-portal:{a.file}"
    run = {"case": "S7", "src": f"haedam-portal:/app/dist/{a.file}", "run_id": now.strftime("%m%d%H%M%S"),
           "file_key": a.file, "baseline": a.baseline or None}
    before = set(tickets_for(group_key))
    # haedam-33 reuses an open ticket for the same file, so a false positive may only add an action to it
    acts_before = {t: len(get(f"{TICKETS}/{t}")["ticket"].get("actions", [])) for t in before}
    target = f"/app/dist/{a.file}"
    run["input_at"] = datetime.now(timezone.utc).isoformat()
    if a.baseline:  # a normal redeploy: same bytes written again, mtime changes, hash does not
        sh("docker", "exec", "haedam-portal", "sh", "-c", f"cp /opt/haedam-s7/baseline/{a.file} {target} && touch {target}")
    else:
        text = COMMENT[Path(a.file).suffix].format(rid=run["run_id"])
        sh("docker", "exec", "-e", "T=" + text, "haedam-portal", "sh", "-c", f'printf %s "$T" >> {target}')
    run["input"] = sh("docker", "exec", "haedam-portal", "sha256sum", target).split()[0]
    print("input", a.file, run["input"][:12], flush=True)

    ticket, end = None, time.time() + (150 if a.baseline else 240)
    while time.time() < end and not ticket:
        new = tickets_for(group_key).keys() - before
        if a.baseline:
            new |= {t for t, n in acts_before.items() if len(get(f"{TICKETS}/{t}")["ticket"].get("actions", [])) > n}
        if new:
            t = get(f"{TICKETS}/{sorted(new)[-1]}")["ticket"]
            if a.baseline or any(x["action"] in S7_ACTIONS for x in t.get("actions", [])):
                ticket = t
        time.sleep(3)
    if a.baseline:
        run.update(ticket_id=ticket["ticket_id"] if ticket else None, result="fail" if ticket else "pass",
                   reason="false positive: ticket for a same-hash redeploy" if ticket else None, verify=verify())
    elif not ticket:
        run.update(result="fail", reason="no S7 ticket with a restore action within 240s", verify=verify())
    else:
        time.sleep(3)  # the AR runs on the agent right after n8n records it
        ticket = get(f"{TICKETS}/{ticket['ticket_id']}")["ticket"]
        acts = [(x["via"], x["action"], x["result"], x.get("finished_at")) for x in ticket.get("actions", [])]
        done = [x for x in acts if x[1] in S7_ACTIONS and x[2] in ("applied", "already_applied") and x[3]]
        det = ts(ticket.get("detected_at"))
        status, sha = served_sha(a.file)
        home, _ = served_sha("")
        run.update(ticket_id=ticket["ticket_id"], status=ticket["status"], actions=acts,
                   mttd_s=mttd(ts(ticket["condition_met_at"]), det) if ticket.get("condition_met_at") and det else None,
                   detect_to_block_s=round(max((ts(x[3]) - det).total_seconds() for x in done), 3) if done and det else None,
                   input_to_block_s=round(max((ts(x[3]) - ts(run["input_at"])).total_seconds() for x in done), 3) if done else None,
                   # "attacker" = what the tampered path serves now; "normal" = the portal home page for a citizen
                   effect={"attacker": "baseline_hash" if sha == base[a.file] else "tampered", "served_status": status,
                           "normal": str(home)})
        port = e.get("N8N_HOST_PORT", "5678")
        run["restore"] = {"verify": verify(), "attacker_after": str(status) if sha == base[a.file] else "tampered",
                          "unauth_webhook": unauth_webhook(port, a.file), "outside_root": outside_root()}
        run["restore"]["permission_enforced"] = (run["restore"]["unauth_webhook"] in ("401", "403")
                                                 and "path_outside_web_root" in run["restore"]["outside_root"])
        run["result"] = assess(run)
    out = ROOT / "docs/tickets/S7/runs.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")
    print(json.dumps(run, ensure_ascii=False, indent=1))
    return 0 if run["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
