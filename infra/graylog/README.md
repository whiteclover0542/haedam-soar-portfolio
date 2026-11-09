# 팀용 Graylog (D PC)

> **이 포트폴리오에서는:** 최상위 `compose.yaml`의 `soc` 프로필(mongodb·opensearch·graylog)로 띄우고 `python infra/graylog/bootstrap.py`로 입력·스트림·파이프라인·알림·이벤트 정의를 반입한다. pfSense Syslog는 lan에서 UDP 1514로 직접 받는다. 아래는 팀 4대 환경 당시의 원문이다.

D(chacha1650a)가 관제 PC에서 돌리는 Graylog입니다. 포털 GELF(A), pfSense Syslog(B), Wazuh 경보(C)를 받는 입구와 스트림만 둡니다.
작업 기준은 [Graylog 셋팅 작업지시](../../team_docs/2026-10-20%20Graylog%20셋팅%20작업지시.md)(초기 설치안), C의 Wazuh 인수인계(10/22), B의 D 인수인계(10/22)입니다. B 인수인계에 따라 작업지시의 과거 상태·수치는 오늘 상태로 복사하지 않고, 수업 볼륨은 보존하고 포트 충돌을 확인했습니다. **상태(10/23): 입력 5개·스트림 2개·파이프라인이 있고, 10/22에 실제 포털(A)·Wazuh(C)·pfSense(B) 로그가 팀 VPN을 거쳐 도착하는 것을 확인했습니다. 10/23 재부팅 뒤 다시 기동했고 입력 5개가 RUNNING, 스트림 규칙은 그대로입니다(재부팅 뒤 포털·Wazuh 새 로그는 아직 확인하지 않았습니다). content pack 내보내기는 아직 하지 않았습니다.**

## 보강 전 상태를 지킵니다

정량평가는 "보강 전 1회 → 보강 후 반복" 순서입니다. 그래서 이 셋팅에는 **입력·스트림·필드 파싱 파이프라인만** 넣고, 이벤트 정의(탐지 규칙)·알림·n8n 워크플로는 넣지 않습니다. 수업 이벤트 정의도 가져오지 않습니다. 각 자리의 규칙은 그 자리가 보강 전 시험을 마친 뒤에 넣습니다.

## 구성

| 파일 | 내용 |
| --- | --- |
| `docker-compose.yml` | Graylog 6.1.16, MongoDB 6.0.28, OpenSearch 2.5.0(버전 고정). 프로젝트 `haedam-soc`, 네트워크 `soc-net`, 컨테이너 `soc-*`, 볼륨은 `haedam-soc_*`라 수업 컨테이너(`gl-*`)·볼륨과 겹치지 않습니다 |
| `.env.example` | 필요한 값의 이름과 예시. 실제 값은 `.env`에만 두고 Git에 올리지 않습니다 |
| `set-admin-password.ps1` | 관리자 비밀번호를 직접 정해 SHA-256 해시만 `.env`에 저장합니다(비밀번호는 저장·출력하지 않음) |
| `pipelines/wazuh-parse.txt` | Wazuh 경보 JSON을 필드로 푸는 파이프라인 규칙(C의 연습 환경에서 동작, 이 환경에서는 미시험) |
| `pipelines/pfsense-parse.txt`, `pipelines/suricata-parse.txt` | pfSense filterlog 정규화와 Suricata EVE JSON 파싱 규칙(Graylog에 먼저 적용한 것을 10/27에 파일로 내보냄. 스트림 `pfsense`는 입력 `pfSense Syslog UDP`만 받는 규칙이라 TCP 메시지는 거치지 않음) |
| `pipelines/s7-parse.txt`, `lookup/` | S7 판정 규칙 3개(기준본 해시로 정상 배포·복구 제외)와 기준본 해시 CSV. 미반입, 반입 순서는 `lookup/README.md` |
| `notifications/` | 이벤트 → n8n 알림 정의 제안(S1 → `haedam-30`). 미반입, 반입 순서는 `notifications/README.md` |

메모리 제한은 시작값입니다(OpenSearch 2g, Graylog 2g, MongoDB 512m, 힙은 OpenSearch·Graylog 각 1g). 측정한 뒤 고칩니다.

## 포트

| 용도 | 호스트 | 컨테이너 | 열어 두는 곳 |
| --- | --- | --- | --- |
| 웹 화면 | 9000/tcp | 9000 | `WEB_BIND_IP`(기본 `127.0.0.1`. 팀원이 보려면 D의 팀 VPN 주소) |
| 포털 GELF (A) | 12201/udp, 12201/tcp | 12201 | `BIND_IP` |
| pfSense Syslog (B) | 514/udp, 514/tcp | 1514 | `BIND_IP` |
| Wazuh 경보 Raw TCP (C) | 5514/tcp | 5514 | `BIND_IP` |
| Suricata EVE JSON Raw TCP (B, pfSense) | 5515/tcp | 5515 | `BIND_IP` |

