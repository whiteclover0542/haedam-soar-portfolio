# 티켓 응답 판단 코드 · 집 검증 후보

사람 담당 D(n8n)·C(티켓), 구현 준비 B. 시험 ID `HOME-TICKET-GUARD-20261024`, 브랜치 `codex/home-handoff-1023`. **API 응답 판단 코드와 집 시험용 loopback HTTP GET 어댑터를 구현했다. 실제 n8n 가져오기/실행·학원용 HTTP 노드 연결·동시 실행 제어·대상 호출은 미구현/미검증**이다.

기준은 [C PR55 수정 패치](../../../patches/ticket-store-pr55/README.md)다. 기존 D의 #43/#56/#57 `haedam-10` 임시 저장소를 덮어쓰지 않는다. 해당 후보의 `other_seat_open`/정적 데이터 판정을 대체할 별도 소비자 코드이며, 계약·증적을 임시 저장소 결과와 섞지 않는다.

## 파일과 실행

- 원본: [ticket-decision.js](ticket-decision.js). 순수 n8n Code 노드, 배치 입력 지원. 외부 호출·자격 증명·상태 저장 없음.
- 생성물: [haedam-16-ticket-decision-offline.json](../workflows/haedam-16-ticket-decision-offline.json). Execute Workflow Trigger → Code 두 노드만 있고 `active:false`다.
- 생성/동기화: `python tools/build_ticket_guard.py`, `python tools/build_ticket_guard.py --check`. AI 자산 동기화 도구와는 별개다.
- 로컬 JS 회귀: `python -m pytest tests/test_ticket_decision.py -q`. **Node.js 필요**. 이 PC에서는 Node 24.15.0으로 생성 워크플로의 실제 JS를 실행했다. Node가 없으면 JS 검사는 명시적으로 skip되며 동작 통과로 취급하지 않는다.
- C 응답 연결 대조: 패치를 적용한 별도 체크아웃을 준비한 뒤 `python tools/check_ticket_guard.py --ticket-source .local/ticket-pr55-final-20261024`. 임시 SQLite와 Flask test client → 응답 스키마 검사 → 생성 JS 실행의 8개 사례를 확인한다. 실제 키/포트/학원 DB를 사용하지 않는다. checkout 이름이 다르면 경로를 바꾼다.

