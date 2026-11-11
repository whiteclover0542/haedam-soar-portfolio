"""Validate MVP source configuration without starting Docker or printing secrets."""

from __future__ import annotations

import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def env_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0])
    return keys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    entrypoint = (ROOT / "infra/pfsense/entrypoint.sh").read_text(encoding="utf-8")
    config = ET.parse(ROOT / "infra/pfsense/config.xml").getroot()
    pfsense_workflow = json.loads((ROOT / "infra/n8n/workflows/haedam-14-pfsense-block.json").read_text(encoding="utf-8"))
    pfsense_pipeline = (ROOT / "infra/graylog/pipelines/pfsense-parse.txt").read_text(encoding="utf-8")
    lite_compose = (ROOT / "compose.lite.yaml").read_text(encoding="utf-8")

    require("${N8N_HOST_PORT:-5678}:5678" in compose, "n8n host-port override is missing")
    require("-serial stdio" in entrypoint, "pfSense serial console is not enabled")
    require("-boot order=cd" in entrypoint, "pfSense disk-first boot order is not configured")
    require(config.findtext("./interfaces/wan/if") == "em0", "pfSense WAN must map to em0")
    require(config.findtext("./interfaces/wan/ipaddr") == "203.0.113.1", "pfSense WAN address mismatch")
    require(config.findtext("./interfaces/lan/if") == "em1", "pfSense LAN must map to em1")
    require(config.findtext("./interfaces/lan/ipaddr") == "10.250.0.1", "pfSense LAN address mismatch")
    require(any(node.get("type") == "n8n-nodes-base.ssh" for node in pfsense_workflow[0]["nodes"]),
            "pfSense workflow must contain its SSH boundary")
    require("haedam-pf-response" in json.dumps(pfsense_workflow), "pfSense workflow command guard is missing")
    require('rule "pfsense: filterlog header"' in pfsense_pipeline, "pfSense Graylog parser header rule is missing")
    require('set_field("pf_src_ip"' in pfsense_pipeline, "pfSense source-IP extraction is missing")
    require('GELF_ENABLED: "0"' in lite_compose, "light mode must disable GELF")
    require('PORTAL_WAN_GATEWAY: ""' in lite_compose, "light mode must omit the pfSense route")

    local_env = ROOT / ".env"
    if local_env.exists():
        missing = env_keys(ROOT / ".env.example") - env_keys(local_env)
        if missing:
            print("WARN local .env is missing example keys:", ", ".join(sorted(missing)))
        else:
            print("OK   local .env contains all documented keys")
    else:
        print("WARN local .env is absent; runtime start will require it")

    print("OK   offline MVP configuration checks passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ET.ParseError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1)
