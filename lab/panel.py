"""실습 제어판: 버튼으로 S10·S8·S1·H1 공격 → 효과 확인 → 해제. A 작성.

python lab/panel.py        → http://127.0.0.1:8099 (브라우저가 자동으로 열림)
버튼은 docs/실습-안내.md의 명령을 그대로 실행하고, 실행한 명령과 결과를 화면 로그에 보여 준다.
127.0.0.1에만 열고, 시작할 때마다 만드는 토큰이 없는 요청은 거절한다(다른 사이트가 버튼을 대신 누르지 못하게).
"""
import json
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.run_ticket import (H1_POSTS, NORMAL, ROOT, SEAT, SRC, TICKETS, env, get, http_code, portal_login,  # noqa: E402
                            portal_posting, sh, tickets_for)
from lab.h2.input import run_h2  # noqa: E402

PORT = 8099
TOKEN = secrets.token_urlsafe(16)
CASES = ["H1", "H2", "H3", "S1", "S4", "S7", "S8", "S10", "S12"]
PENDING_CASES = {"H3", "S4", "S7", "S12"}
H2_GUIDE_PATH = ROOT / "lab" / "h2" / "README.md"
USERS = {}    # S1·H1 이번 실행에서 만든 계정 {"user", "pw"} (이름·비밀번호는 메모리에만)
RUNS = {}     # case → {"at": 공격 시각, "effect": 마지막 효과, "released": 해제 결과}
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
    elif case == "H2":
        stamp = datetime.now().strftime("%H%M%S")
        user, pw = "zz_a_h2_" + stamp, secrets.token_urlsafe(12)
        victim, victim_pw = "zz_v_h2_" + stamp, secrets.token_urlsafe(12)
        result = run_h2(portal_login, attacker=user, attacker_password=pw, victim=victim, victim_password=victim_pw,
                        attacker_source=src, normal_source=NORMAL)
        USERS[case] = {"user": user, "pw": pw, "victim": victim, "victim_pw": victim_pw,
                       "foreign_ids": result["victim_petition_ids"], "own_id": result["attacker_petition_id"]}
        log.append({"step": "fresh victim petitions created", "cmd": "portal_login.py post victim 3", "result": result["victim_petition_ids"]})
        log.append({"step": "attacker requested three foreign petition details", "cmd": "portal_login.py detail attacker <foreign ids>",
                    "result": result["statuses"]})
        log.append({"step": "attacker self-petition access control", "cmd": "portal_login.py detail attacker <own id>",
                    "result": result["own_status"]})
    elif case == "H1":
        user, pw = "zz_a_h1_" + datetime.now().strftime("%H%M%S"), secrets.token_urlsafe(12)
        USERS[case] = {"user": user, "pw": pw}
        reg = portal_login("haedam-attacker", src, "register", user, pw=pw)["statuses"]
        log.append({"step": f"공격자 계정 {user} 가입", "cmd": f"docker exec -e PW haedam-attacker python /lab/portal_login.py --source {src} register {user}",
                    "result": reg})
        posts = portal_login("haedam-attacker", src, "post", user, str(H1_POSTS), pw=pw)["statuses"]
        log.append({"step": f"민원 {H1_POSTS}건 연달아 등록(201)", "cmd": f"docker exec -e PW haedam-attacker python /lab/portal_login.py --source {src} post {user} {H1_POSTS}",
                    "result": posts})
    else:
        user, pw = "zz_a_s1_" + datetime.now().strftime("%H%M%S"), secrets.token_urlsafe(12)
        USERS[case] = {"user": user, "pw": pw}
        reg = portal_login("haedam-normal", NORMAL, "register", user, pw=pw)["statuses"]
        log.append({"step": f"피해자 계정 {user} 가입(정상 시민)", "cmd": f"docker exec -e PW haedam-normal python /lab/portal_login.py --source {NORMAL} register {user}",
                    "result": reg})
        fails = portal_login("haedam-attacker", src, "fail", user, "9")["statuses"]
        log.append({"step": "같은 계정에 틀린 비밀번호 9번", "cmd": f"docker exec haedam-attacker python /lab/portal_login.py --source {src} fail {user} 9",
                    "result": fails})
    log.append({"step": "Graylog가 1분마다 평가 → 보통 30~70초 뒤 티켓·차단", "cmd": "", "result": "기다리는 중"})
    RUNS[case] = {"at": datetime.now(timezone.utc), "effect": None, "released": None}
    return log


