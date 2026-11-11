# S4 · S7 · S12 사전 이식 계획

> 조사 기준: 팀 저장소 `C:\SR\NoBugs\capstone\aleph-soar-capstone`의 2026-11-09 파일과 현재 저장소를 읽기 전용으로 비교했다. 이 문서는 파일을 복사하거나 설정을 반입하지 않는다.

## 결론

S4·S7·S12의 n8n 메인 워크플로와 S4 Graylog 정의는 현재 저장소에 팀 원본과 같은 해시로 이미 있다. S7·S12는 핵심 Graylog 정의와 실측 도구가 현재 저장소에 없으므로, 다음 구현 단계에서 원본을 선별 반입하고 현재 단일 PC 환경으로 다시 검증해야 한다.

## 파일 비교

| 케이스 | 팀 원본 | 현재 상태 | 다음 조치 |
| --- | --- | --- | --- |
| S4 | `infra/n8n/workflows/haedam-31-s4-main.json` | 동일 | 재반입 불필요. 자격 증명·웹훅·실측만 확인 |
| S4 | `lab/s1s4/graylog/s4-fail-then-success.json` | 동일 | 정적 검사 후 Graylog 반입 시점 결정 |
| S7 | `infra/n8n/workflows/haedam-33-s7-main.json` | 동일 | Wazuh API·Active Response 전제조건 확인 |
| S7 | `infra/n8n/workflows/haedam-34-s7-live-acceptance.json` | 동일 | 수동 승인 전용으로 유지 |
| S7 | `lab/s7/graylog/s7-rule-spec.md` | 없음 | 정의와 파이프라인 요구사항을 문서부터 반입 |
| S7 | `tools/make_s7_live_copy.py` | 없음 | 워크플로 생성 규칙 검토 후 반입 |
| S12 | `infra/n8n/workflows/haedam-20-s12-main.json` | 동일 | 재반입 불필요. 현재 S8/S10과 충돌 여부 확인 |
| S12 | `lab/s12/graylog/s12-request-flood.json` | 없음 | 정의·알림 초안을 반입 전 정적 검사 |
| S12 | `tools/s12_flood.py`, `s12_probe.py`, `s12_health.py` | 없음 | 전용 실측 도구를 별도 반입·로컬 테스트 |

## S4: 실패 뒤 성공 계정 잠금

### 필요한 구성

- Graylog 정의: `lab/s1s4/graylog/s4-fail-then-success.json`
- n8n 메인: `haedam-31-s4-main.json`
- 하위 동작: 기존 `haedam-13-portal-account-lock.json`, 결과 기록, Discord
- 실측 도구: `lab/s1s4/a_s4_step.py`, `s4_session_check.py`, `s4_metrics.py`

### 반입 전 확인

1. `lab/s1s4/graylog/check.py`가 S4 정의의 계정·출발지 결합 키와 경계 사례를 통과하는지 확인한다.
2. `haedam-13`의 `X-Response-Key`, `Idempotency-Key`, 관리자 계정 제외 규칙을 확인한다.
3. 정상 로그인·기존 세션 회수·담당자 해제 후 새 로그인 흐름을 분리해 측정한다.

### 위험

실제 계정 잠금은 세션을 회수한다. 합성 계정과 전용 출발지로만 실측하고, 관리자 계정은 대상에 포함하지 않는다.

## S7: 홈페이지 변조와 Wazuh 복구

### 필요한 구성

- Graylog 파이프라인: `infra/graylog/pipelines/wazuh-parse.txt`, `s7-parse.txt`
- 기준 해시 조회: `infra/graylog/lookup/s7_baseline_hashes.csv`
- n8n 메인·수동 승인: `haedam-33-s7-main.json`, `haedam-34-s7-live-acceptance.json`
- Wazuh: `haedam-17-wazuh-token.json`, `haedam-15-wazuh-restore.json`
- 실측·복구: `lab/s7/attack/*`, `lab/s7/restore/*`

### 반입 전 확인

1. Wazuh agent ID, n8n 전용 역할, Active Response 명령 허용 범위를 확인한다.
2. 기준 해시 CSV와 실제 정적 파일 해시를 다시 생성·대조한다.
3. 새 파일 격리와 기준본 파일 복구를 분리해 시험한다.
4. 복구가 만드는 FIM 이벤트가 새 인시던트로 재탐지되지 않는지 확인한다.

### 위험

S7은 실제 정적 파일을 바꾸고 Wazuh Active Response를 호출한다. 현재 컨테이너 기반 포털과 팀 VM의 경로·agent ID가 다를 수 있으므로 원본 워크플로를 그대로 실행하지 않는다.

## S12: 요청 폭주

### 필요한 구성

- Graylog 정의: `lab/s12/graylog/s12-request-flood.json`
- 알림: `infra/graylog/notifications/s12-n8n-haedam-s12.json`
- n8n 메인: `haedam-20-s12-main.json`
- 입력·건강 확인: `tools/s12_flood.py`, `s12_probe.py`, `s12_health.py`
- 비교·집계: `s12_baseline_calc.py`, `s12_compare_phases.py`

### 반입 전 확인

1. 정상 상태의 처리량·응답시간 기준선을 먼저 저장한다.
2. 합성 출발지와 테스트 URL만 사용하는지 확인한다.
3. 포털 IP 차단과 pfSense 차단이 S8·S10 차단 규칙과 겹칠 때 더 짧은 차단으로 완화되지 않는지 확인한다.
4. 차단 뒤 정상 출발지의 health check가 유지되는지 별도로 측정한다.

### 위험

S12는 의도적으로 부하를 만든다. H1·H2 실측, 포털 배포, 다른 사용자와 겹치는 시간에는 실행하지 않는다.

## 권장 이식 순서

1. H1·H2 실측과 배포가 완전히 끝난 뒤 S4를 먼저 정리한다. 기존 파일이 이미 있어 검증 범위가 가장 작다.
2. S12는 전용 기준선·health check를 먼저 이식한 뒤 정의와 워크플로를 붙인다.
3. S7은 Wazuh 권한·경로·기준 해시가 확정된 후 마지막에 진행한다.

## 공통 완료 기준

- 정적 정의 검사와 해당 로컬 테스트가 통과한다.
- n8n 자격 증명과 웹훅 인증이 반입 후에도 유지된다.
- 합성 입력 한 회차에서 탐지, 티켓, 대응 효과, 정상 경로, 원복을 모두 확인한다.
- 수치와 원본 로그를 티켓 문서에 남긴다.