`WEB_BIND_IP`는 웹 화면, `BIND_IP`는 로그 입력 포트의 열림 주소입니다. 둘 다 팀 VPN 접속 전에는 `127.0.0.1`(이 PC 안)입니다. 접속한 뒤 D의 팀 VPN 주소로 바꿉니다. `0.0.0.0`으로 두면 학원 유선망에도 열리므로 쓰지 않습니다. Wazuh 수신 포트 5514는 D가 10/22에 고정했고 지금은 TCP만 받습니다(아래 "로그 수신 프로토콜"). 포트를 바꾸면 이 입력, compose 게시 포트, D 방화벽, C의 중계기 대상, B의 pfSense 허용 규칙을 함께 바꿔야 합니다.

## 실행 순서

1. `.env.example`을 `.env`로 복사합니다.
2. `GRAYLOG_PASSWORD_SECRET`을 무작위 긴 값으로 바꿉니다.
3. 본인 터미널에서 `.\set-admin-password.ps1`을 실행해 관리자 비밀번호 해시를 넣습니다.
4. 같은 PC에서 수업 Graylog가 떠 있으면 `docker stop gl-graylog gl-opensearch gl-mongo`로 멈추기만 합니다. `down -v`와 볼륨 삭제는 하지 않습니다(수업 자료 보존).
5. `docker compose up -d` 뒤 `docker compose ps`로 확인합니다.
6. 화면(`http://127.0.0.1:9000/`, `.env`의 `WEB_BIND_IP`를 바꿨으면 그 주소)에서 아래를 만듭니다.
   - 입력 5개: `haedam GELF UDP`·`haedam GELF TCP`(12201), `pfSense Syslog UDP`·`pfSense Syslog TCP`(1514), `wazuh Raw TCP`(5514, **Raw/Plaintext TCP**. Syslog 입력은 JSON을 깨뜨릴 수 있음). `wazuh Raw UDP`는 만들어 두었지만 꺼 둡니다
   - 스트림 `haedam-portal`(규칙 "match input" = `haedam GELF UDP` **또는** `haedam GELF TCP`, 규칙 조건은 OR. 포털 GELF의 `host`는 앱 `ASSET_ID`라서 `source`가 `haedam-portal`이라고 가정하지 않고 입력으로 모읍니다), 스트림 `wazuh-alerts`(규칙 "match input" = `wazuh Raw TCP`, Default Stream에서 빼기)
   - 파이프라인 `wazuh-parse`(`pipelines/wazuh-parse.txt`)를 `wazuh-alerts`에 연결하고 Stage 0·1에 규칙을 넣기
   - System → Configurations → Message Processors에서 Pipeline Processor가 Message Filter Chain보다 **뒤**에 오는지 확인
7. 입력·스트림만 content pack으로 내보내 `content-pack.json`으로 커밋합니다. 이벤트 정의·알림은 넣지 않고, 비밀값이 없는지 확인합니다.

## 웹 화면 공개와 열람용 계정 (10/22)

- 보강 전 측정에서 A·B·C가 Search·Alerts를 직접 확인할 수 있게 `.env`의 `WEB_BIND_IP`를 D의 팀 VPN 주소(`10.250.0.100`)로 두었습니다. 접속은 `http://10.250.0.100:9000`뿐이고 이 PC에서도 `127.0.0.1:9000`은 닫힙니다. 팀 VPN이 끊기면 이 주소에 포트를 붙이지 못해 컨테이너가 시작되지 않을 수 있습니다.
- 열람용 계정 `viewer-a`·`viewer-b`·`viewer-c`는 D가 Graylog에서 직접 만들었고 역할은 Reader뿐입니다(API로 확인). 비밀번호는 저장소·채팅에 두지 않고 개별 전달합니다. 새 계정으로 로그인해 읽기만 되는지는 확인하지 않았습니다.
- Windows 방화벽에는 Docker 백엔드(`com.docker.backend.exe`)의 TCP·UDP 수신 허용(Public 프로필, 원격 주소 제한 없음)이 이미 있어 별도 포트 규칙 없이 열립니다. 팀 VPN 대역으로 한정한 규칙은 만들지 않았습니다.
- Reader도 모든 스트림의 로그 본문을 볼 수 있습니다. 로그에 비밀값이 섞이지 않는지는 측정 전에 따로 확인해야 합니다.

