# Graylog 알림 → n8n (D)

- 상태: 10/28 반입(URL 허용 목록·알림·S1 정의 꺼짐), 시험 알림 n8n 도착 확인. `detected_at` 추가는 이 PR 병합 뒤 반입. 큰 수정은 PR로 정한 뒤 D가 확인하고 반입한다.
- 대상: S1 실제 완주 1회(팀 계획 10/28). 다른 케이스 알림은 S1이 끝난 뒤 같은 방식으로 추가한다.

| 파일 | 알림 종류 | 보내는 곳 | 붙일 이벤트 정의 |
| --- | --- | --- | --- |
| `s1-n8n-haedam-s1.json` | Custom HTTP Notification(`http-notification-v2`) | `http://host.docker.internal:5678/webhook/haedam-s1`(n8n `haedam-30`) | A의 S1 정의(`lab/s1s4/graylog/s1-login-bruteforce.json`, PR #65) |

## 왜 이렇게 했나 (10/28 읽기 전용 확인)

- **주소:** Graylog 컨테이너(`soc-net`)와 n8n 컨테이너(`n8n_default`)는 네트워크가 달라 `n8n:5678`로는 닿지 않는다. `host.docker.internal:5678/healthz`는 Graylog 컨테이너 안에서 200이었다. n8n은 호스트의 `127.0.0.1:5678`에만 열려 있다.
- **본문:** `haedam-30` 입력 정규화 코드는 본문 최상위의 `event_id`·`asset_id`·`src_ip`·`username`이 없으면 `invalid_input`으로 끝낸다. 기본 HTTP 알림은 값을 `event.fields` 아래에 넣고, A의 S1 정의에는 `asset_id` 필드가 없다. 그래서 본문 템플릿으로 평평하게 만들고 `asset_id`는 `haedam-portal`로 고정한다(C 10/27 지적: 시험 입력에 `portal`이 섞여 티켓 묶기가 갈릴 수 있음).
- **시각:** `detected_at`에 `${event.timestamp_processing}`(Graylog 이벤트 생성 시각, 기획서 5.5 MTTD 끝점)를 넣는다(10/28 C 요청, 리허설 티켓에 비어 있었음). `condition_met_at`에는 `${event.timestamp}`를 넣지만 이는 Graylog 이벤트 시각이라 임계 충족 시각으로 쓰지 않는다(결과표는 A 원본 9번째 401 시각). `haedam-30`은 시간대가 붙은 ISO 문자열만 받으므로 실제 렌더링 값을 반입 뒤 확인한다.
- **인증:** 지금 haedam 웹훅은 모두 인증이 없다. n8n이 `127.0.0.1`에만 열려 있어 D PC 안(Graylog 컨테이너 포함)에서만 닿는다. 헤더 인증을 붙이려면 n8n 웹훅 Header Auth와 이 알림의 `headers`를 함께 바꾼다(별도 결정).

## 반입 순서 (D, PR 병합 뒤)

1. **URL 허용 목록:** Graylog는 URL 허용 목록이 켜져 있고 항목이 0개다(10/28 확인). System → Configurations → URL Allowlist에 아래 한 줄을 넣는다.
   - 종류 `Exact match`, 제목 `n8n haedam-s1`, 값 `http://host.docker.internal:5678/webhook/haedam-s1`
2. **알림 만들기:** `POST /api/events/notifications`(헤더 `X-Requested-By`)로 이 JSON을 넣는다. 형식이 거부되면 화면에서 같은 값으로 만들고 내보낸 JSON으로 이 파일을 고친다.
3. **정의에 붙이기:** A의 S1 정의를 반입할 때 `notifications`에 `{"notification_id": "<위 알림 ID>"}`를 넣는다. 정의는 시험 직전까지 꺼 둔다(B의 S8·S10 시험의 로그인 반복이 S1을 발동시킨다).
4. **한 번 확인:** 정의를 켜기 전 화면의 "Execute Test Notification"으로 n8n `haedam-30` 실행이 1건 생기고, 본문 필드 4개가 채워져 `protected_source`나 `invalid_input`이 아닌 결과가 나오는지 본다. 이때 `haedam-30`은 `dry_run` 기본이라 포털을 부르지 않는다.

## 아직 정하지 않은 것

- 실제 조치는 이 알림의 본문 템플릿으로만 켠다(#82). `"dry_run": false`를 넣으면 실제 포털 차단(112), `"store_real": true`를 넣으면 실제 티켓 기록(C 저장소)이 켜진다. 기본(이 파일 그대로)은 둘 다 꺼진 상태다. 바꾸는 시점은 D의 명시 승인으로 정하고, 리허설은 `store_real`만 켜고 `dry_run`은 그대로 두는 순서를 권한다.
- 시험 알림이 남기는 n8n 실행·티켓(자리표시 저장소)은 시험 ID로 구분해 증적에서 뺀다.

## 10/29 실제 차단 시험용 본문 변경 (D 결정: "차단까지 보자")

- 본문 템플릿 끝에 `"dry_run": false`를 더했다. 이 알림이 붙은 정의가 켜져 있으면 `haedam-30`이 실제 포털 차단(112, haedam-12)을 부른다. `store_real`은 그대로 없다(실제 티켓 기록은 꺼진 채).
- 보호 IP(팀 VPN 대역, `.10`, `.12`, `.100~.109`)는 `haedam-30`·`haedam-12`가 막는다. 시험이 끝나면 이 줄을 빼고(`dry_run` 기본 복귀) 정의도 끈다.
- 반입 방법은 병합 뒤 D 확인을 받아 `PUT /api/events/notifications/<알림 ID>`로 본문 템플릿만 바꾼다. 정의 활성화(14:00)와 별개 단계다.

## 10/29 실제 티켓 기록 시험용 본문 변경 (D 승인, B 요청)

- 본문 템플릿 끝에 `"store_real": true`를 더했다(`dry_run:false`는 #93에서 이미 반영). 이 알림이 붙은 정의가 켜져 있으면 `haedam-30`이 하위 호출(`haedam-10`)에 실제 C 저장소 기록을 켠다. 범위는 S1 R1·R2와 b8 관찰 구간이고, 다른 케이스 알림과 `haedam-30`의 전역 기본값(`dry_run:true`, `store_real:false`)은 그대로다.
- b8은 같은 정의·기록 설정으로 관찰한다. 기록을 꺼서 0건을 만들지 않고, 조건 미충족으로 이벤트·실행·티켓이 0건인지 확인한다.
- 시험이 끝나면 `dry_run:false`·`store_real:true` 두 줄을 함께 빼고(기본 복귀) 정의를 끈다.
- 반영은 병합 뒤 D 확인을 받아 `PUT /api/events/notifications/<알림 ID>`로 본문 템플릿만 바꾼다(10/29 11:40 방식: `basic_auth`·`api_secret`은 `null`, `api_key`는 빈 값, 본문에 `id` 포함).

## 10/29 R1 종료 후 기본값 복귀 (D 승인, B 요청)

- R1(10/29 14:33~15:28) 종료와 R2·b8 재예약에 따라 본문 템플릿에서 `"dry_run": false`와 `"store_real": true`를 뺐다. 기본(`haedam-30`의 `dry_run:true`, `store_real:false`)으로 돌아가며, 이 알림이 붙은 정의가 켜져도 실제 포털 차단·C 저장소 기록은 나가지 않는다.
- S1 정의는 15:38에 DISABLED로 끈 상태다. 다음 R2·b8 회차에서 실제 조치가 필요하면 새 PR로 다시 두 줄을 넣고 D의 시작 직전 승인을 받는다.
- 반영은 병합 뒤 D 확인을 받아 `PUT /api/events/notifications/<알림 ID>`로 본문 템플릿만 바꾼다(`basic_auth`·`api_secret`은 `null`, `api_key`는 빈 값, 본문에 `id` 포함).

## S12 알림 초안 (10/30, 미반입)

- `s12-n8n-haedam-s12.json`: 이벤트를 n8n `haedam-20`(웹훅 `haedam-s12`)으로 보낸다. 본문은 `event_id`·`asset_id`(haedam-portal 고정)·`src_ip`·`case_id`·`condition_met_at`·`detected_at`·`event_definition_id`이고 `dry_run`·`store_real`은 넣지 않는다(기본 dry_run). 실제 조치는 시험 직전에 별도 PR과 D 승인으로 본문에 넣는다.
- 붙일 정의: `lab/s12/graylog/s12-request-flood.json`(포털 `web.request`를 `src_ip`별 1분 창에서 센다). N=93(10/30 기준선 `s12-1030-baseline-30m-01`의 60초 창 최대 31건 x 3, B 전송 기준)과 스트림 haedam-portal(`6ad95444188b5d4016e9d412`)을 채워 두었다. 반입은 D 병합·확인 뒤, 정의는 DISABLED로 넣고 알림을 붙인다. `haedam-20`의 `baseline_ms`는 3414(p95 1137.9ms x3)이고 `dry_run:true`·`store_real:false` 기본은 그대로다.
- URL 허용 목록에 `http://host.docker.internal:5678/webhook/haedam-s12`를 `Exact match`로 추가해야 한다(S1 알림과 같은 방식).
- 확인한 것: JSON 형식과 `haedam-20` 웹훅 경로·필수 필드 일치(`tests/test_s12_graylog_draft.py`). 실제 Graylog 반입과 알림 도착은 시험하지 않았다.