def h1_effect():
    """H1: the flooding account may not post (429) but can still log in and list; another citizen posts fine (201)."""
    src, u = SRC["H1"], USERS.get("H1")
    if not u:
        return [{"step": "이번 실행에서 [공격]을 먼저 누르세요", "cmd": "", "result": "-"}]
    again = portal_login("haedam-attacker", src, "post", u["user"], "1", pw=u["pw"])
    other, other_pw = "zz_a_h1n_" + datetime.now().strftime("%H%M%S"), secrets.token_urlsafe(12)
    portal_login("haedam-normal", NORMAL, "register", other, pw=other_pw)
    normal = portal_login("haedam-normal", NORMAL, "post", other, "1", pw=other_pw)["statuses"][0]
    return [{"step": f"공격 계정 {u['user']} 민원 1건 더", "cmd": "portal_login.py post 1", "result": str(again["statuses"][0])},
            {"step": "같은 계정 로그인 · 내 민원 목록", "cmd": "", "result": [again["login"], again["list"]]},
            {"step": "다른 정상 시민 민원 1건", "cmd": "portal_login.py post 1", "result": str(normal)}]


def h2_effect():
    """H2 response blocks only the attack source; the victim still reads own data."""
    u = USERS.get("H2")
    if not u:
        return [{"step": "Run attack first", "cmd": "", "result": "-"}]
    victim = portal_login("haedam-normal", NORMAL, "detail", u["victim"], str(u["foreign_ids"][0]), pw=u["victim_pw"])
    return [{"step": "attacker source health check", "cmd": "curl /api/v1/health", "result": http_code("haedam-attacker", SRC["H2"])},
            {"step": "victim reads own petition", "cmd": "portal_login.py detail victim <own id>",
             "result": str(victim["statuses"][0])}]


def effect(case):
    src = SRC[case]
    if case == "H1":
        out = h1_effect()
        if case in RUNS and len(out) == 3:
            RUNS[case]["effect"] = {"attacker": out[0]["result"], "normal": out[2]["result"]}
        return out
    if case == "H2":
        out = h2_effect()
        if case in RUNS and len(out) == 2:
            RUNS[case]["effect"] = {"attacker": out[0]["result"], "normal": out[1]["result"]}
        return out
    out = [{"step": "공격자", "cmd": f"docker exec haedam-attacker curl --interface {src} http://203.0.113.1/api/v1/health",
            "result": http_code("haedam-attacker", src)},
           {"step": "정상 시민", "cmd": "docker exec haedam-normal curl http://203.0.113.1/api/v1/health",
            "result": http_code("haedam-normal", NORMAL)}]
    if case == "S1" and USERS.get("S1"):
        u = USERS["S1"]
        login = portal_login("haedam-normal", NORMAL, "login", u["user"], pw=u["pw"])["statuses"]
        out.append({"step": f"계정 주인이 {u['user']}로 로그인", "cmd": "portal_login.py login", "result": login})
    if case in RUNS:
        RUNS[case]["effect"] = {"attacker": out[0]["result"], "normal": out[1]["result"]}
    return out


def group_key(case):
    return USERS.get(case, {}).get("user", "-") if case in ("S1", "H1", "H2") else SRC[case]


def latest_ticket(case):
    items = tickets_for(group_key(case))
    if not items:
        return None
    t = max(items.values(), key=lambda t: t["updated_at"])
    detail = get(f"{TICKETS}/{t['ticket_id']}")["ticket"]
    return {"ticket_id": t["ticket_id"], "case_id": detail["case_id"], "status": detail["status"],
            "mttd_seconds": t.get("mttd_seconds"), "updated_at": t["updated_at"], "raw_actions": detail.get("actions", []),
            "actions": [f"{a['via']} {a['action']} → {a['result']}" for a in detail.get("actions", [])]}


