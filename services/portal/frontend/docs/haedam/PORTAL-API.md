# 해담시청 포털 API v1.0

구현 대상: `haedam-portal-backend`, 소비자: `haedam-portal-frontend`. 2026-10-19 사용자가 프론트·백 구현을 맡고 React + Flask를 선택했다. 기존 관제 계약을 대체하지 않는 포털 전용 계약이다. 로컬 기능 검증과 실제 관제 연동 완료는 구분한다.

## 인증·공통 형식

- 모든 경로는 `/api/v1`. JSON 성공은 `{success:true,data:...}`, 실패는 `{success:false,error:{code,message,fields?}}`. 입력 검증 오류는 선택적인 `fields`에 필드 키→한국어 안내를 담는다. 기존 code/message 소비자와 호환되며 입력 원문은 반영하지 않는다. 오류 스키마는 `contracts/portal-error.schema.json`, 합성 예시는 `contracts/portal-examples/validation-error.json`이다.
- `GET /auth/me` → `{user:null|User,csrf_token:string}`. 익명 세션도 발급한다. 브라우저는 HttpOnly `haedam_session` 쿠키로 인증하고 CSRF 토큰만 메모리에 보관한다.
- POST/PATCH/DELETE는 `Content-Type: application/json`과 `X-CSRF-Token`이 필요하다. 자동화 API는 별도 키·접속망을 사용한다. origin이 있으면 현재 origin과 같아야 한다. CORS를 열지 않는다.
- 로그인 시 세션·CSRF를 회전한다. 세션은 4시간 만료, 로그아웃·비밀번호 변경·계정 잠금·역할 변경 시 회수한다. 잠금 해제 시 이전 세션은 복원하지 않는다.
- 초기 배치는 프록시 없이 `remote_addr`만 사용하며 X-Forwarded-For는 무시한다. IPv4-mapped IPv6 주소는 IPv4로 바꿔 같은 출발지로 본다. 로그인 제한·이벤트·IP 차단·대응 API 호출자 검사가 같은 해석(`client_ip`)을 쓴다.
- 민원은 시민 본인과 지정된 담당자만 볼 수 있다. staff는 미배정 민원 대기열을 볼 수 있고 본인에게 배정한 뒤 처리한다. admin은 계정 관리 역할이며 민원 원문을 볼 수 없다.
- 오류: 400 VALIDATION_ERROR, 401 AUTH_REQUIRED/INVALID_CREDENTIALS, 403 FORBIDDEN/CSRF_FAILED/IP_BLOCKED, 404 NOT_FOUND, 409 CONFLICT, 413 TOO_LARGE, 429 RATE_LIMITED, 500 INTERNAL_ERROR, 503 NOT_READY. 잠금·잘못된 비밀번호는 로그인에서 같은 401 안내로 처리한다.

## 경로

| 메서드·경로 | 권한 | 요청·응답 data |
|---|---|---|
| GET /health | 공개 | DB·민원 테이블 질의 성공 여부·service·status |
| GET /auth/me | 공개 | user·csrf_token |
| POST /auth/register | 익명 | username(3~40 ASCII 영숫자·_), display_name(2~30), password(10~128). citizen만 생성. User, 201 |
| POST /auth/login | 공개 | username,password → user·csrf_token |
| POST /auth/logout | 로그인 | {} → logged_out:true |
| POST /auth/password | 로그인 | current_password,new_password → user·csrf_token; 모든 기존 세션 회수 |
| GET /petitions | citizen/staff | page(1~),page_size(1~50),status,category,q. items·total·page·page_size·pages·counts |
| POST /petitions | citizen | title(5~120),content(10~5000),category → Petition,201 |
| GET /petitions/{id} | 소유자/미배정 대기열 staff/지정 staff | Petition·history |
| PATCH /petitions/{id}/assignment | staff | {} → 자기 배정, 이미 타인 배정이면 404, 동시 수정 충돌 409 |
| PATCH /petitions/{id}/status | 지정 staff | status,reply,version. received→in_progress→completed, completed는 종결. 완료 시 reply(10~3000) 필수. 낙관 잠금 충돌 409 |
| GET /admin/users | admin | page,page_size,q,role,locked → items·total·page·page_size·pages·summary. [전체 계정 조회 계약](ADMIN-USERS-API.md) |
| POST /admin/users | admin | username,display_name,password,role(citizen/staff/admin) → User,201 |
| PATCH /admin/users/{id} | admin | role 또는 locked:true. 본인 변경·마지막 관리자 제거 금지. 잠금은 모든 세션 회수 |
| POST /admin/users/{id}/unlock | admin | reason_code(=false_positive) → locked:false. S4 오탐 해제, 비밀번호 유지, 기존 세션 복구 없음. 처리자는 세션의 관리자 |
| POST /admin/users/{id}/reset-password | admin | new_password → locked:false. 비밀번호 재설정 후 해제, 기존 세션 복구 없음 |
| GET /config | 공개 | dashboard_url은 admin에게만 제공, departments·categories |

