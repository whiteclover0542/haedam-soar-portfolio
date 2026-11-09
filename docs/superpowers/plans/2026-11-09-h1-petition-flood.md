# H1 민원 도배(가용성) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한 시민 계정이 짧은 시간에 민원을 대량 등록하면 Graylog가 탐지하고, n8n이 그 계정의 **민원 작성만** 제한(로그인·조회는 유지)한 뒤 티켓에 남기며, 담당자가 해제하면 다시 작성할 수 있게 한다.

**Architecture:** 포털에 `users.posting_restricted` 플래그와 대응 API(제한·해제)를 더하고, 제한 중 작성은 429로 거부한다. 탐지는 기존 `petition.created` 이벤트를 `username`별로 세는 Graylog 정의 하나, 대응은 검증된 S1 메인(`haedam-30`)·계정 잠금(`haedam-13`)을 본떠 만든 n8n 워크플로 두 개다. 해제는 설계대로 사람의 일로 두고, 실행기는 대응 API를 직접 불러 원복한다.

**Tech Stack:** Flask 3.1·SQLAlchemy·Alembic(포털), Graylog 6.1 이벤트 정의, n8n 2.39, Python 표준 라이브러리(실행기·생성 스크립트)

**Spec:** `docs/MVP-설계.md` 7절(H1 행) · `docs/PROGRESS.md` "H1 민원 도배" H1-1~6

## Global Constraints

- 탐지: 같은 `username`의 `petition.created`가 **10분 안에 N건 이상**. N은 기준선을 잰 뒤 정하고 근거를 티켓 문서에 남긴다(설계 7절).
- 대응: **민원 작성만 제한**, 로그인·조회는 유지. 제한 중 작성은 **429**(설계: 429 또는 403).
- 복구 확인: 담당자 해제 후 작성 **201**.
- 대응 API는 기존 규칙을 그대로 따른다: `X-Response-Key`, `RESPONSE_ALLOWED_CIDRS`(n8n `10.250.0.103/32`), `Idempotency-Key` 8~100자, 관리자 계정은 대상에서 제외.
- 포털 코드 변경은 본인(반소람) 기여로 `CREDITS.md`에 표시한다(원본 포털은 김명준).
- n8n 웹훅은 Header Auth `X-Haedam-Key`(자격 증명 `haedam-h1 caller`). 실제 조치는 본문 불리언 `dry_run:false`·`store_real:true`일 때만(기존 메인과 같음).
- 실측 3회, 실패 회차도 남긴다. 실측·배포는 Task 8 새 설치 리허설 뒤에 한다(그 전에는 코드·단위 테스트만).

## Review Focus

1. **제한 중인 계정의 다른 쓰기(민원 수정·삭제, 비밀번호 변경)** — 작성만 막고 나머지는 그대로여야 한다. → Task 1 `test_restricted_user_can_still_login_and_list`
2. **같은 계정 제한 요청이 두 번 오는 경우(Graylog 재발동·n8n 재시도)** — 두 번째는 `changed:false`, 같은 Idempotency-Key 재전송은 이전 결과를 그대로. → Task 1 `test_restrict_is_idempotent`
3. **관리자·staff 계정이 대상이 되는 경우** — 관리자는 403(기존 규칙), staff는 애초에 민원 작성 권한이 없어 탐지되지 않는다. → Task 1 `test_restrict_refuses_admin`
4. **없는 사용자 이름** — 404, 아무것도 바꾸지 않음. → Task 1 `test_restrict_unknown_user_404`
5. **정상 시민 여러 명이 동시에 민원을 넣는 경우** — `username`별로 세므로 서로 합쳐지지 않아야 한다. → Task 2 `test_h1_definition_groups_by_username`

---

## File Structure

| 파일 | 역할 |
| --- | --- |
| `services/portal/backend/migrations/versions/b1f3c2d4e5a6_add_posting_restricted.py` | `users.posting_restricted` 열 추가 |
| `services/portal/backend/src/haedam_portal/models.py` | `User.posting_restricted`, `public()`에 포함 |
| `services/portal/backend/src/haedam_portal/petitions/__init__.py` | `create()`가 제한 계정을 429로 거부 |
| `services/portal/backend/src/haedam_portal/integration/__init__.py` | `POST /api/v1/response/accounts/posting` 대응 API |
| `services/portal/backend/tests/test_posting_restriction.py` | 위 동작 테스트 |
| `lab/h1/graylog/h1-petition-flood.json` | Graylog 이벤트 정의 |
| `infra/graylog/notifications/h1-n8n-haedam-h1.json` | 알림(→ `/webhook/haedam-h1`) |
| `infra/graylog/bootstrap.py` | 위 정의·알림을 반입 목록에 추가 |
| `tools/make_h1_workflows.py` | `haedam-13`·`haedam-30`에서 H1 워크플로 두 개를 만든다(한 번 실행, 결과 커밋) |
| `infra/n8n/workflows/haedam-18-portal-posting.json`, `haedam-35-h1-main.json` | 생성 결과 |
| `infra/n8n/make_credentials.py`, `infra/n8n/load.py` | `haedam-h1 caller`, 게시 목록 |
| `lab/run_ticket.py`, `lab/portal_login.py`, `tools/summarize_runs.py` | H1 입력·효과·원복·집계 |
| `docs/tickets/H1/README.md` | 시나리오·기준선·실측 |

