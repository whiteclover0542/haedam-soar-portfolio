"""실습 제어판: 버튼으로 S10·S8·S1 공격 → 효과 확인 → 해제. 반소람 작성.

python lab/panel.py        → http://127.0.0.1:8099 (브라우저가 자동으로 열림)
버튼은 docs/실습-안내.md의 명령을 그대로 실행하고, 실행한 명령과 결과를 화면 로그에 보여 준다.
127.0.0.1에만 열고, 시작할 때마다 만드는 토큰이 없는 요청은 거절한다(다른 사이트가 버튼을 대신 누르지 못하게).
"""
import json
import secrets
import sys
import threading
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.run_ticket import (NORMAL, ROOT, SEAT, SRC, TICKETS, env, get, http_code, portal_login,  # noqa: E402
                            sh, tickets_for)

PORT = 8099
TOKEN = secrets.token_urlsafe(16)
CASES = ["S10", "S8", "S1"]
S1_USER = {}  # 이번 실행에서 만든 S1 피해자 계정(이름·비밀번호는 메모리에만)
LOCK = threading.Lock()  # 공격 버튼을 동시에 두 번 누르지 않게


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def attack(case):
    src, log = SRC[case], []
    if case in ("S10", "S8"):
        if case == "S10":
            cmd = f"ping -I {src} -c 1 -W 1 203.0.113.1"
            sh("docker", "exec", "haedam-attacker", *cmd.split(), check=False)
            log.append({"step": "경계 신호: ping(pfSense가 막고 Graylog로 기록)", "cmd": "docker exec haedam-attacker " + cmd,
                        "result": "응답 없음(차단)"})
        sh("docker", "cp", str(ROOT / "tools/s8s10_input.py"), "haedam-attacker:/lab/s8s10_input.py")
        run = "panel" + datetime.now().strftime("%H%M%S")
        cmd = f"python /lab/s8s10_input.py --case {case} --run-id {run} --out /tmp/{run}.json --execute"
        sh("docker", "exec", "haedam-attacker", *cmd.split())
        statuses = [x["status"] for x in json.loads(sh("docker", "exec", "haedam-attacker", "cat", f"/tmp/{run}.json"))["http"]]
        log.append({"step": "스캔(404) → 보안 토큰(200) → 틀린 로그인(401)", "cmd": "docker exec haedam-attacker " + cmd,
                    "result": statuses})
    else:
        user, pw = "zz_a_s1_" + datetime.now().strftime("%H%M%S"), secrets.token_urlsafe(12)
        S1_USER.update(user=user, pw=pw)
        reg = portal_login("haedam-normal", NORMAL, "register", user, pw=pw)["statuses"]
        log.append({"step": f"피해자 계정 {user} 가입(정상 시민)", "cmd": f"docker exec -e PW haedam-normal python /lab/portal_login.py --source {NORMAL} register {user}",
                    "result": reg})
        fails = portal_login("haedam-attacker", src, "fail", user, "9")["statuses"]
        log.append({"step": "같은 계정에 틀린 비밀번호 9번", "cmd": f"docker exec haedam-attacker python /lab/portal_login.py --source {src} fail {user} 9",
                    "result": fails})
    log.append({"step": "Graylog가 1분마다 평가 → 보통 30~70초 뒤 티켓·차단", "cmd": "", "result": "기다리는 중"})
    return log


def effect(case):
    src = SRC[case]
    out = [{"step": "공격자", "cmd": f"docker exec haedam-attacker curl --interface {src} http://203.0.113.1/api/v1/health",
            "result": http_code("haedam-attacker", src)},
           {"step": "정상 시민", "cmd": "docker exec haedam-normal curl http://203.0.113.1/api/v1/health",
            "result": http_code("haedam-normal", NORMAL)}]
    if case == "S1" and S1_USER:
        login = portal_login("haedam-normal", NORMAL, "login", S1_USER["user"], pw=S1_USER["pw"])["statuses"]
        out.append({"step": f"계정 주인이 {S1_USER['user']}로 로그인", "cmd": "portal_login.py login", "result": login})
    return out


def group_key(case):
    return S1_USER.get("user", "-") if case == "S1" else SRC[case]


