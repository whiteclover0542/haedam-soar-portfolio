"""Summarize docs/tickets/*/runs.jsonl into docs/정량평가.md and each ticket README's run table.

python tools/summarize_runs.py
Only the blocks between <!-- runs:start --> and <!-- runs:end --> are rewritten.
"""
import json
import re
from datetime import datetime
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
CASES = ["S10", "S8", "S1", "H1"]
EXPECTED_VIA = {"S10": {"portal", "pfsense"}, "S8": {"portal"}, "S1": {"portal"}, "H1": {"portal"}}
RESPONSE_ACTIONS = ("block", "fw_block", "restrict_posting")
# What the attacker / the normal user should get while the response is in force.
REFUSED = {"H1": ("429",)}
NORMAL_OK = {"H1": "201"}


def _ts(t):
    return datetime.fromisoformat(t.replace("Z", "+00:00"))


def blocked_vias(r):
    return {a[0] for a in r.get("actions") or [] if a[1] in RESPONSE_ACTIONS and a[2] in ("applied", "already_applied")}


def auto_ok(r):
    """Every expected block applied without a person, and the effect seen: attacker refused, normal user fine."""
    eff = r.get("effect") or {}
    return (EXPECTED_VIA[r["case"]] <= blocked_vias(r) and eff.get("attacker") in REFUSED.get(r["case"], ("403", "000"))
            and eff.get("normal") == NORMAL_OK.get(r["case"], "200"))


def input_to_block(r):
    if "input_to_block_s" in r:  # present but null = input time unknown; do not reconstruct it
        return r["input_to_block_s"]
    done = [a[3] for a in r.get("actions") or [] if a[1] in RESPONSE_ACTIONS and a[2] in ("applied", "already_applied") and a[3]]
    return round(max((_ts(t) - _ts(r["input_at"])).total_seconds() for t in done), 3) if done else None


def _median(values):
    values = [v for v in values if v is not None]
    return round(median(values), 3) if values else None


def _stats(all_rows):
    baseline = [r for r in all_rows if r.get("baseline")]
    rows = [r for r in all_rows if not r.get("baseline")]
    tried = [r for r in rows if r.get("restore")]
    return {"runs": len(rows),
            "auto_ok": sum(map(auto_ok, rows)),
            "auto_rate": sum(map(auto_ok, rows)) / len(rows) if rows else None,
            "restore_ok": sum((r["restore"] or {}).get("attacker_after") == "200" for r in tried),
            "restore_tried": len(tried),
            "restore_rate": sum((r["restore"] or {}).get("attacker_after") == "200" for r in tried) / len(tried) if tried else None,
            "normal_fail_runs": sum((r.get("effect") or {}).get("normal") not in (None, NORMAL_OK.get(r["case"], "200")) for r in rows),
            "baseline_runs": len(baseline),
            "false_positives": sum(bool(r.get("ticket_id")) for r in baseline),
            "mttd_median": _median(r.get("mttd_s") for r in rows if auto_ok(r)),
            "detect_to_block_median": _median(r.get("detect_to_block_s") for r in rows if auto_ok(r)),
            "input_to_block_median": _median(input_to_block(r) for r in rows if auto_ok(r))}


def summarize(rows):
    out = {c: _stats([r for r in rows if r["case"] == c]) for c in sorted({r["case"] for r in rows})}
    out["total"] = _stats(rows)
    return out


def _fmt(v, unit=""):
    return "—" if v is None else f"{v:g}{unit}" if isinstance(v, (int, float)) else str(v)


def run_table(rows):
    lines = ["| 회차 | 입력(UTC) | 티켓 | 결과 | 자동 대응 | MTTD | 탐지→차단 | 입력→차단 | 공격자 / normal | 해제 후 공격자 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(rows, 1):
        eff = r.get("effect") or {}
        lines.append(f"| {i} | {r['input_at'][:19].replace('T', ' ')} | {r.get('ticket_id') or '—'} | {r.get('result')} | "
                     f"{'예' if auto_ok(r) else '아니요'} | {_fmt(r.get('mttd_s'), '초')} | {_fmt(r.get('detect_to_block_s'), '초')} | "
                     f"{_fmt(input_to_block(r), '초')} | {eff.get('attacker', '—')} / {eff.get('normal', '—')} | "
                     f"{(r.get('restore') or {}).get('attacker_after', '—')} |")
    return "\n".join(lines)


def summary_table(s):
    lines = ["| 티켓 | 회차 | 자동 대응 | 원복 | 정상 사용자 영향 | 오탐(기준선) | MTTD 중앙값 | 탐지→차단 중앙값 | 입력→차단 중앙값 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for k in [c for c in CASES if c in s] + ["total"]:
        v = s[k]
        lines.append(f"| {'전체' if k == 'total' else k} | {v['runs']} | {v['auto_ok']}/{v['runs']} | "
                     f"{v['restore_ok']}/{v['restore_tried']} | {v['normal_fail_runs']}회 | "
                     f"{v['false_positives']}/{v['baseline_runs']} | {_fmt(v['mttd_median'], '초')} | "
                     f"{_fmt(v['detect_to_block_median'], '초')} | {_fmt(v['input_to_block_median'], '초')} |")
    return "\n".join(lines)


def _replace_block(path, body):
    text = path.read_text("utf-8")
    new = re.sub(r"<!-- runs:start -->.*?<!-- runs:end -->", lambda _: f"<!-- runs:start -->\n{body}\n<!-- runs:end -->", text, flags=re.S)
    path.write_text(new, "utf-8", newline="\n")


def main():
    all_rows = []
    for case in CASES:
        f = ROOT / f"docs/tickets/{case}/runs.jsonl"
        rows = [json.loads(l) for l in f.read_text("utf-8").splitlines() if l.strip()] if f.exists() else []
        all_rows += rows
        if rows:
            _replace_block(ROOT / f"docs/tickets/{case}/README.md", run_table(rows))
    s = summarize(all_rows)
    _replace_block(ROOT / "docs/정량평가.md", summary_table(s))
    print(summary_table(s))


if __name__ == "__main__":
    main()
