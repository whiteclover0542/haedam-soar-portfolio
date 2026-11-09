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
