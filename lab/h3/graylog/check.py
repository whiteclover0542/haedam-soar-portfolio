import json
from pathlib import Path

definition = json.loads(Path(__file__).with_name("h3-petition-update.json").read_text(encoding="utf-8"))
config = definition["config"]
assert config["query"] == 'source:haedam-portal AND event_type:"petition.updated" AND revision_id:*'
assert config["group_by"] == definition["key_spec"] == ["username"]
assert config["search_within_ms"] == 300000 and config["execute_every_ms"] == 60000
assert config["conditions"]["expression"]["right"]["value"] == 2
assert {"petition_id", "revision_id", "case_id"} <= set(definition["field_spec"])
assert definition["field_spec"]["revision_id"]["data_type"] == "string"
assert definition["field_spec"]["petition_id"]["providers"][0]["template"] == "${source.petition_id}"
assert definition["field_spec"]["revision_id"]["providers"][0]["template"] == "${source.revision_id}"
print("H3 Graylog definition check: OK")