## 로그 수신 프로토콜 (10/22): A·B는 UDP·TCP 둘 다, Wazuh는 TCP만

| 로그 | 받는 방식 | 이유 |
| --- | --- | --- |
| 포털 GELF (A) 12201 | UDP·TCP 둘 다 | 보내는 쪽이 어느 쪽을 써도 도착하게 둠 |
| pfSense Syslog (B) 514 | UDP·TCP 둘 다 | 같음 |
| Wazuh 경보 (C) 5514 | **TCP만** | 550(변경) 경보는 약 2KB(C `alerts.json` 기준 2,040B)이고, UDP로 보낸 시험에서 554(1,085B)·553(1,201B)은 왔지만 550만 빠졌습니다. 같은 550이 TCP로는 두 번 모두 도착했습니다. UDP 2KB 단독 시험은 하지 않았습니다 |

- 경로: C manager `syslog_output`(UDP 전용) → C의 중계 컨테이너 `wazuh-tcp-relay`(UDP 5514 → TCP) → 팀 VPN → D `10.250.0.100:5514/tcp`. 보낸 건수는 중계기 통계(`received/sent/dropped/queued`)로 대조합니다. 12:32 TCP 시험(`zz_field_033200`) 554·550·553 3/3 도착, 필드·해시 연결이 C 원본과 일치(C 확인).
- 경과: 11:27경 TCP로 바꿨다가 "팀 VPN이 TCP가 아니라서" UDP로 되돌렸으나, C→D 5514/tcp가 팀 VPN으로 실제 통과해 다시 TCP로 바꿨습니다. 그 사이 약 11:27~12:09(UDP 미수신)과 약 12:17~14:40(A·B UDP 미수신, compose가 TCP만 게시) 구간에 보낸 로그는 D에 없을 수 있습니다. 14:35~14:40에는 컨테이너 재생성·재시작으로 몇 분 끊겼습니다.
- 14:40 확인(이 PC에서 보낸 합성 표식): GELF UDP·TCP, Syslog UDP·TCP 각 도착, GELF는 `haedam-portal` 스트림에 들어감. 실제 pfSense filterlog가 UDP로 다시 들어옴. A 포털의 실제 GELF는 아직 확인하지 않았습니다.
- 주의: 514/udp는 재생성 직후 Docker가 게시 목록에 보여 주면서도 Windows에서 실제로 열리지 않았습니다(`Get-NetUDPEndpoint`에 없음). 컨테이너를 한 번 더 재시작하자 열렸습니다. 포트를 바꾼 뒤에는 `docker port`만 보지 말고 `Get-NetUDPEndpoint -LocalPort 514,12201`과 표식 로그로 확인합니다.
- 화면 설정(입력·스트림 규칙)은 content pack으로 내보낸 것이 아닙니다.

## 확인 결과 (10/22, D PC 한 대 안에서)

표식 로그는 이 PC의 UDP 소켓으로 직접 보낸 합성 값이며, 실제 포털·Wazuh·pfSense가 보낸 것이 아닙니다.

- [x] `docker compose ps`에서 세 컨테이너 실행(graylog healthy), `http://127.0.0.1:9000/api/`가 6.1.16 응답, OpenSearch green
- [x] 표식 로그 수신: GELF 3/3, Syslog 3/3, Raw UDP(Wazuh 모양의 JSON) 3/3. 보낸 건수 = 받은 건수
  - `haedam-portal` 스트림 3건(GELF), `wazuh-alerts` 스트림 3건(Raw UDP)
  - `wazuh-parse` 파이프라인으로 `wazuh_file`, `wazuh_syscheck_sha256_after`가 3건 모두 생기고, `wazuh_syscheck_event:added AND wazuh_rule_id:554`가 3건. 메시지는 `[Wazuh 554] ...`로, `source`는 agent 이름으로 바뀜
  - Syslog는 첫 시험에서 미래 시각(10:00)으로 보낸 3건이 "최근 15분" 검색에 안 보였고, 현재 시각으로 다시 보낸 3건과 함께 6건이 도착함(받은 쪽 시각이 메시지의 시각을 따름)
