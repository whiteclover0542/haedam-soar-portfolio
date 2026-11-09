"""Load Haedam detection config into a fresh Graylog. Safe to re-run: anything that exists by title is skipped.

python infra/graylog/bootstrap.py --url http://127.0.0.1:9000
env: GRAYLOG_ADMIN_PASSWORD, N8N_WEBHOOK_KEY
"""
import argparse
import base64
import copy
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
N8N = "http://10.250.0.103:5678"
INPUTS = [
    ("portal GELF TCP", "org.graylog2.inputs.gelf.tcp.GELFTCPInput", 12201),
    ("pfSense Syslog UDP", "org.graylog2.inputs.syslog.udp.SyslogUDPInput", 1514),
    ("Wazuh Raw TCP", "org.graylog2.inputs.raw.tcp.RawTCPInput", 5514),
]
NOTIFICATIONS = {"haedam-s1": "infra/graylog/notifications/s1-n8n-haedam-s1.json",
                 "haedam-s8-s10": "lab/s8s10/graylog/s8-s10-n8n-notification.json"}
DEFINITIONS = {"lab/s1s4/graylog/s1-login-bruteforce.json": "haedam-s1",
               "lab/s8s10/graylog/s8-scan-then-login.json": "haedam-s8-s10",
               "lab/s8s10/graylog/s10-three-layer.json": "haedam-s8-s10"}


def replace_stream_ids(defn, ids):
    text = json.dumps(defn, ensure_ascii=False)
    for name, stream_id in ids.items():
        text = text.replace(f"REPLACE_{name}_stream_id", stream_id)
    return json.loads(text)


def notification_url(raw, base):
    out = copy.deepcopy(raw)
    out["config"]["url"] = re.sub(r"^https?://[^/]+", base, raw["config"]["url"])
    return out


def live_body(raw, live):
    """--live: n8n mains act only when the body carries boolean dry_run:false and store_real:true."""
    out = copy.deepcopy(raw)
    if live:
        out["config"]["body_template"] = '{"dry_run":false,"store_real":true,' + raw["config"]["body_template"].lstrip()[1:]
    return out


def pipeline_parts(text):
    """Split a .txt export into (pipeline source, [rule sources]). The pipeline lives in `// ` comment lines."""
    m = re.search(r"^// (pipeline .*?^// end)", text, re.S | re.M)
    pipeline = re.sub(r"^// ?", "", m.group(1), flags=re.M)
    # The export writes `stage N match either   rule "a", "b"`; Graylog wants the stage line, then `rule "a";` per line.
    pipeline = re.sub(r"^(stage \d+ match \w+)\s+rule (.*)$",
                      lambda s: s.group(1) + "".join(f"\n  rule {r};" for r in re.findall(r'"[^"]*"', s.group(2))),
                      pipeline, flags=re.M)
    rules = re.findall(r'^rule ".*?^end$', text, re.S | re.M)
    return pipeline, rules