def latest_ticket(case):
    items = tickets_for(group_key(case))
    if not items:
        return None
    t = max(items.values(), key=lambda t: t["updated_at"])
    detail = get(f"{TICKETS}/{t['ticket_id']}")["ticket"]
    return {"ticket_id": t["ticket_id"], "case_id": detail["case_id"], "status": detail["status"],
            "mttd_seconds": t.get("mttd_seconds"),
            "actions": [f"{a['via']} {a['action']} → {a['result']}" for a in detail.get("actions", [])]}


def release(case):
    t = latest_ticket(case)
    if not t:
        return [{"step": "해제할 티켓이 없음", "cmd": "", "result": "-"}]
    body = json.dumps({"seat": SEAT[case], "case_id": t["case_id"], "group_key": group_key(case), "approver": "실습 제어판",
                       "dry_run": False, "reason": "실습 원복"}).encode()
    req = urllib.request.Request("http://127.0.0.1:5678/webhook/haedam-release", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-Haedam-Key": env()["N8N_WEBHOOK_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        rel = json.loads(r.read())
    rel = rel[0] if isinstance(rel, list) else rel
    steps = [f"{'pfSense' if s.get('step') == 1 else '포털'} {s.get('result')}" for s in rel.get("steps") or []]
    return [{"step": "n8n haedam-50 해제(경계 → 앱 순서)", "cmd": "POST /webhook/haedam-release", "result": steps or rel.get("verdict")},
            {"step": "해제 후 공격자", "cmd": "", "result": http_code("haedam-attacker", SRC[case])}]


def state():
    out = {}
    for c in CASES:
        try:
            out[c] = {"src": SRC[c], "ticket": latest_ticket(c)}
        except Exception as exc:  # 티켓 저장소가 잠깐 안 될 때도 화면은 유지
            out[c] = {"src": SRC[c], "ticket": None, "error": type(exc).__name__}
    return out


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, kind="application/json"):
        data = body.encode() if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/":
            return self._send(200, PAGE.replace("__TOKEN__", TOKEN), "text/html")
        if self.path == "/api/state" and self.headers.get("X-Panel-Token") == TOKEN:
            return self._send(200, state())
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.headers.get("X-Panel-Token") != TOKEN:
            return self._send(403, {"error": "token"})
        parts = self.path.strip("/").split("/")  # api/<action>/<case>
        if len(parts) != 3 or parts[0] != "api" or parts[2] not in CASES or parts[1] not in ("attack", "effect", "release"):
            return self._send(404, {"error": "not found"})
        action, case = parts[1], parts[2]
        if not LOCK.acquire(blocking=False):
            return self._send(409, {"error": "다른 버튼이 아직 실행 중입니다"})
        try:
            log = {"attack": attack, "effect": effect, "release": release}[action](case)
            self._send(200, {"at": now(), "case": case, "action": action, "log": log})
        except Exception as exc:
            self._send(500, {"at": now(), "case": case, "action": action, "log": [{"step": "실패", "cmd": "", "result": str(exc)[-300:]}]})
        finally:
            LOCK.release()

    def log_message(self, *args):
        pass


