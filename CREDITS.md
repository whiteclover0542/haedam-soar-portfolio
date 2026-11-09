# 출처와 기여

이 저장소는 팀 NoBugs(Aleph)의 캡스톤 결과물을 반소람(whiteclover0542)이 PC 한 대에서 혼자 설치·실측할 수 있도록 다시 구성한 개인 포트폴리오입니다.

## 원본 저장소

| 원본 | 기준 커밋 |
| --- | --- |
| https://github.com/NoBugs-Aleph/aleph-soar-capstone (main) | `3ac60e8` |
| 같은 저장소 브랜치 `codex/pfsense-response-1026` | `bcaa586` |
| https://github.com/NoBugs-Aleph/haedam-portal-backend | `98e549c` |
| https://github.com/NoBugs-Aleph/haedam-portal-frontend | `994fc45` |

## 팀원과 담당 (2026-10-19 확정)

| 자리 | 이름 (GitHub) | 담당 |
| --- | --- | --- |
| A | 반소람 (whiteclover0542) | 포털 서비스·대응 API, S1·S4 계정 탈취 |
| B | 김명준 (myeongjundev) | pfSense·VPN, S8·S10 스캔→침입, 포털 프론트·백엔드 구현 |
| C | 김상혁 (shk12170-dev) | Wazuh, 티켓 저장소·보안 대시보드, S7 홈페이지 변조 |
| D | 김대훈 (chacha1650a) | Graylog·n8n, S12 서비스 장애 |

## 경로별 원작자

| 이 저장소 경로 | 원작자 | 원본 경로 |
| --- | --- | --- |
| `services/portal/backend`, `services/portal/frontend` | 김명준 (반소람: GELF TCP 전송, 대응 API 기여) | 포털 두 저장소 |
| `services/ticket-store`, `contracts/ticket-record.schema.json` | 김상혁 | `services/ticket-store` |
| `infra/graylog` (compose·파이프라인·알림) | 김대훈 | `infra/graylog` |
| `infra/n8n` (compose·워크플로·가드) | 김대훈 (케이스별 분기: 각 자리 담당) | `infra/n8n` |
| `lab/s1s4/graylog` (S1 탐지 정의) | 반소람 | `lab/s1s4/graylog` |
| `lab/s8s10`, `tools/s8s10_input.py` | 김명준 | 같은 경로 |
| `lab/pfsense`, `tools/build_pfsense_bundle.py`, `contracts/pfsense-response.schema.json` | 김명준 | 브랜치 `codex/pfsense-response-1026` |

PC 한 대 구성(compose·pfSense 컨테이너·반입 스크립트·티켓 실행기·문서)과 이 저장소에서 바뀐 부분은 반소람이 작성했습니다. 변경 이력은 git log를 참고하세요.