---

### Task 1: 포털 — 작성 제한 플래그와 대응 API (H1-1)

**Files:**
- Create: `services/portal/backend/migrations/versions/b1f3c2d4e5a6_add_posting_restricted.py`, `services/portal/backend/tests/test_posting_restriction.py`
- Modify: `models.py`(User), `petitions/__init__.py`(`create`), `integration/__init__.py`

**Interfaces:**
- Produces: `POST /api/v1/response/accounts/posting` — 본문 `{"username": str, "restricted": bool}`, 헤더 `X-Response-Key`·`Idempotency-Key`. 응답 `ok({"user_id": int, "username": str, "posting_restricted": bool, "changed": bool})`. 오류: 403 관리자/인증 실패, 404 없는 계정, 400 `restricted`가 불리언이 아님.
- Produces: 제한 계정의 `POST /api/v1/petitions` → 429, 오류 코드 `POSTING_RESTRICTED`, 이벤트 `petition.create_refused`(outcome `failure`, status 429, `username`).
- Produces: 대응 API 성공 시 이벤트 `account.posting_restricted` 또는 `account.posting_allowed`(status 200, `username`).

- [ ] **Step 1: 실패하는 테스트를 쓴다** (`tests/test_posting_restriction.py`, `conftest.py`의 `Actor`·`PASSWORD`·`citizen`/`other`/`admin` 계정 재사용)

```python
def test_restricted_user_gets_429_and_others_are_fine(app):
    restrict(app, "citizen", True)            # 대응 API 호출 헬퍼(키·Idempotency-Key 포함)
    assert citizen.post_petition().status_code == 429
    assert citizen.post_petition().json["error"]["code"] == "POSTING_RESTRICTED"
    assert other.post_petition().status_code == 201

def test_restricted_user_can_still_login_and_list(app):
    restrict(app, "citizen", True)
    assert login("citizen").status_code == 200
    assert citizen.get("/api/v1/petitions").status_code == 200

def test_allow_restores_201(app):
    restrict(app, "citizen", True); restrict(app, "citizen", False)
    assert citizen.post_petition().status_code == 201

def test_restrict_is_idempotent(app):
    assert restrict(app, "citizen", True).json["data"]["changed"] is True
    assert restrict(app, "citizen", True).json["data"]["changed"] is False
    first = restrict(app, "citizen", True, key="same-key-123")
    assert restrict(app, "citizen", True, key="same-key-123").json == first.json

def test_restrict_refuses_admin(app):
    assert restrict(app, "admin", True).status_code == 403

def test_restrict_unknown_user_404(app):
    assert restrict(app, "nobody", True).status_code == 404

def test_restrict_requires_boolean(app):
    assert restrict(app, "citizen", "yes").status_code == 400

def test_refusal_is_logged(app):
    restrict(app, "citizen", True); citizen.post_petition()
    assert last_event(app)["event_type"] == "petition.create_refused"
```

- [ ] **Step 2: 실패 확인** — `cd services/portal/backend; python -m pytest tests/test_posting_restriction.py -v` → 8개 FAIL(404 또는 AttributeError)

- [ ] **Step 3: 구현**
  - 마이그레이션 `b1f3c2d4e5a6`(down_revision `7c2e9a41d5b3`): `users.posting_restricted` Boolean, `nullable=False`, `server_default=sa.false()`.
  - `User.posting_restricted = db.Column(db.Boolean, nullable=False, default=False)`, `public()`에 추가.
  - `create()`: 입력 검증 전에 `if g.user.posting_restricted:` → `emit("petition.create_refused", "failure", 429, username=...)` 후 `fail(429, "POSTING_RESTRICTED", "민원 작성이 일시 제한된 계정입니다. 담당 부서에 문의해 주세요.")`.
  - 대응 API `posting_response()`: `account_action`과 같은 순서(인증 → `request_digests` → `with_for_update` 조회 → `replayed` → 관리자 거부 → 변경 → `ResponseReceipt` → commit → 이벤트). 세션은 회수하지 않는다(로그인 유지가 요구사항).