기존 PR55 API는 이 브랜치에 병합하지 않았다. 위 `--ticket-source`는 [패치 안내의 새 체크아웃](../../../patches/ticket-store-pr55/README.md#다른-pc에서-같은-패치-검증)을 지정한다. 고정 기준과 패치가 달라지면 다시 대조한다.

## 집에서 실제 HTTP 경계까지 재검증

```powershell
python -m pytest tests/test_ticket_http.py -q
python tools/check_ticket_guard.py --ticket-source .local/ticket-pr55-final-20261024 --loopback-http
```

`tools/ticket_http.py`의 `TicketHTTP`는 집 시험용 **읽기 전용 수집기**다. 실제 `GET /open`, `GET /active`에서 보낸 query·수신 HTTP 상태·JSON을 판단 노드의 입력 봉투로 만든다. GET 외의 메서드·record 쓰기·대상 대응은 제공하지 않는다. 기존 API 계약이나 n8n 생성 JSON을 변경하지 않았다.

- 주소는 `http://127.0.0.1:<명시한 포트>`만 허용한다. 학원 VPN/LAN 주소·localhost 이름·임의 경로/사용자정보·HTTPS는 받지 않는다. 학원 주소에 맞추려고 제한만 제거하지 말고 D의 인증/경로/실행 조건을 먼저 확정한다.
- 프록시·리다이렉트·자동 재시도 없이 요청당 1회만 조회한다. `X-Response-Key`는 메모리에만 주입하며 출력/로그로 남기지 않는다. 3xx Location에는 키를 다시 보내지 않는다.
- JSON 객체·UTF-8·응답 64KiB 제한을 확인하고, 중복 JSON 키/NaN·잘린 응답/다른 Content-Type은 판정 가능한 빈 티켓으로 바꾸지 않는다. 오류 본문을 정상 200으로 바꾸지 않으며, 전송 실패는 `status:null, transport_error:true`다.
- 기본2초(최대10초)는 **소켓 무응답 제한**이다. 전체 벽시계 마감/느리게 이어지는 응답의 총 시간 제한은 보장하지 않는다. 학원 HTTP 어댑터의 전체 마감·제한 재시도·실제 수신 완전성은 별도 조건이다.
- `--loopback-http`는 OS가 배정한 임시 포트로 127.0.0.1에만 시험 서버를 띄우고, 임시 DB·합성 키를 사용한다. 정상 종료/오류 시 서버와 DB를 정리한다. Windows/VPN/방화벽·고정 포트 설정을 바꾸지 않는다.

연결 대조8개 중 **조회6개는 실제 loopback TCP HTTP**, record ACK/409 2개는 기존 Flask test client 응답이다. 시험용 입력/해제 이력을 만드는 record도 임시 DB의 test client로만 넣으며 네트워크 POST나 실제 차단/해제를 하지 않는다. 이 결과는 집 HTTP 경계 검증이며 D→C VPN 접속이나 n8n 실행의 증거가 아니다. 호출 상태는 `observation.transport: "loopback_http"`로 구분한다.

## 입력: 실제 HTTP 어댑터가 나중에 채울 봉투

API 자체의 입력/출력 계약은 바꾸지 않는다. 아래는 **판단 노드 전용 내부 입력**이다. `observation`에 합성 응답을 넣어 통과해도 실제 HTTP 호출 증적은 아니다.

| 필드 | 의미 |
| --- | --- |
| `mode` | `apply` / `release` / `record_response` |
| `expected.resource` | 적용 동작 기준의 정확한 `{asset_id, via, action, target}`. release에서도 unblock이 아니라 block 등 |
| `expected.seat` | 사람 자리 A~D |
| `expected.bot`, `expected.group_key` | apply에서 필수. 봇은 `"112"` 같은 문자열 |
| `expected.owner_ticket_id` | release에서 필수. 자기 티켓 하나만 제외; 자기 자리 전체를 제외하지 않음 |
| `expected.ticket_id` | record_response에서 필수. 기존 티켓이면 ID, 생성 요청이면 명시적 null |
| `observation.status` | HTTP 상태 숫자. 응답 없음은 null |
| `observation.query` | apply는 실제 요청한 `{seat, group_key}`, release는 실제 요청한 resource 4개. expected를 무조건 복사해 증적으로 만들지 않음 |
| `observation.body` | 파싱된 C API JSON 객체. 문자열/HTML/구형 임시 응답은 판정 보류 |
| `observation.transport_error` | 시간 초과/연결 실패라면 true. 정상 응답을 가장해 빈 tickets로 바꾸지 않음 |

apply 입력 예시(합성·가동 증적 아님):

```json
{
  "mode": "apply",
  "expected": {
    "seat": "D", "group_key": "203.0.113.11", "bot": "112",
    "resource": {"asset_id": "haedam-portal", "via": "portal", "action": "block", "target": "203.0.113.11"}
  },
  "observation": {
    "status": 200,
    "query": {"seat": "D", "group_key": "203.0.113.11"},
    "body": {"ok": true, "exists": false, "ticket_id": null, "status": null, "applied_actions": []}
  }
}
```

`/open` 응답은 자산을 되돌려주지 않으므로 apply의 자산 일치/대상별 호출 권한까지 증명하지 못한다. 원본 자산·이벤트 ID·실행 ID·요청 키는 상위 실행 맥락에서 따로 보존한다. 판단 출력에는 원문/입력 전체를 반사하지 않으며, 배치 출력 순서는 입력과 같다.

## 출력과 D가 연결할 분기

모든 출력은 `version:1`, `decision`, `reason`, **`allow_target_call:false`, `automatic_retry:false`**다. 조건부 `ticket_id` 또는 `blocking_ticket_ids` 외에 키·원문·응답 본문을 복사하지 않는다. 이 플래그를 나중에 임의로 true로 바꾸는 것으로 동시 실행 문제가 해결되지는 않는다.

| 관측 | decision / reason | 다음 행동 |
| --- | --- | --- |
| 열린 티켓 없음 / 같은 현재 활성 조치 없음 | apply_candidate | 조회 시점 후보만 표시. 자산/허용 대상·대상 API 멱등성·동시 호출 제어가 확인되기 전 호출 보류 |
| 같은 bot/via/action/target 활성 | skip_active / matching_active_action | 중복 대상 호출 생략; 현재 조치의 효과 검증은 별도 |
| 기존 티켓 restored | hold / close_restored_before_new_cycle | 원복 확인→사람 닫기→새 이벤트/요청 키의 새 주기. 대상 호출 전에 이 분기 수행 |
| 자기 티켓 외의 활성 조치 있음 | hold / other_active_claims | 같은 자리의 다른 티켓·다른 봇·closed 미해제 조치도 보류 사유 |
| 자기 조치만 존재 | release_candidate / owner_only_snapshot_requires_serialization | 조회와 해제 사이 경쟁은 미해결. 자원별 적용/해제 직렬화 또는 소유권 예약을 실제 호출 계층에 구현해야 함 |
| 기록상 조치 0건 | hold / no_recorded_claims | 실제 대상 상태와 이력 대조; 해제 성공이나 원복 완료로 표시하지 않음 |
| 형식/범위/소유 자리 불일치·401/404/5xx/시간 초과 | hold | 기존 조회 오류와 구분되는 reason으로 중단, 0건으로 바꾸지 않음 |
| record 200/201·정상 모양·기대 티켓 일치 | record_acknowledged / effect_not_inferred | 기록 수신 확인만 인정; 실제 적용/효과·원복 판정은 별도 |
| record 409 IDEMPOTENCY_CONFLICT | hold / resolve_key_body_conflict | 같은 키/다른 본문 원인 수정. 새 키로 무조건 반복하지 않음 |
| record 409 INVALID_TRANSITION | hold / resolve_cycle_or_asset_scope | 이전 티켓 주기/자산 범위를 확인. 해소 전 반복 금지 |
| record 응답 불명/5xx | hold / reconcile_record_same_request | 대상 상태·기존 요청 키를 대조. 대상 대응 API 재호출 금지; 기록 요청만 같은 키/본문으로 제한 재시도할지는 D 어댑터에서 결정 |

후속 담당 첫 행동은 C 패치 정책과 자산/해제 동작 표를 확정하고, D가 실제 HTTP 응답의 status/body/query를 위 봉투에 연결하는 것이다. n8n 2.39.5 환경의 가져오기·Code 노드/Execute Workflow 실행·배치 항목 연결은 **확인 필요**다. 이 파일을 가져오더라도 기존 워크플로를 교체하거나 활성화하지 않는다. 최종 연결 때에는 호출 계층의 원자적 멱등성·적용/해제 직렬화와 실제 효과·정상 접근·원복을 별도로 검증한다.

10/24 후속으로 [단일 호스트 예약과 읽기 전용 시험](../../../docs/resource-gate-home.md)을 구현했다. `--reserved-trial`은 예약→최신 loopback GET→이 판단 노드→not_called 정리를 연결한다. 같은 완료된 시험ID에는 과거 후보 판단을 다시 주지 않는다. 실제 대상 호출/n8n 실행 어댑터는 미연결이며 기존 allow_target_call=false는 유지한다.
