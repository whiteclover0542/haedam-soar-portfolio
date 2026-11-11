"""Import Haedam credentials and workflows into the running haedam-n8n container. Safe to re-run (fixed ids).

python infra/n8n/load.py
Reads .env and the dedicated pfSense key (.local/haedam-pf). Secrets go through docker exec stdin into a
temp file that is deleted right after import; nothing is written on the host.
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from infra.n8n.make_credentials import attach_credentials, build_credentials  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONTAINER = "haedam-n8n"
# Only what the current stage uses goes into n8n (the other files stay in the repo); each gets a role tag for
# filtering in the n8n list. Add a line here when a stage (S4·S7·S12) starts.
# Everything listed is published: webhooks need it, and n8n 2.x refuses to run an unpublished sub-workflow.
SCOPE = {
    "haedamS1Main01": "메인", "haedamS8S10Main01": "메인", "haedamH1Main01": "메인", "haedamH2Main01": "메인",
    "haedamResultLog01": "부품", "haedamDiscord01": "부품", "haedamPortalIp01": "부품", "haedamPfsense01": "부품",
    "haedamPortalPosting01": "부품", "haedamAccountLock01": "부품",
    "haedamRelease01": "점검·해제", "haedamTicketCheck01": "점검·해제", "haedamPfStatusCheck01": "점검·해제",
}
NOT_PUBLISHED = {"haedamPfStatusCheck01"}  # manual trigger only; run with `n8n execute`


def env_file():
    pairs = (l.split("=", 1) for l in (ROOT / ".env").read_text("utf-8").splitlines() if "=" in l and not l.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def n8n_import(kind, payload):
    tmp = f"/tmp/haedam-{kind}.json"
    cmd = f"cat > {tmp} && n8n import:{kind} --input={tmp}; status=$?; rm -f {tmp}; exit $status"
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", cmd],
                       input=json.dumps(payload, ensure_ascii=False).encode(), capture_output=True)
    if r.returncode:
        print(f"import:{kind}", (r.stdout + r.stderr).decode(errors="replace")[-800:])
        raise SystemExit(1)


def main():
    env = env_file()
    key_file = ROOT / env.get("PF_SSH_PRIVATE_KEY_FILE", ".local/haedam-pf")
    env["PF_SSH_PRIVATE_KEY"] = key_file.read_text("utf-8")
    creds = build_credentials(env)
    workflows = []
    for p in sorted((ROOT / "infra/n8n/workflows").glob("*.json")):
        w = json.loads(p.read_text("utf-8"))
        w = w[0] if isinstance(w, list) else w
        if w.get("id") in SCOPE:
            workflows.append({**attach_credentials(w, creds), "tags": [{"name": SCOPE[w["id"]]}]})
    missing = SCOPE.keys() - {w["id"] for w in workflows}
    if missing:
        raise SystemExit(f"workflow files not found for: {sorted(missing)}")
    n8n_import("credentials", creds)
    for w in workflows:  # one at a time: a batch creates each new tag once per workflow and hits UNIQUE(name)
        n8n_import("workflow", [w])
    publish = [wid for wid in SCOPE if wid not in NOT_PUBLISHED]
    for wid in publish:
        subprocess.run(["docker", "exec", CONTAINER, "n8n", "publish:workflow", f"--id={wid}"], check=True,
                       capture_output=True)
    # publish:workflow does not register webhooks in the running server (team note 11/03); a restart does.
    subprocess.run(["docker", "restart", CONTAINER], check=True, capture_output=True)
    print(f"workflows {len(workflows)}, credentials {len(creds)}, published {len(publish)}: {', '.join(publish)}; n8n restarted")


if __name__ == "__main__":
    main()
