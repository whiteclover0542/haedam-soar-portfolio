import json
from pathlib import Path

import pytest

from infra.n8n.make_credentials import attach_credentials, build_credentials

ENV = {"N8N_WEBHOOK_KEY": "w" * 20, "TICKET_STORE_KEY": "t" * 20, "PORTAL_RESPONSE_KEY": "p" * 20,
       "PF_SSH_PRIVATE_KEY": "fake-ssh-key-for-tests"}
WORKFLOWS = sorted(Path("infra/n8n/workflows").glob("*.json"))


def load(path):
    w = json.loads(path.read_text("utf-8"))
    return w[0] if isinstance(w, list) else w


def test_all_referenced_credentials_built():
    built = {c["name"] for c in build_credentials(ENV)}
    referenced = {c["name"] for p in WORKFLOWS for n in load(p)["nodes"] for c in (n.get("credentials") or {}).values()}
    assert referenced and referenced <= built


def test_missing_env_raises():
    env = dict(ENV)
    del env["PORTAL_RESPONSE_KEY"]
    with pytest.raises(KeyError, match="PORTAL_RESPONSE_KEY"):
        build_credentials(env)


def test_attach_sets_ids_on_every_header_auth_node():
    creds = build_credentials(ENV)
    ids = {c["id"] for c in creds}
    for p in WORKFLOWS:
        w = attach_credentials(load(p), creds)
        for n in w["nodes"]:
            pr = n["parameters"]
            if n["type"].endswith("httpRequest") and pr.get("genericAuthType") == "httpHeaderAuth":
                assert n["credentials"]["httpHeaderAuth"]["id"] in ids, (p.name, n["name"])
            for ref in (n.get("credentials") or {}).values():
                assert ref["id"] in ids, (p.name, n["name"])
