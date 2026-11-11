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
CASES = ["S10", "S8", "S1", "S4", "S12", "H1", "H2", "H3"]
EXPECTED_VIA = {"S10": {"portal", "pfsense"}, "S8": {"portal"}, "S1": {"portal"}, "S4": {"portal"}, "S12": {"portal"}, "H1": {"portal"}, "H2": {"portal"}, "H3": {"portal"}}
RESPONSE_ACTIONS = ("block", "fw_block", "restrict_posting", "lock")
# What the attacker / the normal user should get while the response is in force.
REFUSED = {"H1": ("429",), "H3": ("401",), "S4": ("401",)}  # H3: attacker = the locked staff login, normal = the owner's restored petitions
NORMAL_OK = {"H1": "201"}
# Runs from before a fix are left out of the main table and counted separately below it. S10: pfSense read-after-apply and release verdict.
# H1: the ticket store rejected case_id H1. See journal 2026-11-09.
# H3: the staff-name restore returned only the last changed petition (the other two stayed changed). See tickets/H3/README.md.
# S4: runs 1 minute apart hit the portal's login rate limit (20 per source in 5 minutes); spacing raised to 5 minutes.
# The cut sits just after the third run's input so the baseline that followed stays in the main table.
FIXED_AT = {"S10": "2026-11-09T03:46:00+00:00", "H1": "2026-11-09T06:56:00+00:00", "H3": "2026-11-11T05:50:00+00:00",
            "S4": "2026-11-11T06:32:00+00:00"}


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


def restored(r):
    """After release the attacker gets what a normal user gets (H1: can post again)."""
    return (r.get("restore") or {}).get("attacker_after") == NORMAL_OK.get(r["case"], "200")


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
            "restore_ok": sum(map(restored, tried)),
            "restore_tried": len(tried),
            "restore_rate": sum(map(restored, tried)) / len(tried) if tried else None,
            "normal_fail_runs": sum((r.get("effect") or {}).get("normal") not in (None, NORMAL_OK.get(r["case"], "200")) for r in rows),
            "baseline_runs": len(baseline),
            "false_positives": sum(bool(r.get("ticket_id")) for r in baseline),
            "mttd_median": _median(r.get("mttd_s") for r in rows if auto_ok(r)),
            "detect_to_block_median": _median(r.get("detect_to_block_s") for r in rows if auto_ok(r)),
            "input_to_block_median": _median(input_to_block(r) for r in rows if auto_ok(r))}


def after_fix(r):
    return r["case"] not in FIXED_AT or _ts(r["input_at"]) >= _ts(FIXED_AT[r["case"]])


def _by_case(rows):
    out = {c: _stats([r for r in rows if r["case"] == c]) for c in CASES if any(r["case"] == c for r in rows)}
    out["total"] = _stats(rows)
    return out


def summarize(rows):
    """Main table: runs after each fix. "before": the runs from before a fix, counted on their own."""
    out = _by_case([r for r in rows if after_fix(r)])
    out["before"] = _by_case([r for r in rows if not after_fix(r)])
    return out


def _fmt(v, unit=""):
    return "—" if v is None else f"{v:g}{unit}" if isinstance(v, (int, float)) else str(v)


def run_table(rows):
    lines = ["| 회차 | 입력(UTC) | 티켓 | 결과 | 자동 대응 | MTTD | 탐지→차단 | 입력→차단 | 공격자 / normal | 해제 후 공격자 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(rows, 1):
        eff = r.get("effect") or {}
        lines.append(f"| {i} | {r['input_at'][:19].replace('T', ' ')} | {r.get('ticket_id') or '—'} | {r.get('result')}{' (기준선)' if r.get('baseline') else ''} | "
                     f"{'예' if auto_ok(r) else '아니요'} | {_fmt(r.get('mttd_s'), '초')} | {_fmt(r.get('detect_to_block_s'), '초')} | "
                     f"{_fmt(input_to_block(r), '초')} | {eff.get('attacker', '—')} / {eff.get('normal', '—')} | "
                     f"{(r.get('restore') or {}).get('attacker_after', '—')} |")
    return "\n".join(lines)


LABEL = {"total": "전체"}


def _rows(s, cols):
    return [f"| {LABEL.get(k, k)} | " + " | ".join(c(s[k]) for c in cols) + " |" for k in [c for c in CASES if c in s] + ["total"]]


def summary_table(s):
    main = [lambda v: str(v["runs"]), lambda v: f"{v['auto_ok']}/{v['runs']}", lambda v: f"{v['restore_ok']}/{v['restore_tried']}",
            lambda v: f"{v['normal_fail_runs']}회", lambda v: f"{v['false_positives']}/{v['baseline_runs']}",
            lambda v: _fmt(v["mttd_median"], "초"), lambda v: _fmt(v["detect_to_block_median"], "초"),
            lambda v: _fmt(v["input_to_block_median"], "초")]
    lines = ["| 티켓 | 회차 | 자동 대응 | 원복 | 정상 사용자 영향 | 오탐(기준선) | MTTD 중앙값 | 탐지→차단 중앙값 | 입력→차단 중앙값 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"] + _rows(s, main)
    if s["before"]["total"]["runs"]:
        lines += ["", "수정 전 실패 회차(위 표에 넣지 않음. 원인과 수정은 아래 해석)", "",
                  "| 티켓 | 회차 | 자동 대응 | 원복 | 정상 사용자 영향 |", "| --- | --- | --- | --- | --- |"] + _rows(s["before"], main[:4])
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
