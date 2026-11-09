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
# Webhook entry points to publish. Sub-workflows are published too: n8n 2.x refuses to execute an
# unpublished one ("Workflow is not active"), and they have no webhook, so publishing exposes nothing.
PUBLISH = ["haedamS1Main01", "haedamS8S10Main01", "haedamTicketCheck01", "haedamRelease01", "haedamH1Main01"]


def is_sub_workflow(w):
    return any(n["type"].endswith("executeWorkflowTrigger") for n in w["nodes"])


def env_file():
    pairs = (l.split("=", 1) for l in (ROOT / ".env").read_text("utf-8").splitlines() if "=" in l and not l.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def n8n_import(kind, payload):
    tmp = f"/tmp/haedam-{kind}.json"
    cmd = f"cat > {tmp} && n8n import:{kind} --input={tmp}; status=$?; rm -f {tmp}; exit $status"
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", cmd],
                       input=json.dumps(payload, ensure_ascii=False).encode(), capture_output=True)
    print(f"import:{kind}", "ok" if r.returncode == 0 else r.stderr.decode(errors="replace")[-500:])
    if r.returncode:
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
        if w.get("id"):  # haedam-16 is an offline design note without an id
            workflows.append(attach_credentials(w, creds))
    n8n_import("credentials", creds)
    n8n_import("workflow", workflows)
    publish = PUBLISH + [w["id"] for w in workflows if is_sub_workflow(w)]
    for wid in publish:
        subprocess.run(["docker", "exec", CONTAINER, "n8n", "publish:workflow", f"--id={wid}"], check=True,
                       capture_output=True)
    # publish:workflow does not register webhooks in the running server (team note 11/03); a restart does.
    subprocess.run(["docker", "restart", CONTAINER], check=True, capture_output=True)
    print(f"workflows {len(workflows)}, credentials {len(creds)}, published {len(publish)}: {', '.join(publish)}; n8n restarted")


if __name__ == "__main__":
    main()
