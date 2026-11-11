from copy import deepcopy

from infra.graylog.bootstrap import notification_url, replace_stream_ids


def test_replace_stream_ids_removes_placeholders():
    definition = {"config": {"streams": ["REPLACE_haedam-portal_stream_id", "REPLACE_pfsense_stream_id"]}}

    result = replace_stream_ids(definition, {"haedam-portal": "portal-id", "pfsense": "pfsense-id"})

    assert result["config"]["streams"] == ["portal-id", "pfsense-id"]
    assert "REPLACE_" not in str(result)
    assert definition != result


def test_notification_url_rewrites_host_docker_internal():
    raw = {"config": {"url": "http://host.docker.internal:5678/webhook/haedam-s8-s10"}}

    result = notification_url(raw, "http://10.250.0.103:5678")

    assert result["config"]["url"] == "http://10.250.0.103:5678/webhook/haedam-s8-s10"
    assert raw["config"]["url"] == "http://host.docker.internal:5678/webhook/haedam-s8-s10"


def test_pipeline_parts_reads_team_export():
    from pathlib import Path
    from infra.graylog.bootstrap import pipeline_parts

    pipeline, rules = pipeline_parts(Path("infra/graylog/pipelines/pfsense-parse.txt").read_text("utf-8"))

    assert pipeline.startswith('pipeline "pfsense-parse"') and pipeline.rstrip().endswith("end")
    assert "//" not in pipeline
    assert '  rule "pfsense: rule block";' in pipeline and '",' not in pipeline  # one rule per line
    assert len(rules) == 9 and all(r.startswith('rule "pfsense: ') and r.endswith("end") for r in rules)


def test_live_body_adds_switches_and_stays_json():
    import json
    from infra.graylog.bootstrap import live_body

    raw = {"config": {"body_template": '{"event_id":"${event.id}","src_ip":"${event.fields.src_ip}"}'}}
    live = json.loads(live_body(raw, True)["config"]["body_template"].replace("${", "").replace("}\"", "\""))
    assert live["dry_run"] is False and live["store_real"] is True and "event_id" in live
    assert live_body(raw, False) == raw


def test_h1_definition_groups_by_username():
    import json
    from pathlib import Path

    d = json.loads(Path("lab/h1/graylog/h1-petition-flood.json").read_text("utf-8"))
    c = d["config"]
    assert c["group_by"] == ["username"] and c["search_within_ms"] == 600000 and c["execute_every_ms"] == 60000
    assert 'event_type:"petition.created"' in c["query"] and "status:201" in c["query"]
    assert c["conditions"]["expression"]["right"]["value"] == 4  # count() > 4, 즉 N=5(초안). 기준선 뒤 바뀌면 함께 고친다
    assert c["streams"] == ["REPLACE_haedam-portal_stream_id"] and d["key_spec"] == ["username"]


def test_bootstrap_lists_h1():
    from infra.graylog.bootstrap import DEFINITIONS, NOTIFICATIONS

    assert DEFINITIONS["lab/h1/graylog/h1-petition-flood.json"] == "haedam-h1"
    assert NOTIFICATIONS["haedam-h1"] == "infra/graylog/notifications/h1-n8n-haedam-h1.json"


def test_bootstrap_lists_h2_with_the_foreign_detail_definition():
    from infra.graylog.bootstrap import DEFINITIONS, NOTIFICATIONS

    assert DEFINITIONS["lab/h2/graylog/h2-petition-access-denied.json"] == "haedam-h2"
    assert NOTIFICATIONS["haedam-h2"] == "infra/graylog/notifications/h2-n8n-haedam-h2.json"


def test_bootstrap_lists_h3_staff_update_definition():
    from infra.graylog.bootstrap import DEFINITIONS, NOTIFICATIONS

    assert DEFINITIONS["lab/h3/graylog/h3-petition-update.json"] == "haedam-h3"
    assert NOTIFICATIONS["haedam-h3"] == "infra/graylog/notifications/h3-n8n-haedam-h3.json"


def test_h3_definition_copies_restore_identifiers_from_the_source_message():
    import json
    from pathlib import Path

    definition = json.loads(Path("lab/h3/graylog/h3-petition-update.json").read_text(encoding="utf-8"))

    fields = definition["field_spec"]
    assert fields["petition_id"]["providers"][0]["template"] == "${source.petition_id}"
    assert fields["revision_id"]["providers"][0]["template"] == "${source.revision_id}"
