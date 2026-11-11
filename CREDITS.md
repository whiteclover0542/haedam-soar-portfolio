# 출처와 기여

이 저장소는 팀 NoBugs(Aleph)의 캡스톤 결과물을 A(whiteclover0542)가 PC 한 대에서 혼자 설치·실측할 수 있도록 다시 구성한 개인 포트폴리오입니다.

## 원본 저장소

| 원본 | 기준 커밋 |
| --- | --- |
| https://github.com/NoBugs-Aleph/aleph-soar-capstone (main) | `3ac60e8` |
| 같은 저장소 브랜치 `codex/pfsense-response-1026` | `bcaa586` |
| https://github.com/NoBugs-Aleph/haedam-portal-backend | `98e549c` |
| https://github.com/NoBugs-Aleph/haedam-portal-frontend | `994fc45` |

## 팀원과 담당 (2026-10-19 확정)

| 자리 | GitHub | 담당 |
| --- | --- | --- |
| A | whiteclover0542 | 포털 서비스·대응 API, S1·S4 계정 탈취 |
| B | myeongjundev | pfSense·VPN, S8·S10 스캔→침입, 포털 프론트·백엔드 구현 |
| C | shk12170-dev | Wazuh, 티켓 저장소·보안 대시보드, S7 홈페이지 변조 |
| D | chacha1650a | Graylog·n8n, S12 서비스 장애 |

## 경로별 원작자

| 이 저장소 경로 | 원작자 | 원본 경로 |
| --- | --- | --- |
| `services/portal/backend`, `services/portal/frontend` | B (A: GELF TCP 전송, 대응 API 기여) | 포털 두 저장소 |
| `services/ticket-store`, `contracts/ticket-record.schema.json` | C | `services/ticket-store` |
| `infra/graylog` (compose·파이프라인·알림) | D | `infra/graylog` |
| `infra/n8n` (compose·워크플로·가드) | D (케이스별 분기: 각 자리 담당) | `infra/n8n` |
| `lab/s1s4/graylog` (S1 탐지 정의) | A | `lab/s1s4/graylog` |
| `lab/s8s10`, `tools/s8s10_input.py` | B | 같은 경로 |
| `lab/pfsense`, `tools/build_pfsense_bundle.py`, `contracts/pfsense-response.schema.json` | B | 브랜치 `codex/pfsense-response-1026` |

PC 한 대 구성(compose·pfSense 컨테이너·반입 스크립트·티켓 실행기·문서)과 이 저장소에서 바뀐 부분은 A가 작성했습니다. 변경 이력은 git log를 참고하세요.

## 팀 원본에서 바꾼 부분

PC 한 대에서 동작시키느라 원작 파일을 고친 곳입니다. 동작 판단 로직은 바꾸지 않았고, 이유는 [작업 일지](docs/journal/2026-11-09.md)에 있습니다.

| 파일 | 원작자 | 바꾼 내용 | 이유 |
| --- | --- | --- | --- |
| `lab/pfsense/pfsense_response.py` | B | `easyrule` 뒤 테이블 반영을 최대 15초 기다림. 승인 해시 `f0eea297…` → `c9f561ba…`(`install_bundle.py`·`tools/build_pfsense_bundle.py`·`lab/pfsense/INSTALL.md`) | 실제 장비에서 반영이 약 2초 늦어 즉시 읽기가 `outcome_needs_reconciliation`이 됨 |
| `infra/n8n/workflows/haedam-50-release.json` | D | 본문 `dry_run:false`일 때만 실제 해제, 웹훅에 Header Auth(`haedam-release caller`) | 해제가 코드에 고정된 관찰 모드였고, 웹훅에 인증이 없었음 |
| `infra/n8n/workflows/haedam-11-discord-notify.json` | D | 본문을 티켓 카드(embed: 색 막대·IP·심각도·계정·티켓·상태 칸)로, Discord 노드가 embed를 보냄 | 알림을 한눈에 읽게(사용자 요청) |
| `infra/n8n/workflows/haedam-15·17` | D | Wazuh API 주소 `10.250.0.3:55000` → `10.250.0.4:55000` | 단일 PC 주소 |
| `infra/graylog/pipelines/pfsense-parse.txt` | B | 파일은 그대로. 반입할 때 `bootstrap.py`가 단계별 규칙을 한 줄씩으로 바꿔 넣음 | Graylog API 문법 |
| `infra/wazuh/config/*` | Wazuh Inc.(wazuh-docker v4.9.2, GPLv2) | 인증서 경로를 생성기 파일 이름으로, 비밀번호를 `.env`로(`internal_users.yml`은 템플릿에서 생성) | 바인드 마운트 키 권한 문제, 기본 비밀번호 제거 |
| `services/ticket-store/compose.yaml`, `infra/n8n/docker-compose.yml`, `infra/graylog/docker-compose.yml` | C·D | 삭제. 최상위 `compose.yaml`로 대체 | 네트워크를 한 곳에서 정의 |

새로 추가한 것(A): `infra/n8n/workflows/haedam-03-pf-status-check.json`(pfSense 상태 확인), `infra/graylog/bootstrap.py`, `infra/n8n/{make_credentials,load}.py`, `infra/wazuh/make_users.py`, `infra/pfsense/`, `lab/{run_ticket,portal_login}.py`, `tools/{check_stack,summarize_runs}.py`, `compose.yaml`.
