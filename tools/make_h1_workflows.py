"""One-off: derive the H1 workflows from the reviewed S1 main (haedam-30) and account lock (haedam-13).

python tools/make_h1_workflows.py
Plain text substitutions on the raw files keep the originals' formatting, so the H1 files diff cleanly against
their sources. Every substitution must hit; if an original changes, this stops instead of writing a wrong file.
Written by 반소람 (H1). Originals: 김대훈 / 반소람(S1 분기).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / "infra/n8n/workflows"


def js(text):
    """A JavaScript snippet as it appears inside the JSON string of a Code node."""
    return json.dumps(text, ensure_ascii=False)[1:-1]


SUB = ("haedam-13-portal-account-lock.json", "haedam-18-portal-posting.json", [
    ('"haedamAccountLock01"', '"haedamPortalPosting01"'),
    ("haedam-13 포털 계정 잠금 (111)", "haedam-18 포털 민원 작성 제한 (115)"),
    (js("if (b.action !== 'lock') return [{ json: { result: 'failed', detail: 'only lock is automated (해제·재설정은 사람이)', stop: true, ctx } }];"),
     js("if (b.action !== 'restrict') return [{ json: { result: 'failed', detail: 'only restrict is automated (해제는 담당자가)', stop: true, ctx } }];")),
    (js("-111-${b.username}-lock"), js("-115-${b.username}-restrict")),
    (js("return [{ json: { action: 'lock',"), js("return [{ json: { action: 'restrict',")),
    ("/api/v1/response/accounts/lock", "/api/v1/response/accounts/posting"),
    (js("JSON.stringify({ username: $('요청 준비').first().json.username })"),
     js("JSON.stringify({ username: $('요청 준비').first().json.username, restricted: true })")),
])

MAIN = ("haedam-30-s1-main.json", "haedam-35-h1-main.json", [
    ('"haedamS1Main01"', '"haedamH1Main01"'),
    ("haedam-30 S1 계정 탈취 시도 → 출발지 차단 (A)", "haedam-35 H1 민원 도배 → 작성 제한 (A)"),
    ('"haedam-s1"', '"haedam-h1"'),
    ("haedam-s1 caller", "haedam-h1 caller"),
    (js("const missing = ['event_id', 'asset_id', 'src_ip', 'username']"), js("const missing = ['event_id', 'asset_id', 'username']")),
    (js("const p = protectedIp(t.src_ip);"), js("const p = /^[a-z0-9_]{3,40}$/.test(t.username) ? null : 'bad_username';")),
    (js("verdict: 'protected_source', reason: p, case_id: 'S1'"), js("verdict: 'protected_source', reason: p, case_id: 'H1'")),
    (js("case_id: 'S1', title: 'S1 로그인 반복 실패(무차별 대입)', event_id: t.event_id, asset_id: t.asset_id, src_ip: t.src_ip,"),
     js("case_id: 'H1', title: 'H1 민원 도배(작성 제한)', event_id: t.event_id, asset_id: t.asset_id, src_ip: t.src_ip || null,")),
    (js("expected: [{ bot: '112', via: 'portal', action: 'block', target: t.src_ip }]"),
     js("expected: [{ bot: '115', via: 'portal', action: 'restrict_posting', target: t.username }]")),
    (js("dry_run: x.cfg.dry_run, action: 'block', ip: x.src_ip }"), js("dry_run: x.cfg.dry_run, action: 'restrict', username: x.username }")),
    (js("action: { bot: '112', target: x.src_ip, via: 'portal', action: 'block',"),
     js("action: { bot: '115', target: x.username, via: 'portal', action: 'restrict_posting',")),
    (js("const expected = x.expected || [{bot:'112',via:'portal',action:'block',target:x.src_ip}];"),
     js("const expected = x.expected || [{bot:'115',via:'portal',action:'restrict_posting',target:x.username}];")),
    ('"haedamPortalIp01"', '"haedamPortalPosting01"'),
    ("조치1 입력 (포털 IP 차단)", "조치1 입력 (포털 작성 제한)"),
    ("조치1 (포털 IP 차단)", "조치1 (포털 작성 제한)"),
])


def derive(src, dst, subs):
    text = (WF / src).read_text("utf-8")
    for old, new in subs:
        if old not in text:
            raise SystemExit(f"{src}: substitution target not found: {old[:80]}")
        text = text.replace(old, new)
    json.loads(text)
    (WF / dst).write_text(text, "utf-8", newline="")
    print("wrote", dst)


if __name__ == "__main__":
    derive(*SUB)
    derive(*MAIN)