User: id,username,display_name,role,department,locked,created_at. 비밀번호 해시·세션 키 제외.

Petition: id,reference,title,content,category,status,version,created_at,updated_at,applicant{id,display_name},assignee{id,display_name}|null,reply,history[]. 목록은 content·reply·history를 제외하고 상세에서만 제공한다. history는 from_status,to_status,actor,created_at. 타인 민원 ID는 404. 시민 목록은 본인만. 검색은 권한 필터 적용 뒤 수행한다. counts는 검색어와 별개인 본인/담당자 범위의 상태별 수다.

## 자동화 경계

`POST /response/accounts/{id}/lock`, `/reset`, `POST /response/accounts/lock`(본문 `{username}`): `X-Response-Key`, 허용 CIDR, `Idempotency-Key`(8~100) 필수이며 인증 실패는 모두 403 `FORBIDDEN`. S4 이벤트에는 `username`만 남으므로 n8n은 username 잠금을 쓴다. username은 로그인과 같이 앞뒤 공백을 떼고 소문자로 바꿔 찾는다. 해제(reset)는 사람이 하는 원복이라 id 경로만 두고 잠금 응답의 `user_id`를 쓴다. lock은 모든 세션 회수, reset은 new_password로 재설정 뒤 해제. 관리자 계정은 대상에서 빼고 403 `FORBIDDEN`, 없는 계정은 404 `NOT_FOUND`. 두 lock 경로 모두 `{user_id,locked,changed,revoked_sessions}`를 반환하며 같은 키·같은 요청 재시도는 동일 결과, 다른 요청에 같은 키는 409. 원문 키·비밀번호·요청 본문은 저장하지 않고 해시만 비교한다.

앱 IP 차단(대응 봇 112): `POST /response/ips/block`·`/unblock`, 본문 `{ip, minutes?}`. 같은 키·허용 CIDR·`Idempotency-Key` 규칙을 따른다. `minutes`는 차단할 때만 1~1440 정수이고, 없으면 해제할 때까지 차단한다. 허용 CIDR(관리망·대응 호출자) 안의 주소는 block을 403으로 거부하고, 남아 있는 차단 행이 있어도 접근을 막지 않는다(자기 차단 방지). unblock은 주소와 관계없이 허용한다. 허용 CIDR을 바꿨다면 그 대역에 남은 차단을 unblock으로 정리한다. `{ip,blocked,changed,expires_at}`를 반환하며, `expires_at`은 처리 뒤 저장된 만료(초 단위, 무기한이면 null)다. `GET /response/ips`는 현재 유효한 차단 `{items:[{ip,expires_at,created_at}]}`을 돌려준다. 차단된 출발지의 모든 요청(화면·정적 파일·API)은 403 `IP_BLOCKED`를 받는다. 같은 `Idempotency-Key`로 다시 보내면 현재 상태가 아니라 처음 응답 전체(`changed`·`expires_at` 포함)를 그대로 돌려준다. 112는 S1·S8·S10·S12가 함께 쓰므로 차단이 겹치면 더 긴 쪽을 유지한다. 이미 차단된 주소를 다른 키로 다시 차단하면 무기한이 만료 있는 차단보다, 늦은 만료가 이른 만료보다 우선하며 차단을 짧게 만들지 않는다. 만료가 늦춰지거나 무기한이 되면 `changed:true`, 저장된 차단이 그대로면 `changed:false`이고 응답의 `expires_at`은 유지된 만료다. 이미 풀린 주소를 해제해도 `changed:false`다. 같은 주소나 같은 키의 요청이 동시에 겹치면 서버가 새 트랜잭션으로 최대 3번 다시 처리해 이 규칙대로 응답하고, 그래도 겹치면 409 `CONFLICT`를 준다. 이때 호출자는 같은 키로 다시 보낸다. pfSense 경계 차단은 B 담당과 연동 전이다.

