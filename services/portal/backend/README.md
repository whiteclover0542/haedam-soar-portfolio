# 해담시청 민원포털 · Flask 백엔드

시민의 목소리를 담다, 해담시청. Python 3.12+, Flask 3.1.3, SQLAlchemy, Alembic, Waitress. 프론트는 형제 폴더 `haedam-portal-frontend`의 React 앱이다.

시민 로그인·가입·민원 신청/본인 조회, 담당자 배정/상태 처리/답변·이력, 관리자 계정/권한/잠금/비밀번호 재설정, 서버 저장 세션·CSRF·세션 회수, JSONL/GELF 이벤트와 제한된 계정·IP 차단 대응 API를 구현했다. 담당: B + Codex. 독립 팀 리뷰와 실제 두 PC 관제 연결은 별도다.

## Windows에서 실행

두 저장소를 같은 상위 폴더에 둔다. 최초 준비와 빌드:

```powershell
cd haedam-portal-backend
.\tools\start.ps1 -Setup -SeedDemo
```

빈 DB에만 합성 계정·민원 3건을 생성하고 이번 실행의 임시 비밀번호를 콘솔에 한 번 표시한다. `citizen_demo`, `staff_demo`, `admin_demo`는 합성 계정이다. 기존 DB가 있으면 `-SeedDemo`를 빼고 실행한다. 실제 정보·다른 서비스 비밀번호를 넣지 않는다. 준비 이후 재실행:

```powershell
.\tools\start.ps1
```

주소 `http://127.0.0.1:5000`. 종료 Ctrl+C. 다른 프로세스가 사용 중이면 `-Port 5010`. Waitress는 루프백에만 바인딩하며 프록시를 추가하지 않는다. `.env.example`을 `.env`로 복사하면 시작 스크립트가 허용된 환경값만 읽는다.

Python 도구만 준비할 때는 `python tools/bootstrap.py`. Linux는 `.venv/bin/python`으로 동일 Flask 명령을 쓰고 `waitress-serve --host=127.0.0.1 --port=5000 --call haedam_portal:create_app`을 실행한다. 프론트 빌드가 없으면 `/`는 503으로 명시한다.

## DB·마이그레이션

환경값이 없으면 `instance/haedam.sqlite3`를 사용한다. 이는 로컬 개발용이며 팀 배포 계획은 MySQL이다. 비밀값·DB·이벤트 파일·로그는 Git에서 제외한다.

```powershell
# DATABASE_URL은 자신의 비밀값으로 현재 셸에 설정한다.
# URL 형식: mysql+pymysql://USER:PASSWORD@HOST/haedam?charset=utf8mb4
.\.venv\Scripts\python.exe -m flask --app haedam_portal:create_app db upgrade
.\.venv\Scripts\python.exe -m flask --app haedam_portal:create_app db check
.\.venv\Scripts\python.exe -m flask --app haedam_portal:create_app create-admin
```

`create-admin`은 비밀번호를 숨김 입력받는다. 시작 시 임의 관리자·테이블을 자동 생성하지 않는다. DB 백업 후 배포하며, `db downgrade base`는 모든 포털 데이터를 지우므로 실제 데이터가 있는 DB에 실행하지 않는다. 되돌리기 검증은 폐기 가능한 QA DB에서만 했다. 스키마: users, login_sessions, petitions, petition_history, response_receipts, login_attempts.

