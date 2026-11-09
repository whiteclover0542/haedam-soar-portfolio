# 진행 현황 (PROGRESS)

- 최종 갱신: 2026-11-09 · 반소람(whiteclover0542)
- 제출 기한: **2026-11-12(목) 10:00**. 학원 PC에서 강사가 README대로 설치하고, 티켓 1~2개를 그 자리에서 실측한다.
- 근거 문서: [MVP 설계](MVP-설계.md) · [구현 계획](MVP-구현계획.md) · [작업 일지](journal/) · [출처](../CREDITS.md)
- 표기: ⬜ 예정 · 🟡 진행 중 · ✅ 완료(실측·출력으로 확인한 것만) · ⛔ 막힘

## 지금 할 일

**Task 1 pfSense:** KVM을 확인했고 이미지 빌드도 끝났다. 지금은 ISO를 받는 중이다. 다음 순서는 다음과 같다.

1. `docker compose --profile pfsense up -d`
2. `127.0.0.1:8006` 콘솔에서 설치(WAN `em0` 203.0.113.1, LAN `em1` 10.250.0.1)
3. 웹 설정(포트 포워드·syslog·SSH)
4. 스파이크 판정: pfSense를 거쳐 200 응답, 출발지 보존, 차단 로그

## 한눈에 보기

| 단계 | 내용 | 상태 |
| --- | --- | --- |
| **MVP** | 5개 구성 동시 기동 + S10·S8·S1 실측 + README | 🟡 |
| H1 | 민원 도배 (가용성) | ⬜ |
| H2 | 타인 민원 엿보기 (기밀성) | ⬜ |
| H3 | 민원 처리 결과 조작 (무결성) | ⬜ |
| S4 | 실패 뒤 성공 → 계정 잠금 | ⬜ |
| S7 | 홈페이지 변조 (Wazuh FIM·AR) | ⬜ |
| S12 | 요청 폭주 | ⬜ |
| PPT | 개인 포트폴리오 PPT | ⬜ |
| 이력서 | 이력서·자기소개서 기본본 | ⬜ |
| H4 | 담당자 대량 조회 (여유 시) | ⬜ |

## MVP 작업 (구현 계획 Task 0~9)

| # | 작업 | 상태 | 확인 근거 |
| --- | --- | --- | --- |
| 0 | 저장소 반입·민감정보 검사·GitHub 비공개 저장소 | ✅ | 테스트 8개 통과, `secret_scan` 0건, `whiteclover0542/haedam-soar-portfolio` push |
| 1 | pfSense 컨테이너(QEMU/KVM) | 🟡 | KVM 사용 가능, 이미지 빌드 완료. 설치·스파이크 판정 전 |
| 2 | 서버(포털·MySQL·티켓 저장소) | ⬜ | |
| 3 | Graylog + 탐지 설정 자동 반입 | ⬜ | |
| 4 | n8n 워크플로·자격 증명 반입 | ⬜ | |
| 5 | Wazuh single-node | ⬜ | |
| 6 | 최상위 compose·`.env.example`·동시 기동 점검 | ⬜ | |
| 7 | 티켓 실행기, S10 → S8 → S1 실측 | ⬜ | |
| 8 | README·새 설치 리허설·공개 전환 | ⬜ | |
| 9 | 정량평가 요약 | ⬜ | |

## 결정 기록

| 날짜 | 결정 | 이유 |
| --- | --- | --- |
| 11/09 | fork 대신 새 저장소, 필요한 파일만 반입 | 팀 협업 자료를 빼고 출처는 `CREDITS.md`로 밝힘 |
| 11/09 | pfSense는 진짜 pfSense CE 2.7.2(QEMU 컨테이너) | 과제 요건. 대체 컨테이너는 쓰지 않음 |
| 11/09 | 검사 시연 티켓은 S10·S8, 본인 티켓 S1 동반 | S10 하나로 서버·Graylog·pfSense·n8n을 모두 보여줌 |
| 11/09 | 신규 케이스 H1~H3(가용성·기밀성·무결성), H4는 여유 시 | 시청 업무에 맞춘 차별점 |
| 11/09 | 팀 주소 체계(203.0.113.x / 10.250.0.x)를 Docker 망에 그대로 유지 | 워크플로·규칙·보호 IP 목록 수정 최소화 |

## 환경 상태 (학원 PC)

| 항목 | 상태 |
| --- | --- |
| Docker Desktop | 29.7.2, Compose v5.4.0, WSL2 메모리 약 12.5GB·CPU 16 |
| `.wslconfig` | `memory=12GB`, `vm.max_map_count=262144` |
| KVM | 사용 가능 |
| Docker Hub 로그인 | 안 함(필요 시 로그인) |

## 집 PC에서 이어 하기

1. Docker Desktop을 WSL2 백엔드로 설치하고, `.wslconfig`도 위와 같이 설정한다.
2. `gh auth login` → `gh repo clone whiteclover0542/haedam-soar-portfolio` → `git switch mvp`
3. `.env`를 새로 만든다(git에 없음). pfSense ISO를 받고 다시 설치한다.
4. Claude Code에서 이 파일, `git log`, 작업 일지를 읽고 첫 미완료 Task부터 이어 간다. 세부 진행 기록(`.superpowers/`)은 git에 올라가지 않으므로, PC 사이에서는 이 파일이 기준이다. Task가 끝날 때마다 이 표를 갱신한다.