## 이벤트

`contracts/portal-event.schema.json`의 별도 v1.0 계약. 익명 username은 null. auth.login_succeeded/auth.login_failed, auth.account_locked/auth.account_unlocked/auth.password_reset, iam.role_changed, web.not_found, web.request, web.file_access, web.ip_blocked/web.ip_unblocked, petition.created/petition.updated. web.request는 S12 후보 입력일 뿐 탐지 판정이 아니며 `/assets` 정적 파일 요청은 세지 않는다. 차단된 출발지의 요청은 outcome `denied`로 남는다. web.file_access는 실제로 내준 파일(화면 경로의 `index.html`, `assets/...`, `favicon.svg`)마다 `details.file_key`를 남겨 S7의 Wazuh FIM 경로와 묶는다. file_key는 웹 루트(`FRONTEND_DIST`) 기준 상대 경로다. `/`로 구분하고 200자 이하이며, `.`·`..`·빈 세그먼트, 드라이브 접두사, 제어문자, `?`·`#`·`\`가 없다. 이 규칙을 지키지 못하는 파일은 포털이 내주지 않는다(404). Wazuh `syscheck.path`는 `FRONTEND_DIST` 접두사를 떼고 구분자를 `/`로 바꾼 뒤 같은 규칙으로 맞춰 묶는다. web.ip_blocked/unblocked는 대응 호출자를 src_ip로, 대상 주소를 `details.target_ip`로 남긴다. auth.account_unlocked는 해제 대상을 username으로, 처리자를 `details.actor_user_id`·`actor_username`으로, 사유를 `details.reason_code`(false_positive)로 남긴다. 실제 잠금→해제일 때만 이벤트가 난다. 민원 원문·제목·표시 이름·비밀번호·쿠키·토큰을 기록하지 않는다. 경로 대신 route template 사용, 404는 resource=unmatched로 남겨 쿼리·원문 경로 유출을 막는다. GELF rule login-success/login-bruteforce/web-scan/request-observed/file-access 등과 매핑하고, `_file_key`·`_target_ip` 필드를 함께 보낸다. UDP 전송 성공은 수신 증명이 아니다. 로컬 JSONL이 실측 출처다.

## 배포와 호환

React 빌드 dist를 Flask `FRONTEND_DIST`로 제공. 허용한 /, /login, /register, /petitions, /petitions/new, /petitions/{id}, /work, /admin, /account만 화면 라우트다. 나머지는 404와 web.not_found. `/assets`는 정적 파일만 제공한다. DB는 MySQL 계획, SQLite는 격리된 로컬 개발·회귀검증용이며 MySQL 실측과 다르다. [합성 예시](../../contracts/portal-examples/flow.json), 기존 event v1.0·incident v1.0 소비자에는 포털 이벤트가 자동 호환되지 않는다. D가 정규화·탐지 룰을 연결해야 한다. v1.0에 이벤트 종류·필드를 더했으므로, 스키마를 고정해 검증하는 소비자(D의 validator·정규화)를 이 계약으로 먼저 갱신한 뒤 백엔드를 배포한다. 프론트 저장소의 계약 사본은 이벤트를 소비하지 않더라도 배포·인수 전에 같은 커밋으로 맞춘다.