- [x] `docker compose restart graylog` 뒤 새 표식 로그 1건이 다시 검색됨(입력이 다시 실행됨)
- [x] Event Definitions에 케이스 규칙 없음(Graylog 기본 "System notification events" 하나뿐)
- [x] Message Processors 순서: Message Filter Chain → Stream Rule Processor → Pipeline Processor(규칙이 적용되는 순서)
- [x] 자원(부하 없음): soc-graylog 1.30GiB/2GiB, soc-opensearch 1.62GiB/2GiB, soc-mongo 66MiB/512MiB. 같은 PC에서 수업 Wazuh·n8n 컨테이너가 함께 돌 때 호스트 여유 RAM 0.4~1.6GB, WSL 여유 0.9~2.3GB에 스왑 1.2~1.4GB 사용. 부하를 걸지 않은 값이다. 수업 Wazuh 3개를 멈춘 뒤(n8n은 유지)에는 soc-graylog 1.41GiB, soc-opensearch 1.62GiB, n8n 247MiB, 호스트 여유 RAM 2.0GB, WSL 여유 3.5GB, 스왑 0.7GB 사용으로 줄었고 Graylog는 계속 정상 응답했다
- [x] 실제 포털 GELF가 `haedam-portal` 스트림에 도착(10/22, A가 보낸 `web.request` 등, `src_ip`가 Kali `203.0.113.10`으로 보임). `login-bruteforce` 등 케이스 필드 확인은 이벤트 정의 단계에서
- [x] 실제 Wazuh 경보 550·553·554가 TCP 5514로 3/3 도착하고 필드·해시가 C 원본과 일치(10/22 12:32, C 확인). 중계기 중복 전송 여부는 C와 확인 중
- [ ] pfSense filterlog는 도착하지만(10/23 10:14 최근 10분 523건) 본문의 출발지 필드 추출은 아직 하지 않았다(B, 공통 기반)
- [ ] content pack(입력·스트림만) 내보내기와 `content-pack.json` 커밋

## 아직 정하지 않은 것

- D의 팀 VPN 주소는 B가 `10.250.0.100`으로 고정했습니다. 재부팅·재접속 뒤에도 같은 주소가 유지되는지는 10/23 재접속에서 `10.250.0.100`을 확인했을 뿐 반복 확인은 하지 않았습니다. 이 주소가 바뀌면 `.env`의 `BIND_IP`·`WEB_BIND_IP`와 A의 `RESPONSE_ALLOWED_CIDRS`를 함께 고칩니다.
- 포털 GELF의 실제 `host`(ASSET_ID)와 `_event_type`·`_asset_id`가 Graylog에서 어떤 필드로 색인되는지: 실제 수신 뒤 확인합니다. S12 요청 수는 `web.request`로 한정해 세야 하고(한 요청의 `web.file_access`·인증 이벤트까지 합치면 중복 집계), `/assets/`·`/favicon.svg`는 `web.request`에서 제외됩니다(B 인수인계 5절).
- n8n은 `infra/n8n/`의 해담용 compose(`127.0.0.1:5678`, PR #40)로 옮겼습니다. 수업 워크플로는 10/22 09:56에 비활성화했습니다.
- Wazuh 경보는 C 중계기 → D `10.250.0.100:5514/tcp`로 받는 것으로 확정했습니다(12:32 시험 3/3). 중계기 재연결 때 중복 전송이 있는지는 C와 확인 중입니다.
- S7의 `file_key`·`asset_id` 규칙: C의 규칙 예시가 있지만, 보강 전 1회 측정이 끝나고 A·C와 자산 ID를 확정한 뒤 만듭니다.
- 이 PC의 시계: Windows 시간 서비스가 시작돼 있지 않아 NTP 동기화가 되지 않았습니다(10/22 확인). 판정 시각이 어긋나지 않게 시험 전에 맞춥니다.
- 수업 컨테이너: 수업 Wazuh·n8n·Graylog 컨테이너는 `restart: unless-stopped`라서 Docker가 다시 시작되면 함께 올라와 메모리를 씁니다(10/22 관찰). 수업 Graylog(`gl-mongo`, `gl-opensearch`)와 수업 Wazuh(`wazuh-manager`, `wazuh-indexer`, `wazuh-dashboard`)는 D의 승인으로 `docker stop`만 했습니다(삭제·볼륨 삭제 없음). n8n은 D의 작업이라 그대로 둡니다. 멈춘 컨테이너도 `unless-stopped`라 수동으로 멈추면 Docker 재시작 때 다시 올라오지 않습니다. 10/23 재부팅 뒤에는 수업 `gl-graylog`와 `flask_mysql`(`0.0.0.0:3306`)이 다시 올라와 있어 `docker stop`으로 멈췄습니다. 재부팅하면 다시 올라올 수 있으니 부팅 뒤 `docker ps`로 확인합니다.
- Docker 메모리: `.wslconfig`는 만들지 않았고 기본 한도(7.7GiB)로 시험했습니다. 수업 Wazuh를 멈춘 상태에서 부하 시험(S12) 전에 다시 측정해서 정합니다.

비밀번호·API 키·토큰은 이 폴더와 Git에 넣지 않습니다.
