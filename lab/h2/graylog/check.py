import json
from pathlib import Path


definition = json.loads((Path(__file__).with_name("h2-petition-access-denied.json")).read_text(encoding="utf-8"))
config = definition["config"]

assert config["query"] == 'source:haedam-portal AND event_type:"petition.access_denied" AND status:403'
assert config["group_by"] == ["username", "src_ip"]
assert definition["key_spec"] == ["username", "src_ip"]
assert config["search_within_ms"] == 300000
assert config["execute_every_ms"] == 60000
assert config["conditions"]["expression"]["right"]["value"] == 2
assert definition["field_spec"]["case_id"]["providers"][0]["template"] == "H2"

print("H2 Graylog definition check: OK")
