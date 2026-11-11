"""Check that all five parts are up. Prints `OK|FAIL name detail`; exits 1 if any FAIL.

python tools/check_stack.py
Host-side checks use the 127.0.0.1 ports; lan-only checks run inside haedam-portal (it has Python and sits on lan),
and the pfSense check runs from haedam-normal so the request really crosses pfSense.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LAN_PROBE = r"""
import json, os, ssl, sys, urllib.request, base64
kind = sys.argv[1]
if kind == "wazuh":
    req = urllib.request.Request("https://10.250.0.4:55000/security/user/authenticate?raw=true", method="POST",
        headers={"Authorization": "Basic " + base64.b64encode(("wazuh-wui:" + os.environ["P"]).encode()).decode()})
    ctx = ssl._create_unverified_context()  # Wazuh API uses its own self-signed certificate
else:
    req = urllib.request.Request("http://10.250.0.3:8088/api/v1/tickets/open?group_key=__check_stack__",
                                 headers={"X-Response-Key": os.environ["P"]})
    ctx = None
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    body = r.read()
print(r.status, len(body) if kind == "wazuh" else body[:80].decode())
"""


def env():
    pairs = (l.split("=", 1) for l in (ROOT / ".env").read_text("utf-8").splitlines() if "=" in l and not l.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


def http(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return f"{r.status} {r.read()[:60].decode(errors='replace')}"


def docker(*args, stdin=None, environ=None):
    extra = [x for k, v in (environ or {}).items() for x in ("-e", f"{k}={v}")]
    cmd = ["docker", "exec", *(["-i"] if stdin else []), *extra, *args]
    r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout).strip()[-200:])
    return r.stdout.strip()


def main():
    e = env()
    n8n_host_port = e.get("N8N_HOST_PORT", "5678")
    checks = [
        ("portal", lambda: http("http://127.0.0.1:8080/api/v1/health")),
        ("graylog", lambda: http("http://127.0.0.1:9000/api/system/lbstatus")),
        ("n8n", lambda: http(f"http://127.0.0.1:{n8n_host_port}/healthz")),
        ("wazuh", lambda: docker("haedam-portal", "python", "-", "wazuh", stdin=LAN_PROBE,
                                 environ={"P": e["WAZUH_API_PASSWORD"]})),
        ("pfsense", lambda: docker("haedam-normal", "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                   "--max-time", "10", "http://203.0.113.1/api/v1/health")),
        ("ticket-store", lambda: docker("haedam-portal", "python", "-", "ticket", stdin=LAN_PROBE,
                                        environ={"P": e["TICKET_STORE_KEY"]})),
    ]
    failed = 0
    for name, fn in checks:
        try:
            detail = fn()
            ok = detail.startswith("200")
        except Exception as exc:  # any failure is reported, never raised
            detail, ok = f"{type(exc).__name__}: {exc}", False
        failed += not ok
        print(f"{'OK  ' if ok else 'FAIL'} {name:<13} {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