PAGE = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>해담 SOAR 실습</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--mute:#5d6676;--line:#dde1e7;--red:#c8372d;--blue:#2459c4;--green:#1f7a4d}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--ink:#e6e9ef;--mute:#9aa3b2;--line:#2e343e;--red:#ff6b5e;--blue:#7aa2ff;--green:#4cc38a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,"Malgun Gothic",sans-serif}
header{padding:20px 24px 8px}h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:var(--mute)}
nav{display:flex;flex-wrap:wrap;gap:8px;padding:8px 24px 16px}nav a{color:var(--blue);text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:4px 10px;background:var(--card)}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px;padding:0 24px 24px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.card h2{margin:0;font-size:17px}.card .who{color:var(--mute);font-size:13px;margin:2px 0 10px}.card .desc{margin:0 0 12px}
.btns{display:flex;gap:8px;flex-wrap:wrap}button{font:inherit;border-radius:6px;padding:7px 14px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
button.attack{background:var(--red);border-color:var(--red);color:#fff}button:disabled{opacity:.5;cursor:wait}
.ticket{margin-top:12px;border-top:1px solid var(--line);padding-top:10px;font-size:14px}.ticket b{font-weight:600}.ok{color:var(--green)}
#log{margin:0 24px 32px;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;max-height:45vh;overflow:auto}
#log h2{font-size:16px;margin:0 0 8px}.entry{border-top:1px solid var(--line);padding:6px 0}.entry code{color:var(--mute);font-size:12px;word-break:break-all}
</style></head><body>
<header><h1>해담 SOAR 실습 제어판</h1><p>버튼은 <code>docs/실습-안내.md</code>의 명령을 그대로 실행합니다. 같은 출발지는 15분(S1 30분)에 한 번씩.</p></header>
<nav><a href="http://127.0.0.1:9000" target="_blank">Graylog</a><a href="http://127.0.0.1:5678" target="_blank">n8n</a>
<a href="http://127.0.0.1:8089" target="_blank">티켓 대시보드</a><a href="https://127.0.0.1:8443" target="_blank">pfSense</a><a href="http://127.0.0.1:8080" target="_blank">민원 포털</a></nav>
<main id="cards"></main>
<section id="log"><h2>실행 기록</h2><div id="entries"></div></section>
<script>
const TOKEN="__TOKEN__";
const INFO={S10:["경계 차단 → 스캔 → 로그인 시도","ping(pfSense 차단) + 스캔 + 틀린 로그인. 포털과 pfSense 모두에서 막힙니다. 공격자 기대값 000(연결 불가)."],
S8:["포털 스캔 → 로그인 시도","ping 없이 스캔 + 틀린 로그인. 포털에서만 막습니다. 공격자 기대값 403."],
S1:["로그인 무차별 대입","같은 계정에 틀린 비밀번호 9번. 출발지만 막고 계정 주인은 정상 로그인(200)."]};
const H={"X-Panel-Token":TOKEN};
document.getElementById("cards").innerHTML=Object.keys(INFO).map(c=>`<section class="card"><h2>${c} · ${INFO[c][0]}</h2>
<div class="who" id="src-${c}"></div><p class="desc">${INFO[c][1]}</p>
<div class="btns"><button class="attack" onclick="run('attack','${c}',this)">공격</button><button onclick="run('effect','${c}',this)">효과 확인</button><button onclick="run('release','${c}',this)">해제</button></div>
<div class="ticket" id="t-${c}">티켓 없음</div></section>`).join("");
function esc(s){return String(s).replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]))}
async function run(action,c,btn){document.querySelectorAll("button").forEach(b=>b.disabled=true);
 try{const r=await fetch(`/api/${action}/${c}`,{method:"POST",headers:H});const d=await r.json();
  const label={attack:"공격",effect:"효과 확인",release:"해제"}[action]||action;
  const rows=(d.log||[{step:d.error,result:""}]).map(x=>`<div>${esc(x.step)} → <b>${esc(JSON.stringify(x.result))}</b>${x.cmd?`<br><code>${esc(x.cmd)}</code>`:""}</div>`).join("");
  document.getElementById("entries").insertAdjacentHTML("afterbegin",`<div class="entry"><b>${new Date().toLocaleTimeString()} ${c} ${label}</b>${rows}</div>`);}
 finally{document.querySelectorAll("button").forEach(b=>b.disabled=false);refresh();}}
async function refresh(){try{const s=await (await fetch("/api/state",{headers:H})).json();
 for(const c in s){document.getElementById("src-"+c).textContent="출발지 "+s[c].src;const t=s[c].ticket;
  document.getElementById("t-"+c).innerHTML=t?`<b>${t.ticket_id}</b> · 상태 <b class="${t.status==='restored'?'ok':''}">${t.status}</b>${t.mttd_seconds!=null?` · MTTD ${t.mttd_seconds}초`:""}<br>${t.actions.map(esc).join("<br>")||"조치 없음"}`:"이 출발지의 티켓 없음";}}catch(e){}}
refresh();setInterval(refresh,5000);
</script></body></html>"""


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"실습 제어판: http://127.0.0.1:{PORT}  (끄려면 Ctrl+C)")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    server.serve_forever()
