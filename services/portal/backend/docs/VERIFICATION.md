# 2026-10-19 로컬 검증

- 플랫폼: Windows, Python 3.12.10, Node 24.15.0, npm 11.12.1. 브랜치 `codex/haedam-portal-mvp`.
- SQLite: `python -m pytest -q` **27 passed, 1 skipped**. skip은 MySQL 행 잠금 전용 동시 요청 시험이다. 한국어 필드 오류 계약·입력값 미노출, 잘못된 답변 제출 시 상태 유지 검증 2건을 추가했다.
- 실제 일회용 MySQL 8.4 Docker: `python tools/check_mysql.py` **28 passed**. 마이그레이션 upgrade → db check(차이 없음) → 빈 QA DB downgrade → upgrade 통과. 같은 중복 키로 동시에 들어온 계정 잠금 2건은 200·같은 응답·세션 회수 1회였다. 필드 오류 검증을 포함해 최신 코드에서 재실행했다.
- `python tools/check_mysql_e2e.py`: 실제 MySQL **8.4.11** + Flask/Waitress + React/Edge 브라우저 **12 passed**. 기존 업무/사용성 11건과 MySQL 전용 영속성 1건이며 프론트 빌드·MySQL 마이그레이션·db check도 통과했다. 기본 SQLite 브라우저도 별도로 **11 passed** 재확인했다.
- MySQL 브라우저 시험에서 신청 직후 실제 서버 PID **40384→43492**, 답변 완료 후 **43492→35744**로 교체했다. 같은 시민/담당자 세션에서 데이터·답변·버전·이력을 재조회했다. 타인 목록/상세 원문 미노출과 CSRF 누락 거절, 한글·4바이트 문자 왕복도 확인했다.
- 별도 MySQL 읽기 감사: 합성 민원 id 1, status completed, version 4, 접수→배정→처리 중→완료 이력 4건, utf8mb4 왕복, Alembic `04440ce16125`, 스키마 차이 없음. UI/API 관찰과 DB 직접 감사 결과를 구분한다.
- QA 이미지 확인 digest: `sha256:24989179f58856db763f418010c1169fecc944e3ec1ea7e921572d83eb070f70`. 테스트용 컨테이너는 완료 후 제거했다. 팀 서비스용 MySQL 서버를 설치한 것은 아니다.
- 실제 Flask/Waitress + React 빌드: 프론트 Playwright/Edge **11 passed**. 신청→새로고침→다른 브라우저 담당자 배정/답변→시민 완료 확인, 가입·로그인 실패 재시도·타인 거절·XSS 문자열·로그아웃, 관리자 계정 생성/권한/잠금/재설정, 모바일·키보드·404, 비밀번호 변경·연결 오류, axe 자동 검사. 추가 사용성 검증은 이탈 경고·입력 유지·필드 오류·검색/분야/상태/페이지 복원·저장 중 이동·320/390px 가독성을 포함한다.
- 프론트 `npm run build` 통과, `npm install`/audit 당시 취약점 보고 0. 이는 취약점이 없다는 보증이 아니다.
- capstone **31 passed**, AI 생성물 **14개** 일치, 작업 DAG **6개** 검증. 포털 event v1.0과 오류 스키마/합성 예시를 기존 관제 계약과 구분했다. 오류에 선택적 fields를 추가하며 기존 code/message 응답을 유지한다.
- 로컬 기본 DB의 Alembic `db check` 차이 없음, Waitress 127.0.0.1:5000 헬스 응답 200 확인. 시작 스크립트 `tools/start.ps1` 확인.

검증 중 로그인 실패 401을 세션 만료로 잘못 처리하는 프론트 문제와 MySQL 외래키 인덱스의 downgrade 순서 문제를 수정한 후 통과했다. 본문 바로가기 초기 포커스와 작은 글씨 대비도 수정하고 재검증했다.

## 검증 한계와 전달

SQLite/일회용 MySQL 브라우저와 MySQL 백엔드 시험을 각각 수행했다. 팀 서비스 VM·상시 MySQL 배포, MySQL 서버 자체 재시작·백업 복원·실제 Graylog/Wazuh/n8n/pfSense 수신/탐지/대응/원복·NAT·두 PC 자원·공방전은 시험하지 않았다.