def release(case):
    t = latest_ticket(case)
    if not t:
        return [{"step": "해제할 티켓이 없음", "cmd": "", "result": "-"}]
    if case == "H1":  # 담당자가 포털 대응 API로 작성 제한을 푼다(haedam-50은 IP 차단만 푼다)
        u = USERS["H1"]
        code = portal_posting(env(), u["user"], False)
        after = str(portal_login("haedam-attacker", SRC[case], "post", u["user"], "1", pw=u["pw"])["statuses"][0])
        if case in RUNS:
            RUNS[case]["released"] = {"steps": [f"포털 작성 제한 해제 {code}"], "attacker": after}
        return [{"step": "담당자: 포털 대응 API로 작성 제한 해제", "cmd": "POST /api/v1/response/accounts/posting", "result": code},
                {"step": "해제 후 공격 계정 민원 1건", "cmd": "", "result": after}]
    body = json.dumps({"seat": SEAT[case], "case_id": t["case_id"], "group_key": group_key(case), "approver": "실습 제어판",
                       "dry_run": False, "reason": "실습 원복"}).encode()
    req = urllib.request.Request("http://127.0.0.1:5678/webhook/haedam-release", data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-Haedam-Key": env()["N8N_WEBHOOK_KEY"]})
    with urllib.request.urlopen(req, timeout=120) as r:
        rel = json.loads(r.read())
    rel = rel[0] if isinstance(rel, list) else rel
    steps = [f"{'pfSense' if s.get('step') == 1 else '포털'} {s.get('result')}" for s in rel.get("steps") or []]
    after = http_code("haedam-attacker", SRC[case])
    if case in RUNS:
        RUNS[case]["released"] = {"steps": steps, "attacker": after}
    return [{"step": "n8n haedam-50 해제(경계 → 앱 순서)", "cmd": "POST /webhook/haedam-release", "result": steps or rel.get("verdict")},
            {"step": "해제 후 공격자", "cmd": "", "result": after}]


EXPECT = {"S10": ("000", "pfSense에서 연결 자체가 끊김"), "S8": ("403", "포털이 IP_BLOCKED로 거절"),
          "S1": ("403", "포털이 IP_BLOCKED로 거절"), "H1": ("429", "그 계정의 민원 작성만 막힘, 로그인·조회는 유지")}
NORMAL_OK = {"H1": "201"}  # 나머지는 200


EXPECT["H2"] = ("403", "attacker source blocked after the H2 alert")
NORMAL_OK["H2"] = "200"


def graylog_count(case, since):
    q = f"username:{group_key(case)}" if case in ("S1", "H1", "H2") else f"src_ip:{SRC[case]}"
    pw = env()["GRAYLOG_ADMIN_PASSWORD"]
    url = ("http://127.0.0.1:9000/api/search/universal/absolute?limit=1&query=" + urllib.parse.quote(q)
           + "&from=" + since.strftime("%Y-%m-%dT%H:%M:%S.000Z") + "&to=" + datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
    req = urllib.request.Request(url, headers={"Accept": "application/json", "Authorization":
                                               "Basic " + __import__("base64").b64encode(f"admin:{pw}".encode()).decode()})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["total_results"]


def timeline(case):
    run = RUNS.get(case)
    if not run:
        return {"steps": [], "elapsed": None}
    at = run["at"]
    elapsed = int((datetime.now(timezone.utc) - at).total_seconds())
    t = latest_ticket(case)
    if t and t["updated_at"] < at.isoformat():
        t = None  # 이번 공격 전의 티켓
    logs = graylog_count(case, at)
    acts = (t or {}).get("raw_actions", [])
    blocks = [a for a in acts if a["action"] in ("block", "fw_block", "restrict_posting") and a["result"] in ("applied", "already_applied")]
    need = {"portal", "pfsense"} if case == "S10" else {"portal"}
    done = need <= {a["via"] for a in blocks}
    if t and done and run["effect"] is None and run["released"] is None:  # 차단이 들어가면(해제 전) 효과를 한 번 자동으로 본다
        if case in ("H1", "H2"):
            effect(case)
        else:
            run["effect"] = {"attacker": http_code("haedam-attacker", SRC[case]), "normal": http_code("haedam-normal", NORMAL)}
    eff, rel = run["effect"], run["released"]
    want, why = EXPECT[case]
    ok = NORMAL_OK.get(case, "200")
    st = lambda ok, wait=True: "done" if ok else ("wait" if wait else "bad")
    steps = [
        {"name": "① 공격 보냄", "state": "done", "text": f"{SRC[case]}에서 입력을 보냈습니다.", "link": None},
        {"name": "② Graylog에 로그 도착", "state": st(logs > 0), "link": "http://127.0.0.1:9000/search",
         "text": f"이번 공격 뒤 이 출발지 로그 {logs}건." if logs else "포털·pfSense 로그가 Graylog에 들어오기를 기다리는 중."},
        {"name": "③ 탐지 (Graylog 경보)", "state": st(bool(t)), "link": "http://127.0.0.1:9000/alerts",
         "text": (f"경보 → n8n 호출 → 티켓 {t['ticket_id']} 생성." if t else
                  f"Graylog가 1분마다 조건을 확인합니다. 공격 뒤 {elapsed}초 경과(보통 30~70초).")},
        {"name": "④ 자동 대응 (n8n)", "state": st(done, wait=not (t and elapsed > 240)), "link": "http://127.0.0.1:5678/home/executions",
         "text": ("차단 적용: " + ", ".join(f"{a['via']} {a['result']}" for a in blocks)) if blocks else
                 ("조치를 기다리는 중." if t else "탐지 뒤에 시작됩니다.")
                 + (" (S10은 포털과 pfSense 둘 다)" if case == "S10" else "")},
        {"name": "⑤ 효과", "state": st(bool(eff) and eff["attacker"] == want and eff["normal"] == ok, wait=not eff),
         "link": None,
         "text": (f"공격자 {eff['attacker']}(기대 {want}: {why}), 정상 시민 {eff['normal']}(기대 {ok})." if eff
                  else "차단이 적용되면 자동으로 확인합니다.")},
        {"name": "⑥ 해제 (사람이 확인 후)", "state": st(bool(rel) and rel["attacker"] == ok, wait=not rel), "link": "http://127.0.0.1:8089",
         "text": (f"{' → '.join(rel['steps']) or '단계 없음'} · 공격자 다시 {rel['attacker']}." if rel
                  else "효과를 확인했으면 [해제]를 누릅니다. " + ("담당자가 포털 대응 API로 작성 제한을 풉니다." if case == "H1"
                                                         else "pfSense를 먼저 풀고 포털을 풉니다."))},
    ]
    return {"steps": steps, "elapsed": elapsed, "ticket": t and {k: t[k] for k in ("ticket_id", "status", "mttd_seconds")}}


def pending_state(case):
    result = {
        "src": "연결 전",
        "pending": True,
        "steps": [{
            "name": "연결 대기",
            "state": "wait",
            "text": f"{case} 실습 도구와 탐지·대응 흐름을 연결한 뒤 실행할 수 있습니다.",
        }],
    }
    if case == "H2":
        result["guide_url"] = "/guide/h2"
    return result


def state():
    out = {}
    for c in CASES:
        if c in PENDING_CASES:
            out[c] = pending_state(c)
            continue
        try:
            out[c] = {"src": SRC[c], **timeline(c)}
        except Exception as exc:  # 한 구성이 잠깐 안 될 때도 화면은 유지
            out[c] = {"src": SRC[c], "steps": [], "error": f"{type(exc).__name__}: {str(exc)[:120]}"}
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
        if self.path == "/guide/h2":
            return self._send(200, H2_GUIDE_PATH.read_text(encoding="utf-8"), "text/markdown")
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
        if case in PENDING_CASES:
            return self._send(409, {"error": "이 케이스는 아직 연결 전입니다."})
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
:root{--bg:#f6f7f9;--card:#fff;--ink:#1d2330;--mute:#5d6676;--line:#dde1e7;--red:#c8372d;--blue:#2459c4;--green:#1f7a4d;--amber:#a86400}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--ink:#e6e9ef;--mute:#9aa3b2;--line:#2e343e;--red:#ff6b5e;--blue:#7aa2ff;--green:#4cc38a;--amber:#f0b44c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,"Malgun Gothic",sans-serif}
header{padding:20px 24px 4px}h1{margin:0;font-size:20px}header p{margin:4px 0 0;color:var(--mute)}
nav{display:flex;flex-wrap:wrap;gap:8px;padding:10px 24px 16px}nav a{color:var(--blue);text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:4px 10px;background:var(--card)}
.tabs{display:flex;gap:8px;padding:0 24px}.tabs button{font:inherit;border:1px solid var(--line);border-bottom:none;border-radius:8px 8px 0 0;padding:8px 16px;background:var(--bg);color:var(--mute);cursor:pointer}
.tabs button.on{background:var(--card);color:var(--ink);font-weight:600}
.panel{margin:0 24px 24px;background:var(--card);border:1px solid var(--line);border-radius:0 10px 10px 10px;padding:18px 20px}
.top{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px;align-items:flex-start}.top h2{margin:0;font-size:18px}.top p{margin:4px 0 0;color:var(--mute);max-width:640px}
.btns{display:flex;gap:8px}.btns button{font:inherit;border-radius:6px;padding:8px 16px;border:1px solid var(--line);background:var(--card);color:var(--ink);cursor:pointer}
.btns .attack{background:var(--red);border-color:var(--red);color:#fff}.btns button:disabled{opacity:.5;cursor:wait}
ol{list-style:none;margin:18px 0 0;padding:0}li{display:grid;grid-template-columns:32px 1fr;gap:10px;padding:10px 0;border-top:1px solid var(--line)}
.dot{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-size:14px;font-weight:700;color:#fff;background:var(--line)}
.done .dot{background:var(--green)}.wait .dot{background:var(--amber)}.bad .dot{background:var(--red)}.idle .dot{background:var(--line)}
.wait .dot{animation:pulse 1.4s infinite}@keyframes pulse{50%{opacity:.45}}
li b{display:block}li span{color:var(--mute)}li a{color:var(--blue);font-size:13px;margin-left:6px}
.hint{margin-top:14px;padding:10px 12px;border-radius:8px;background:var(--bg);color:var(--mute)}
details{margin:0 24px 32px}summary{cursor:pointer;color:var(--mute)}.entry{border-top:1px solid var(--line);padding:6px 0;font-size:14px}.entry code{color:var(--mute);font-size:12px;word-break:break-all}
</style></head><body>
<header><h1>해담 SOAR 실습 제어판</h1><p>티켓을 고르고 [공격]을 누른 뒤, 아래 단계가 차례로 초록색이 되는 것을 지켜보세요.</p></header>
<nav><a href="http://127.0.0.1:8080" target="_blank">민원 포털</a><a href="http://127.0.0.1:8089" target="_blank">티켓 대시보드</a>
<a href="https://127.0.0.1:8443" target="_blank">pfSense</a><a href="http://127.0.0.1:9000" target="_blank">Graylog</a><a href="http://127.0.0.1:5678" target="_blank">n8n</a></nav>
<div class="tabs" id="tabs"></div><section class="panel" id="panel"></section>
<details><summary>실행한 명령 보기</summary><div id="entries"></div></details>
<script>
const TOKEN="__TOKEN__",H={"X-Panel-Token":TOKEN};
const INFO={S10:["S10 · 경계 차단 → 스캔 → 로그인 시도","공격자가 ping(방화벽에서 막힘), 없는 페이지 스캔, 틀린 로그인을 차례로 합니다. 세 신호가 모두 모이면 포털과 pfSense 양쪽에서 막습니다."],
S8:["S8 · 포털 스캔 → 로그인 시도","ping 없이 스캔과 틀린 로그인만 합니다. 방화벽 신호가 없으니 포털에서만 막습니다."],
S1:["S1 · 로그인 무차별 대입","정상 시민이 계정을 만들고, 공격자가 그 계정에 틀린 비밀번호를 9번 넣습니다. 공격자 IP만 막고 계정 주인은 그대로 로그인합니다."]};
const CASE_ORDER=["H1","H2","H3","S1","S4","S7","S8","S10","S12"];
Object.assign(INFO,{
 H1:["H1 · 민원 도배","공격자가 계정을 만들어 민원 8건을 연달아 등록합니다. 그 계정의 민원 작성만 막고(429), 로그인·조회와 다른 시민의 작성은 그대로 둡니다."],H2:["H2 · 타인 민원 엿보기","새 공격자 계정이 다른 시민의 민원 상세를 세 번 요청해 403을 만듭니다. Graylog와 n8n이 탐지한 뒤 공격 출발지만 차단하고, 해제 후에도 타인 민원은 계속 403입니다."],H3:["H3 · 연결 대기","실습 도구 연결 전입니다."],
 S4:["S4 · 연결 대기","실습 도구 연결 전입니다."],S7:["S7 · 연결 대기","실습 도구 연결 전입니다."],S12:["S12 · 연결 대기","실습 도구 연결 전입니다."]
});
let cur="H1",last={};
function esc(s){return String(s??"").replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]))}
function tabs(){document.getElementById("tabs").innerHTML=CASE_ORDER.map(c=>`<button class="${c===cur?'on':''}" onclick="cur='${c}';tabs();draw()">${c}</button>`).join("")}
function draw(){const d=last[cur]||{},steps=d.steps||[];
 if(d.pending){const waiting=steps[0]||{},guide=d.guide_url?`<p><a href="${d.guide_url}" target="_blank">H2 실습 안내 열기</a></p>`:"";document.getElementById("panel").innerHTML=`<div class="top"><div><h2>${esc(INFO[cur][0])}</h2><p>${esc(waiting.text||"실습 도구 연결 전입니다.")}</p>${guide}</div></div><div class="hint">연결이 완료되면 공격·효과 확인·해제 버튼이 표시됩니다.</div>`;return;}
 const list=steps.length?steps:["① 공격 보냄","② Graylog에 로그 도착","③ 탐지 (Graylog 경보)","④ 자동 대응 (n8n)","⑤ 효과","⑥ 해제 (사람이 확인 후)"].map(n=>({name:n,state:"idle",text:"[공격]을 누르면 시작합니다."}));
 const icon={done:"✓",wait:"…",bad:"!",idle:""};
 const next=!steps.length?"[공격]을 눌러 시작하세요.":steps.find(s=>s.state==="bad")?"빨간 단계를 확인하세요. 오른쪽 링크의 화면에서 원인을 볼 수 있습니다.":
   steps[5].state==="done"?"한 바퀴 끝. 같은 출발지는 15분(S1 30분, H1 10분) 뒤에 다시 할 수 있습니다. S1과 H1은 출발지(.11)가 같으니 이어서 하지 마세요.":
   steps[4].state==="done"?"효과까지 확인됐습니다. 티켓 대시보드에서 기록을 본 뒤 [해제]를 누르세요.":"자동으로 진행 중입니다. 5초마다 갱신됩니다.";
 document.getElementById("panel").innerHTML=`<div class="top"><div><h2>${INFO[cur][0]}</h2><p>${INFO[cur][1]}</p><p>공격자 IP <b>${esc(d.src)}</b>${d.elapsed!=null?` · 공격 뒤 <b>${d.elapsed}초</b>`:""}${d.ticket?` · 티켓 <b>${esc(d.ticket.ticket_id)}</b> (${esc(d.ticket.status)})`:""}</p></div>
 <div class="btns"><button class="attack" onclick="run('attack')">공격</button><button onclick="run('effect')">효과 다시 확인</button><button onclick="run('release')">해제</button></div></div>
 <ol>${list.map(s=>`<li class="${s.state}"><div class="dot">${icon[s.state]||""}</div><div><b>${esc(s.name)}${s.link?`<a href="${s.link}" target="_blank">화면 열기</a>`:""}</b><span>${esc(s.text)}</span></div></li>`).join("")}</ol>
 <div class="hint">${d.error?"상태를 읽지 못했습니다: "+esc(d.error):next}</div>`;}
async function run(action){const c=cur;document.querySelectorAll(".btns button").forEach(b=>b.disabled=true);
 try{const r=await fetch(`/api/${action}/${c}`,{method:"POST",headers:H});const d=await r.json();
  const rows=(d.log||[{step:d.error,result:""}]).map(x=>`<div>${esc(x.step)} → <b>${esc(JSON.stringify(x.result))}</b>${x.cmd?`<br><code>${esc(x.cmd)}</code>`:""}</div>`).join("");
  document.getElementById("entries").insertAdjacentHTML("afterbegin",`<div class="entry"><b>${new Date().toLocaleTimeString()} ${c} ${action}</b>${rows}</div>`);}
 finally{await refresh();}}
async function refresh(){try{last=await (await fetch("/api/state",{headers:H})).json();}catch(e){} draw();}
tabs();refresh();setInterval(refresh,5000);
</script></body></html>"""


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"실습 제어판: http://127.0.0.1:{PORT}  (끄려면 Ctrl+C)")
    webbrowser.open(f"http://127.0.0.1:{PORT}")
    server.serve_forever()