class Graylog:
    def __init__(self, url, password):
        self.url = url.rstrip("/")
        self.auth = "Basic " + base64.b64encode(f"admin:{password}".encode()).decode()

    def call(self, method, path, body=None):
        req = urllib.request.Request(self.url + path, method=method,
                                     data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": self.auth, "X-Requested-By": "bootstrap",
                                              "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raise SystemExit(f"{method} {path} -> {e.code}: {e.read()[:300].decode(errors='replace')}")
        return json.loads(raw) if raw else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:9000")
    ap.add_argument("--live", action="store_true", help="alerts make n8n block and record tickets (default: observe)")
    args = ap.parse_args()
    gl = Graylog(args.url, os.environ["GRAYLOG_ADMIN_PASSWORD"])
    key = os.environ["N8N_WEBHOOK_KEY"]
    for _ in range(60):  # Graylog takes a while after the container starts
        try:
            gl.call("GET", "/api/system")  # not lbstatus: it answers text/plain and fails the JSON Accept
            break
        except (urllib.error.URLError, ConnectionError, SystemExit):
            time.sleep(5)
    created = 0

    existing = {i["title"]: i for i in gl.call("GET", "/api/system/inputs")["inputs"]}
    inputs = {}
    for title, kind, port in INPUTS:
        conf = {"bind_address": "0.0.0.0", "port": port, "recv_buffer_size": 262144}
        if "Syslog" in kind:
            conf["timezone"] = "Asia/Seoul"  # pfSense BSD syslog has no zone; default UTC puts messages 9h ahead
        body = {"title": title, "type": kind, "global": True, "configuration": conf}
        if title not in existing:
            inputs[title] = gl.call("POST", "/api/system/inputs", body)["id"]
            created += 1
        else:
            inputs[title] = existing[title]["id"]
            if any(existing[title]["attributes"].get(k) != v for k, v in conf.items()):
                gl.call("PUT", f"/api/system/inputs/{inputs[title]}", body)

    index_set = next(s["id"] for s in gl.call("GET", "/api/system/indices/index_sets")["index_sets"] if s["default"])
    streams = {s["title"]: s["id"] for s in gl.call("GET", "/api/streams")["streams"]}
    for title, rule in [("haedam-portal", {"field": "source", "type": 1, "value": "haedam-portal", "inverted": False}),
                        ("pfsense", {"field": "gl2_source_input", "type": 8,
                                     "value": inputs["pfSense Syslog UDP"], "inverted": False})]:
        if title not in streams:
            streams[title] = gl.call("POST", "/api/streams", {
                "title": title, "index_set_id": index_set, "rules": [rule], "matching_type": "AND",
                "remove_matches_from_default_stream": True})["stream_id"]
            gl.call("POST", f"/api/streams/{streams[title]}/resume")
            created += 1

    pipeline_src, rule_srcs = pipeline_parts((ROOT / "infra/graylog/pipelines/pfsense-parse.txt").read_text("utf-8"))
    have_rules = {r["title"] for r in gl.call("GET", "/api/system/pipelines/rule")}
    for src in rule_srcs:
        if re.match(r'rule "(.*?)"', src).group(1) not in have_rules:
            gl.call("POST", "/api/system/pipelines/rule", {"source": src, "description": ""})
            created += 1
    pipelines = {p["title"]: p["id"] for p in gl.call("GET", "/api/system/pipelines/pipeline")}
    if "pfsense-parse" not in pipelines:
        pid = gl.call("POST", "/api/system/pipelines/pipeline", {"source": pipeline_src, "description": ""})["id"]
        gl.call("POST", "/api/system/pipelines/connections/to_stream",
                {"stream_id": streams["pfsense"], "pipeline_ids": [pid]})
        created += 1

    allow = gl.call("GET", "/api/system/urlwhitelist")
    urls = {e["value"] for e in allow["entries"]}
    for name in NOTIFICATIONS:
        url = f"{N8N}/webhook/{name}"
        if url not in urls:
            allow["entries"].append({"id": str(uuid.uuid4()), "type": "literal", "value": url, "title": name})
            created += 1
    allow["disabled"] = False
    gl.call("PUT", "/api/system/urlwhitelist", allow)

    notes = {n["title"]: n for n in gl.call("GET", "/api/events/notifications?per_page=100")["notifications"]}
    note_ids = {}
    for name, path in NOTIFICATIONS.items():
        raw = live_body(notification_url(json.loads((ROOT / path).read_text("utf-8")), N8N), args.live)
        raw["config"]["headers"] = f"X-Haedam-Key:{key}"  # n8n webhooks use Header Auth with this name
        if raw["title"] not in notes:
            note_ids[name] = gl.call("POST", "/api/events/notifications", raw)["id"]
            created += 1
            continue
        note_ids[name] = notes[raw["title"]]["id"]
        if notes[raw["title"]]["config"].get("body_template") != raw["config"]["body_template"]:
            gl.call("PUT", f"/api/events/notifications/{note_ids[name]}", {**raw, "id": note_ids[name]})
    print("mode:", "live (dry_run:false, store_real:true)" if args.live else "observe (n8n defaults)")

    defs = {d["title"] for d in gl.call("GET", "/api/events/definitions?per_page=100")["event_definitions"]}
    for path, note in DEFINITIONS.items():
        defn = replace_stream_ids(json.loads((ROOT / path).read_text("utf-8")), streams)
        if defn["title"] not in defs:
            defn["notifications"] = [{"notification_id": note_ids[note]}]
            gl.call("POST", "/api/events/definitions?schedule=true", defn)
            created += 1

    print(f"생성 {created}")


if __name__ == "__main__":
    sys.exit(main())