새 실행기는 비허용 DB를 연결 전에 거절하는 것도 확인했다. Windows venv 실행기와 실제 서버 PID를 구분하고 자체 프로세스 트리·컨테이너·임시 런타임을 정리한다. DB 자격 증명을 브라우저에 전달하지 않으며 MySQL 브라우저 트레이스는 끈다. 비밀값 없는 요약은 Git 제외 `.local/mysql-e2e-report.json`, 합성 화면은 프론트 `test-results/mysql-citizen-after-restart.png`다. 기존 5000 미리보기와 SQLite DB는 보존했다.

## 2026-10-27 · WQ04 관리자 전체 계정 조회

- 47be008에서 codex/admin-filter-1027로 분리했다. 기존 관리자 GET에 role/locked 교차 필터와 q만 적용한 전체 summary를 추가했다. 페이지 total/pages는 교집합 기준이며 집계는 검색어 기준으로 고정한다. 잘못된/중복 필터400, 빈 결과와 범위 밖 페이지, literal `%`/`_`, 비관리자401/403과 공개 User 필드 경계를 확인했다. DB 스키마·변경 API·권한/세션·이벤트 의미는 변경하지 않았다.
- capstone 계약 원본21d1848의 관리자 조회 문서·응답 스키마·합성 예시와 기존 포털 계약을 동기화했다. 기존 앱 IP 차단 중복 요청의 기간 유지 서술도 이미 구현된 backend 계약에 맞춰 원본에서 정리했으며 동작 변경은 없다.
- 신규 조회 회귀13개와 기존 전체를 합쳐 `.venv/Scripts/python.exe -m pytest -q`: **56 passed,3 skipped(43.39초)**.27계정 표본의12개 교차 조건·전체 페이지를 실제 test client/임시 SQLite로 읽고 새 응답 스키마로 검증했다. 역할/잠금/재설정 후 재집계·검색0건·필터 밖 페이지의 기존 total도 확인했다.
- Docker CLI는 있으나 dockerDesktopLinuxEngine 파이프가 없어 엔진 미가동을 확인했다. 이번 변경의 MySQL 전용 시험은 실행하지 않았으며 이전 MySQL 검증을 이번 결과로 세지 않는다. 학원 VM/운영 MySQL·부하·실장비 연동과 독립 리뷰는 미검증이다.
- 새 프론트는 summary 누락/불일치를 계약 오류로 처리한다. backend→frontend 순서로 채택하고 A/C가 정상 배포·FIM117 기준본을 맞춰야 한다.5005 사용자 미리보기는 재시작하지 않는다. 브라우저 검증은 별도5006의 새 임시 SQLite에서 수행하며 최종 짝과 결과는 frontend 구현 계획 및 capstone10/27 일지에 기록한다. PR·팀 메시지·장비/망·전역 설정 변경은 없다.

로그인·404·요청 이벤트의 JSONL은 로컬에서 확인했다. D는 포털 event v1.0 정규화와 Graylog 입력·n8n 경로를 연결하고, B는 실제 출발지·pfSense 차단·해제를 확인해야 한다. C는 실제 FRONTEND_DIST 경로와 정상 배포·FIM 기준본·복구를 맞춘다. 독립 팀 리뷰와 발표용 증적은 별도로 수행한다.

## 2026-10-27 · main 9507fce 일회용 MySQL 재검증

- 대상: main `9507fce`(backend #2 IP 차단·#3 username 잠금·#4 unlock 병합 뒤, 트리 `8c9b9d6` = `2cf7dcb`). 위 WQ04 항목에서 실행하지 못한 MySQL 전용 시험을 이 커밋으로 다시 돌렸다.
- 실제 일회용 MySQL 8.4 Docker(고정 digest): `python tools/check_mysql.py` **63 passed(91초)**. 마이그레이션 upgrade(`04440ce16125` → `7c2e9a41d5b3`) → db check(차이 없음) → 빈 QA DB downgrade → upgrade 통과. SQLite에서 건너뛰는 MySQL 행 잠금·동시 재생 시험 4건이 포함됐다. 같은 날 SQLite는 59 passed, 4 skipped.
- 실행 환경: Windows, 기존 클론의 venv에 `PYTHONPATH=src`로 이 트리의 소스를 불러 실행했다(불러온 모듈 경로 확인). 컨테이너는 스크립트가 지웠고 실행 뒤 Docker를 종료했다. 운영 MySQL(`10.10.20.10`)·포털 VM은 건드리지 않았다.
- 미실행: `check_mysql_e2e.py`(브라우저 전체 시험). 포털 VM 배포(17:18, `9507fce`)와 n8n → 112 실제 차단·해제(사전 시험)는 capstone 10/27 A 작업일지에 기록했다.
