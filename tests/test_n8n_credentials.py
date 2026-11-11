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


def test_h1_workflows_derived():
    main = load(Path("infra/n8n/workflows/haedam-35-h1-main.json"))
    sub = load(Path("infra/n8n/workflows/haedam-18-portal-posting.json"))
    assert main["id"] == "haedamH1Main01" and sub["id"] == "haedamPortalPosting01"
    text = json.dumps(main, ensure_ascii=False)
    assert "haedam-h1" in text and "haedamPortalPosting01" in text and "haedamPortalIp01" not in text
    assert "restrict_posting" in text and "'112'" not in text
    sub_text = json.dumps(sub, ensure_ascii=False)
    # restricted는 action에서 파생된다(restrict→true, release→false). 본문은 그 값을 동적으로 보낸다(해제도 같은 워크플로로).
    assert ("/api/v1/response/accounts/posting" in sub_text and "b.action === 'restrict'" in sub_text
            and "restricted: $('" in sub_text and "/accounts/lock" not in sub_text)


def test_h2_workflow_is_a_separate_portal_ip_block_flow():
    main = load(Path("infra/n8n/workflows/haedam-36-h2-main.json"))
    text = json.dumps(main, ensure_ascii=False)

    assert main["id"] == "haedamH2Main01"
    assert "haedam-h2" in text and "haedamPortalIp01" in text
    assert "case_id: 'H2'" in text and "action: 'block'" in text


def test_discord_is_optional_and_wired_when_set():
    assert "discordWebhookApi" not in {c["type"] for c in build_credentials(ENV)}
    creds = build_credentials({**ENV, "DISCORD_WEBHOOK_URL": "https://example.invalid/webhook"})
    w = attach_credentials(load(Path("infra/n8n/workflows/haedam-11-discord-notify.json")), creds)
    node = next(n for n in w["nodes"] if n["type"] == "n8n-nodes-base.discord")
    assert node["credentials"]["discordWebhookApi"]["id"] in {c["id"] for c in creds}


def test_discord_notification_shows_risk_score_and_dashboard_link():
    workflow = json.loads(Path("infra/n8n/workflows/haedam-11-discord-notify.json").read_text(encoding="utf-8"))[0]
    code = next(node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.code" and node["name"].startswith("Discord"))["parameters"]["jsCode"]

    assert "risk_score" in code
    assert "위험도:" in code
    assert "dashboard_url" in code
    assert "보안 대시보드 열기" in code
    assert "심각" in code
