"""Derive the H2 n8n main flow from the reviewed S1 portal-IP-block flow.

Run after changing the S1 source:
    python tools/make_h2_workflow.py
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "infra" / "n8n" / "workflows"
SOURCE = WORKFLOWS / "haedam-30-s1-main.json"
TARGET = WORKFLOWS / "haedam-36-h2-main.json"


def build(source: str) -> str:
    replacements = (
        ('"haedamS1Main01"', '"haedamH2Main01"'),
        ("haedam-30 S1", "haedam-36 H2"),
        ("haedam-s1", "haedam-h2"),
        ("S1", "H2"),
    )
    result = source
    for old, new in replacements:
        if old not in result:
            raise ValueError(f"source substitution missing: {old}")
        result = result.replace(old, new)
    json.loads(result)
    return result


def main():
    TARGET.write_text(build(SOURCE.read_text(encoding="utf-8")), encoding="utf-8", newline="")
    print(f"wrote {TARGET.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