## 검증

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools/check_mysql.py
.\.venv\Scripts\python.exe tools/check_mysql_e2e.py
```

첫 명령은 임시 SQLite, 둘째는 Docker가 필요하며 고유 이름·랜덤 루프백 포트·일회용 비밀번호의 MySQL 8.4 컨테이너를 만들고 검사 뒤 제거한다. 기존 DB·컨테이너를 건드리지 않는다. 인증·세션 만료/회수·CSRF·소유권·동시 버전·개인정보 제외 이벤트·대응 중복/망 검사·MySQL 동시 호출을 검증한다. 실제 브라우저 테스트는 프론트 `npm run test:e2e`.

`check_mysql_e2e.py`는 Docker와 형제 프론트의 `npm ci`·Edge가 필요하다. digest로 고정한 일회용 MySQL을 시작하고 React를 빌드한 뒤 실제 Flask/Waitress에서 브라우저 전체 테스트를 실행한다. 5005가 사용 중이면 기존 서버를 보존하고 중단한다. 신청 직후와 답변 완료 후 실제 Waitress 프로세스를 교체해 같은 세션의 데이터·이력 유지, 한글/4바이트 문자, 타인 조회 거절을 확인한다. 추가로 MySQL을 직접 읽어 상태·버전·이력을 감사하고 `db check`를 실행한다.

재시작 제어는 실행기 소유의 임시 파일로만 전달하며 업무용 재시작 HTTP API는 없다. 브라우저 러너에 DB 자격 증명을 전달하지 않고 MySQL 실행의 Playwright 트레이스를 끈다. 성공·실패 모두 자체 프로세스 트리·컨테이너·임시 런타임을 정리한다. 비밀값 없는 결과 요약은 Git 제외 `.local/mysql-e2e-report.json`, 합성 화면은 프론트 `test-results/mysql-citizen-after-restart.png`다. 기본 5000 미리보기·기존 SQLite를 MySQL로 전환하는 명령은 아니다.

## 연결 계약

- 관리자 `GET /api/v1/admin/users`는 검색(q)·권한(role)·이용 상태(locked=true/false)·페이지 크기를 서버에서 적용한다. 목록 total은 조건의 교집합, summary는 검색어만 적용한 전체의 권한별/잠금별 집계다. [관리자 조회 계약](docs/haedam/ADMIN-USERS-API.md)을 따른다. DB 마이그레이션·변경 API·세션 정책은 바꾸지 않는다. 새 프론트는 summary가 필요하므로 백엔드→프론트 순서로 배포한다. 현재 실행 중인 구 서버는 소스 변경만으로 새 API가 되지 않는다.

- [포털 API](docs/haedam/PORTAL-API.md), [계약 출처](contracts/README.md), [게시판 참고 범위](docs/BENCHMARK.md).
- 브라우저는 `/auth/me`의 CSRF를 메모리에 두고 HttpOnly 세션 쿠키를 사용한다. 토큰을 localStorage에 저장하지 않는다.
- 프론트 dist의 정적 파일과 명시한 화면 라우트만 제공한다. 없는 경로는 404와 `web.not_found`. 출발지는 `remote_addr`로 통일하며(`common.client_ip`, IPv4-mapped 주소는 IPv4로) 전달 헤더를 신뢰하지 않는다.
- `FRONTEND_DIST`의 실제 배포 폴더가 C의 FIM 감시 대상이다. 소스 src를 감시하는 것과 다르다.
- 기본 이벤트는 `instance/events.jsonl`. `GELF_ENABLED=1`, 실제 `GELF_HOST`/`GELF_PORT`를 설정하면 UDP 전송한다. `GELF_TRANSPORT=tcp`이면 GELF TCP(널 바이트 구분)로 보낸다. 요청은 큐에 넣기만 하고 백그라운드 스레드 하나가 보낸다(연결 제한 2초). 송신에 실패하면 같은 메시지(같은 event_id·발생 시각)를 Graylog가 돌아올 때까지 1·2·5초 간격으로 다시 보내고, 큐(1,000건)가 찬 동안 들어온 메시지만 경고를 남기고 버린다. JSONL은 송신 전에 기록하고 지우지 않으므로 버린 메시지도 event_id로 찾을 수 있다. 끊기기 직전에 도착한 메시지가 다시 갈 수 있어 중복은 event_id로 대조하고, 포털을 재시작하면 큐에 남은 메시지는 사라진다. 그래서 Graylog가 느리거나 막혀도 포털 응답은 늦어지지 않는다. 어느 방식이든 송신 성공은 Graylog 처리 증명이 아니고, 로컬 JSONL이 실측 출처다. route template·계정 식별자만 기록하고 민원 제목/본문·표시 이름·비밀번호·토큰·쿼리를 제외한다. web.request는 S12 후보 입력이며 탐지 판정이 아니다. 실제로 내준 파일은 `web.file_access`에 웹 루트 기준 `file_key`(예: `assets/app.js`, 화면 경로는 `index.html`)를 남겨 S7 FIM 경로와 묶는다.
- `RESPONSE_API_KEY`와 `RESPONSE_ALLOWED_CIDRS`가 모두 설정돼야 계정·IP 차단 대응 API를 호출할 수 있다. 프론트에 키를 넣지 않는다. 키 인증·관리망·중복 방지·대상 제한은 로컬로 검증했다. 계정 잠금은 id 경로(`/api/v1/response/accounts/{id}/lock`)와 S4 이벤트용 username 경로(`POST /api/v1/response/accounts/lock`, 본문 `{username}`)가 있고, 해제(`/reset`)는 사람이 id 경로로만 한다. 앱 IP 차단(`/api/v1/response/ips/block`·`/unblock`, 조회 `GET /api/v1/response/ips`)은 차단된 출발지의 모든 요청에 403 `IP_BLOCKED`를 주고, `RESPONSE_ALLOWED_CIDRS` 안의 주소는 새로 차단할 수 없고, 남은 차단 행이 있어도 막지 않는다(자기 차단 방지). 해제는 주소와 관계없이 허용하므로 허용 대역을 바꾼 뒤에는 그 대역의 기존 차단을 해제로 정리한다. 같은 주소·같은 키의 요청이 동시에 겹치면 서버가 새 트랜잭션으로 다시 처리해 같은 키는 처음 응답을 재생한다. 다른 키로 다시 차단하면 더 긴 차단(무기한 우선)을 유지하고, 차단이 늘어났을 때만 `changed:true`다. pfSense 차단·인시던트·FIM 복구는 제공하지 않는다.
- 차단 여부를 DB에서 확인하므로, DB가 응답하지 않으면 화면·정적 파일·대응 API까지 503으로 응답한다(fail-closed: 차단을 확인할 수 없으면 막는다). `/api/v1/health`로 준비 상태를 확인하고, DB가 돌아오면 별도 조치 없이 회복된다. DB 연결 시간 제한은 따로 설정하지 않았고 드라이버 기본값을 따른다. 실제 DB 장애·부하 시험은 하지 않았다.
- 웹 루트 기준 file_key 규칙(`/` 구분, 200자 이하, `.`·`..`·빈 세그먼트·드라이브 접두사·제어문자·`?`·`#`·백슬래시 없음)을 지키지 못하는 정적 파일은 내주지 않는다(404). 프론트 빌드 산출물의 이름은 이 규칙 안에 있다.
- `DASHBOARD_URL`은 관리자의 관제 링크다. 주소 미설정이면 링크를 만들지 않는다. 관제 서비스 자체 인증은 별도다.

외부 Graylog·Wazuh·n8n·pfSense 연결, 실제 NAT 출발지 보존, 두 PC 자원·시연 측정, 강사님 수업 코드 공유 확인은 이 구현의 검증 범위에 포함되지 않는다. 인터넷 공개 배포를 수행하지 않았다.

입력 검증 실패는 기존 `error.code/message`와 함께 선택적인 `error.fields`를 반환한다. 키는 필드 식별자이고 값은 한국어 안내이며, 잘못 입력한 원문·비밀번호는 오류 응답에 반영하지 않는다. 프론트는 이를 해당 입력란에 연결하고 오류 위치로 포커스를 옮긴다. [오류 스키마](contracts/portal-error.schema.json)와 [합성 예시](contracts/portal-examples/validation-error.json)를 계약 원본과 함께 관리한다.

적용한 계약 원본: capstone `d134c71a6a9ae941c149c969ca42884348197eba`. 계약 사본 8개와 해시는 [SOURCE.json](docs/SOURCE.json)에 고정했다. 공통 규칙 v3 원본은 `5e79d461d71e5f70c4daf0288572624a0962f817`이며 자세한 해시·초기 이력은 [SOURCE.json](docs/SOURCE.json)에 있다.