- [ ] **Step 4: 통과 확인** — 같은 명령 8개 PASS, 이어서 `python -m pytest -q`로 기존 포털 테스트도 모두 PASS

- [ ] **Step 5: 커밋** — `feat(portal): 민원 작성 제한 플래그와 대응 API(H1)`

### Task 2: Graylog — H1 탐지 정의와 알림 (H1-2)

**Files:**
- Create: `lab/h1/graylog/h1-petition-flood.json`, `infra/graylog/notifications/h1-n8n-haedam-h1.json`
- Modify: `infra/graylog/bootstrap.py`(`NOTIFICATIONS`, `DEFINITIONS`), `tests/test_graylog_bootstrap.py`

**Interfaces:**
- Consumes: 포털 GELF 필드 `_event_type`, `_username`, `_status`(Task 1의 `petition.created` 201)
- Produces: 정의 제목 `H1 민원 도배 (username)`, 알림 제목 `n8n haedam-h1 (H1 → haedam-35)`, 알림 URL `http://10.250.0.103:5678/webhook/haedam-h1`, 본문 필드 `event_id, asset_id, username, src_ip, case_id, condition_met_at, detected_at, event_definition_id`(S1 알림과 같은 형식, `case_id`는 `H1` 고정)

- [ ] **Step 1: 실패하는 테스트**

```python
def test_h1_definition_groups_by_username():
    d = json.loads(Path("lab/h1/graylog/h1-petition-flood.json").read_text("utf-8"))
    c = d["config"]
    assert c["group_by"] == ["username"] and c["search_within_ms"] == 600000
    assert 'event_type:"petition.created"' in c["query"] and "status:201" in c["query"]
    assert c["conditions"]["expression"]["right"]["value"] == 4   # count() > 4, 즉 N=5(초안). Task 5 기준선 뒤 바뀌면 이 값도 고친다

def test_bootstrap_lists_h1():
    from infra.graylog.bootstrap import DEFINITIONS, NOTIFICATIONS
    assert DEFINITIONS["lab/h1/graylog/h1-petition-flood.json"] == "haedam-h1" and "haedam-h1" in NOTIFICATIONS
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_graylog_bootstrap.py -v`
- [ ] **Step 3: 구현** — S1 정의(`lab/s1s4/graylog/s1-login-bruteforce.json`)를 본떠 쿼리 `source:haedam-portal AND event_type:"petition.created" AND status:201`, `group_by ["username"]`, 창 10분, 평가 60초, `field_spec`의 `case_id`는 `H1`. 알림은 `s1-n8n-haedam-s1.json`의 URL·제목만 바꾼다. `bootstrap.py` 두 사전에 한 줄씩.
- [ ] **Step 4: 통과 확인**
- [ ] **Step 5: 커밋** — `feat(graylog): H1 민원 도배 탐지 정의·알림`

### Task 3: n8n — H1 메인과 작성 제한 하위 워크플로 (H1-3)

**Files:**
- Create: `tools/make_h1_workflows.py`, `infra/n8n/workflows/haedam-18-portal-posting.json`, `infra/n8n/workflows/haedam-35-h1-main.json`
- Modify: `infra/n8n/make_credentials.py`(`CALLERS`에 `haedam-h1`, `HTTP_HEADER_AUTH`에 `haedamPortalPosting01`), `infra/n8n/load.py`(`PUBLISH`에 `haedamH1Main01`), `tests/test_n8n_credentials.py`

**Interfaces:**
- Consumes: Task 1 API, Task 2 알림 본문
- Produces: 하위 `haedamPortalPosting01` — 입력 `{action: "restrict"|"allow", username, ticket_id, dry_run, ctx}`, 출력은 `haedam-13`과 같은 형태(`ok, result, applied_verified, detail`). 메인 `haedamH1Main01` — 웹훅 `haedam-h1`, `group_key = username`, 조치 기록 `{bot: "113", via: "portal", action: "restrict_posting", target: username}`(111 계정 잠금·112 IP 차단과 구분), seat `A`.

- [ ] **Step 1: 실패하는 테스트** — 기존 `test_all_referenced_credentials_built`·`test_attach_sets_ids_on_every_header_auth_node`가 새 파일까지 덮는다. 추가:

```python
def test_h1_workflows_derived():
    main = load(Path("infra/n8n/workflows/haedam-35-h1-main.json"))
    sub = load(Path("infra/n8n/workflows/haedam-18-portal-posting.json"))
    assert main["id"] == "haedamH1Main01" and sub["id"] == "haedamPortalPosting01"
    text = json.dumps(main, ensure_ascii=False)
    assert "haedam-h1" in text and "haedamPortalPosting01" in text and "haedamPortalIp01" not in text
    assert "/api/v1/response/accounts/posting" in json.dumps(sub)
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_n8n_credentials.py -v`
- [ ] **Step 3: 구현** `tools/make_h1_workflows.py` — 원본 JSON을 읽어 문자열 치환으로 새 파일을 쓴다. 치환 표는 스크립트 맨 위 상수로 두고(id·이름·웹훅 경로·하위 워크플로 ID·포털 경로·요청 본문 필드·`expected` 조치·`group_key`), 각 치환이 원본에 정확히 1회 이상 있는지 `assert`한다(원본이 바뀌면 조용히 틀린 파일을 만들지 않도록). 생성 결과는 사람이 읽고 커밋한다. 생성기는 다시 돌리지 않는 한 번용이다.
- [ ] **Step 4: 통과 확인** — `python -m pytest tests -q`
- [ ] **Step 5: 커밋** — `feat(n8n): H1 메인·작성 제한 워크플로`

### Task 4: 실행기·집계에 H1 추가, 기준선 모드 (H1-4 준비)

**Files:**
- Modify: `lab/portal_login.py`(`post` 모드: N건 작성, 상태 코드만 출력), `lab/run_ticket.py`, `tools/summarize_runs.py`, `tests/test_run_ticket.py`, `tests/test_summarize_runs.py`

**Interfaces:**
- `python lab/run_ticket.py H1 [--restore] [--baseline]`
  - 입력: `attacker`(`.11`)에서 새 계정 `zz_a_h1_<run_id>` 가입 → 같은 세션으로 민원 `H1_POSTS`건(초안 8) 연속 작성
  - 효과: 같은 계정 작성 429, 같은 계정 로그인 200·목록 200, `normal`의 다른 계정 작성 201
  - `--restore`: n8n 컨테이너에서 대응 API `{"restricted": false}` 호출 → 같은 계정 작성 201
  - `--baseline`: `normal`이 새 계정으로 3건을 2분 간격으로 작성 → 180초 안에 티켓이 없어야 통과. 행에 `"baseline": true`
- `summarize_runs`: `EXPECTED_VIA["H1"] = {"portal"}`, 차단 판정에 `restrict_posting` 포함, 효과 공격자 기대값 `429`, `baseline` 행은 실측 집계에서 빼고 "오탐" 칸에 발동 수를 센다.

- [ ] **Step 1: 실패하는 테스트**

```python
def test_h1_auto_ok_expects_429():
    r = row(case="H1", actions=[["portal", "restrict_posting", "applied", "2026-11-09T03:00:40+00:00"]],
            effect={"attacker": "429", "normal": "201"})
    assert summarize([r])["H1"]["auto_rate"] == 1.0

def test_baseline_rows_count_false_positives_only():
    s = summarize([row(case="H1", baseline=True, ticket_id="T-1"), row(case="H1", baseline=True, ticket_id=None)])
    assert s["H1"]["runs"] == 0 and s["H1"]["false_positives"] == 1
```

- [ ] **Step 2: 실패 확인** — `python -m pytest tests/test_summarize_runs.py -v`
- [ ] **Step 3: 구현** (위 인터페이스대로. 정상 사용자 효과의 기대값은 H1에서 `201`)
- [ ] **Step 4: 통과 확인** — `python -m pytest tests -q`
- [ ] **Step 5: 커밋** — `feat(lab): 실행기·집계에 H1과 기준선 모드`

### Task 5: 배포·기준선·실측·티켓 문서 (H1-4~6) — Task 8 리허설 뒤

- [ ] **Step 1:** `docker compose up -d --build portal`(마이그레이션 자동) → `python infra/graylog/bootstrap.py --live` → `python infra/n8n/load.py` → `python tools/check_stack.py` 6/6 OK
- [ ] **Step 2: 기준선** — `python lab/run_ticket.py H1 --baseline` 2회. 티켓 0이어야 한다. 정상 시민이 10분에 3건을 넘기기 어렵다는 근거(seed 민원 분포, 기준선 결과)로 **N=5**를 확정하거나, 발동하면 N을 올리고 Task 2 테스트 값과 함께 고친다.
- [ ] **Step 3: 실측 3회** — `python lab/run_ticket.py H1 --restore`(같은 계정은 회차마다 새로 만들므로 창 대기 없음, 단 출발지 `.11`은 S1과 겹치지 않게 S1 회차와 30분 띄움)
- [ ] **Step 4:** `docs/tickets/H1/README.md`(시나리오·기준선 표·N 근거·실측 표 자리), `python tools/summarize_runs.py`, `CREDITS.md`에 포털 변경 본인 기여 표시, `PROGRESS.md` H1-1~6 갱신
- [ ] **Step 5: 커밋** — `docs(h1): 기준선·실측 3회·티켓 문서`
