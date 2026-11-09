# MVP 구현 계획 (S10 · S8 · S1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**목표:** 학원 PC 한 대에서 `docker compose`로 5개 구성(서버·Graylog·Wazuh·pfSense·n8n)을 띄우고, S10·S8·S1을 공격 → 탐지 → 자동 대응 → 복구까지 혼자 재현·실측한다.

**구조:** 팀 4대 분산 환경의 주소 체계를 Docker 네트워크 두 개로 그대로 옮긴다.
- **`wan`(203.0.113.0/24):** 공격자·정상 사용자
- **`lan`(10.250.0.0/24, 옛 팀 VPN 대역):** 포털·티켓 저장소·Graylog·n8n·Wazuh

pfSense CE 2.7.2는 QEMU 컨테이너 안 VM으로 돌리고, NIC 두 개를 각 네트워크에 브리지한다. 주소가 그대로라 팀 워크플로·탐지 규칙·보호 IP 목록을 거의 고치지 않고 쓴다.

**기술:** Docker Desktop(WSL2), compose `include`·`profiles`, QEMU/KVM, pfSense CE 2.7.2, Graylog 6.1.16·OpenSearch 2.5.0·MongoDB 6.0.28, Wazuh 4.9.2 single-node, n8n 2.39.5, Flask(포털·티켓 저장소)·MySQL 8.4, React 19(Vite 빌드), Python 3.12

**설계:** [docs/MVP-설계.md](MVP-설계.md)

## 전역 제약

- 소스 기준은 다음과 같다.
  - 팀 `origin/main` `3ac60e8`
  - pfSense 도구: 브랜치 `origin/codex/pfsense-response-1026`, `bcaa586`
  - 포털 백엔드 `98e549c`, 프론트 `994fc45`
- 위치: `C:\SR\NoBugs\capstone\{aleph-soar-capstone, Alephhaedam-portal-backend\haedam-portal-backend, Alephhaedam-portal-frontend\haedam-portal-frontend}`
- 비밀값은 `.env`에만 둔다. `.env`는 `.gitignore`에 넣고, 저장소에는 `.env.example`만 둔다. 필수 값이 비면 compose가 `${VAR:?설명}`으로 멈춘다.
- 호스트에 여는 포트는 모두 `127.0.0.1:`에 바인딩한다.
- WSL2 설정(`%USERPROFILE%\.wslconfig`): `memory=12GB`, `kernelCommandLine = sysctl.vm.max_map_count=262144`
- 팀원 코드는 파일 머리말 또는 `CREDITS.md`에 이름을 적는다.
  - 포털: 김명준
  - pfSense 도구·S8/S10 규칙: 김명준
  - 티켓 저장소·대시보드·S7: 김상혁
  - Graylog·n8n 구성·S12: 김대훈
  - S1·S4 규칙·스크립트: 반소람
- 실측값은 이 PC에서 잰 것만 `docs/tickets/`에 적는다. 팀 측정값을 옮길 때는 "팀 공통(4대 분산)"으로 표시한다.
- 커밋 메시지 끝에는 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`를 붙인다.

### 주소 표 (모든 작업이 이 값을 쓴다)

| 이름 | 네트워크 | IP | 호스트 포트 |
| --- | --- | --- | --- |
| Docker 게이트웨이 | wan / lan | 203.0.113.254 / 10.250.0.254 | — |
| pfSense WAN `em0` / LAN `em1` | wan / lan | 203.0.113.1 / 10.250.0.1 | — |
| `pf-ui`(socat 중계, pfSense 웹·SSH) | lan | 10.250.0.10 | 127.0.0.1:8443→10.250.0.1:443 |
| pfSense 설치 콘솔(QEMU VNC 웹) | — | — | 127.0.0.1:8006 |
| `portal`(백엔드+프론트 빌드) | lan | 10.250.0.2 | 127.0.0.1:8080→5000 |
| `mysql` | lan | 10.250.0.5 | 없음 |
| `ticket-store` | lan | 10.250.0.3 | 127.0.0.1:8089(대시보드) |
| `wazuh.manager` / `indexer` / `dashboard` | lan | 10.250.0.4 / .6 / .7 | 127.0.0.1:8443은 pfSense가 쓰므로 대시보드는 127.0.0.1:5601 |
| `graylog` / `opensearch` / `mongodb` | lan | 10.250.0.100 / .101 / .102 | 127.0.0.1:9000 |
| `n8n` | lan | 10.250.0.103 | 127.0.0.1:5678 |
| `attacker`(S1 `.11`, S8 `.21`, S10 `.22` 별칭 IP) | wan | 203.0.113.11 / .21 / .22 | 없음 |
| `normal`(정상 사용자) | wan | 203.0.113.100 | 없음 |

- **포트 포워드:** pfSense WAN 203.0.113.1:80 → 10.250.0.2:5000. NAT는 출발지 주소를 보존한다.
- **복귀 경로:** `portal` 컨테이너에 `ip route add 203.0.113.0/24 via 10.250.0.1`을 둔다(`cap_add: NET_ADMIN`). 이 경로가 없으면 응답이 Docker 게이트웨이로 새서 연결이 끊긴다.

## 리뷰 중점

1. **같은 출발지로 15분 안에 재시험:** Graylog `grace_period`(S8·S10 15분, S1 30분) 때문에 알림이 안 나간다. 실행기는 직전 실행 시각을 기록해 두고, 창 안이면 거부하고 남은 시간을 출력해야 한다. → Task 7 테스트
2. **이전 회차 차단이 남은 상태:** 포털 `blocked_ips`나 pfSense 테이블에 남은 항목이 있으면 다음 실측이 오염된다. 실행기의 사전 점검이 잔여를 발견하면 중단해야 한다. → Task 7 테스트
3. **정상 사용자 셀프 차단:** 차단 중에도 `203.0.113.100`은 200이어야 하고, 호스트(10.250.0.254)는 보호 대역(10.250.0.*)이라 차단되면 안 된다. → Task 7 실측 단계에서 단언
4. **빈 볼륨 첫 기동:** MySQL이 준비되기 전에 마이그레이션이 돌면 포털이 죽는다. → Task 2의 `down -v` 후 기동 검증
5. **`.env` 값 누락:** 조용히 빈 키로 뜨면 안 되고, compose가 어떤 값이 빠졌는지 말하며 멈춰야 한다. → Task 6 검증

---

### Task 0: 개인 저장소 초기화와 소스 반입

**파일**
- 만들기: `.gitignore`, `CREDITS.md`, `tools/secret_scan.py`, `tests/test_secret_scan.py`
- 반입(복사):
  - 팀 `origin/main`의 `infra/graylog/{pipelines,notifications,lookup}`, `infra/n8n/{workflows,guards}`, `lab/s1s4`, `lab/s8s10`, `services/ticket-store`, `tools/s8s10_input.py`, `contracts/`
  - 브랜치 `bcaa586`의 `lab/pfsense/`
  - 포털 두 저장소의 `git archive HEAD` 결과를 `services/portal/backend/`·`services/portal/frontend/`에 넣는다. 단 `AGENTS.md`·`CLAUDE.md`·`CODEX.md`는 뺀다.
  - 로컬 미커밋 `lab/s1s4/a_s1_step.py`(본인 작성)
- 반입 안 함: 설계 2절의 비목표 목록

**인터페이스**
- 만드는 것: `python tools/secret_scan.py [경로...]` → 발견 시 `파일:줄: 패턴이름`을 출력하고 종료 코드 1, 없으면 0
- 패턴:
  - Discord 웹훅 `discord(app)?\.com/api/webhooks/\d+/`
  - `-----BEGIN [A-Z ]*PRIVATE KEY-----`
  - `(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['"]?[A-Za-z0-9/+_-]{16,}`
  - `.env.example`의 `change-me`·`replace-with` 자리표시는 허용한다.

- [x] **1단계:** `git init`을 하고 `.gitignore`에 `.env`, `*.qcow2`, `*.iso`, `.venv/`, `__pycache__/`, `node_modules/`, `dist/`, `instance/`, `.pytest_cache/`를 넣는다.
- [x] **2단계:** 실패하는 테스트를 쓴다. `tests/test_secret_scan.py`
  - `test_flags_discord_webhook`: 임시 파일에 `https://discord.com/api/webhooks/123/abc` → 종료 1
  - `test_flags_private_key`: `-----BEGIN OPENSSH PRIVATE KEY-----` → 종료 1
  - `test_allows_placeholder`: `GRAYLOG_PASSWORD_SECRET=change-me-to-a-long-random-string` → 종료 0
- [x] **3단계:** `python -m pytest tests/test_secret_scan.py -v`를 돌려 FAIL을 확인한다.
- [x] **4단계:** `tools/secret_scan.py`를 구현한다. `re`와 `pathlib`만 쓴다. 인자가 없으면 `git ls-files` 대상을 본다.
- [x] **5단계:** 같은 명령으로 PASS를 확인한다.
- [x] **6단계:** 위 반입 목록을 복사하고 `python tools/secret_scan.py`를 돌린다. 발견이 0이 될 때까지 값을 `.env` 참조로 바꾼다. 무엇을 뺐는지 `docs/journal/2026-11-09.md`에 적는다.
- [x] **7단계:** `CREDITS.md`에 반입 경로별 원작자와 원본 커밋 해시 표를 쓴다.
- [x] **8단계:** 커밋한다. `chore: 팀 저장소에서 MVP 소스 반입, 민감정보 검사 도구`
- [x] **9단계(집 PC 이어 작업용):** 사용자에게 저장소 이름과 공개 여부를 확인받는다. `secret_scan` 0건을 다시 확인한 뒤 `gh repo create <이름> --private --source . --push`를 실행한다. 제출 직전 Task 8에서 공개로 바꾼다. 이후 작업 단위마다 push한다.

### Task 1: pfSense 컨테이너 (스파이크 겸 구성)

**파일**
- 만들기: `infra/pfsense/Dockerfile`, `infra/pfsense/entrypoint.sh`, `infra/pfsense/compose.yaml`, `infra/pfsense/config.xml`(Task 끝에 내보낸 뒤 민감정보 제거), `infra/pfsense/INSTALL.md`

**인터페이스**
- 만드는 것: 서비스 `pfsense`(WAN 203.0.113.1, LAN 10.250.0.1, SSH 22, 웹 443), `pf-ui`(10.250.0.10)
- 네트워크 이름은 `wan`·`lan`이며, 이후 모든 compose가 `external: false`로 같은 이름을 쓴다(최상위 compose에서 정의).
- 만드는 것: pfSense 안에 `/usr/local/sbin/haedam-pf-response`(김명준 도구, `lab/pfsense/install_bundle.py --install`)와 SSH 계정 `haedam-pf`. 이 계정은 공개키와 forced command로 위 도구만 실행한다.

**방식**
- 이미지는 `alpine:3.20`에 `qemu-system-x86_64`, `qemu-img`, `iproute2`, `novnc`를 넣는다.
- entrypoint는 다음을 한다.
  - `br0`(eth0+tap0), `br1`(eth1+tap1)을 만들고 eth0·eth1의 IP를 비운다.
  - `/dev/kvm`이 있으면 `-enable-kvm`, 없으면 TCG로 띄운다.
  - NIC는 `-device e1000`, 디스크는 볼륨의 `pfsense.qcow2`(8GB, 없으면 생성), 설치 전에는 ISO로 부팅한다.
- 컨테이너 권한은 `cap_add: [NET_ADMIN]`, `devices: [/dev/net/tun, /dev/kvm]`이다. KVM이 없을 때를 대비해 `devices`는 `.env`의 `PFSENSE_KVM`으로 고른다.

- [x] **1단계:** Docker Desktop을 켜고 `docker run --rm --device /dev/kvm alpine ls -l /dev/kvm`을 실행한다. 결과(있음/없음)를 저널에 적는다.
- [x] **2단계:** Dockerfile·entrypoint·compose를 쓰고 pfSense CE 2.7.2 ISO를 받는다(`atxfiles.netgate.com/mirror/downloads/pfSense-CE-2.7.2-RELEASE-amd64.iso.gz`, SHA-256 확인). `INSTALL.md`에 받는 명령을 적는다.
- [x] **3단계:** `127.0.0.1:8006` 콘솔에서 설치한다. 인터페이스는 WAN `em0`=203.0.113.1/24, LAN `em1`=10.250.0.1/24로 지정한다. 화면 순서를 `INSTALL.md`에 캡처와 함께 적는다.
- [x] **4단계:** 웹(127.0.0.1:8443)에서 다음을 설정한다.
  - 포트 포워드 WAN:80→10.250.0.2:5000
  - WAN 차단 기본 규칙 로깅 켜기
  - 원격 syslog 10.250.0.100:1514 UDP(filter 로그, Graylog 입력 포트. 11/09 514에서 변경)
  - SSH 켜기
  - `lab/pfsense/INSTALL.md`(김명준) 순서대로 도구 설치, `haedam-pf` 계정과 공개키 등록
- [x] **5단계(스파이크 판정):** 다음을 확인한다. 하나라도 실패하면 설계 4-3의 대체안으로 바꾸고 저널에 원인을 적는다.
  - 임시 `nginx`를 10.250.0.2에 붙이고 `normal` 컨테이너에서 `curl -s -o /dev/null -w '%{http_code}' http://203.0.113.1/` → `200`
  - nginx 로그의 출발지가 `203.0.113.100`
  - `docker run --rm --network wan --ip 203.0.113.22 alpine ping -c1 203.0.113.1`을 보내면 pfSense `Status > System Logs > Firewall`에 차단 1건이 남음
- [x] **6단계:** `Diagnostics > Backup`으로 `config.xml`을 내보낸다. 비밀번호 해시·SSH 키·인증서 개인키를 자리표시로 바꾼 뒤 `python tools/secret_scan.py infra/pfsense`로 0건을 확인한다.
- [x] **7단계:** 커밋한다. `feat(pfsense): QEMU 컨테이너로 pfSense CE 2.7.2 구동, wan/lan 브리지`

### Task 2: 서버 (포털·MySQL·티켓 저장소)

**파일**
- 만들기: `services/portal/Dockerfile`, `services/portal/entrypoint.sh`, `services/portal/compose.yaml`
- 수정: `services/ticket-store/compose.yaml`(VPN 바인딩 → `lan` 고정 IP 10.250.0.3, 포트 8088은 호스트에 열지 않음)

**인터페이스**
- 만드는 것: `http://10.250.0.2:5000`(대응 API `/api/v1/response/ips`·`/accounts/lock`, 키 헤더 `X-Response-Key`), `http://10.250.0.3:8088`(키 `TICKET_STORE_KEY`)
- 포털 환경 값:

  ```
  DATABASE_URL=mysql+pymysql://haedam:${MYSQL_PASSWORD}@10.250.0.5/haedam?charset=utf8mb4
  GELF_ENABLED=1
  GELF_HOST=10.250.0.100
  GELF_TRANSPORT=tcp
  RESPONSE_API_KEY=${PORTAL_RESPONSE_KEY}
  RESPONSE_ALLOWED_CIDRS=10.250.0.103/32
  DASHBOARD_URL=http://127.0.0.1:8089
  ```

**방식**
- Dockerfile은 2단계다.
  - `node:22-alpine`에서 `npm ci && npm run build`
  - `python:3.12-slim`에서 백엔드 `pip install .`, 프론트 `dist`를 `FRONTEND_DIST=/app/dist`로 복사
- `entrypoint.sh` 순서:
  - `ip route add 203.0.113.0/24 via 10.250.0.1`
  - MySQL 대기 루프: `python -c` + PyMySQL 접속, 2초 간격·60초 제한
  - `flask --app haedam_portal db upgrade`
  - 첫 기동이면 `flask seed-demo`와 `create-admin`(값은 `.env`)
  - `waitress-serve --port 5000`

- [x] **1단계:** Dockerfile·entrypoint·compose를 쓴다.
- [x] **2단계:** `docker compose -f services/portal/compose.yaml up -d --build`를 실행한다. 이어서 `docker compose ... down -v && ... up -d`(빈 볼륨 재기동)를 하고 `docker logs portal`에 `Serving on`이 나오는지 본다(리뷰 중점 4).
- [x] **3단계:** `normal` 컨테이너에서 `curl -s http://203.0.113.1/api/v1/health`(pfSense 경유) → 200 JSON. 호스트에서 `http://127.0.0.1:8080` → 로그인 화면.
- [x] **4단계:** 포털 `instance/events.jsonl`의 마지막 줄 `src_ip`가 `203.0.113.100`인지 확인한다(NAT 보존).
- [x] **5단계:** 커밋한다. `feat(server): 포털·MySQL·티켓 저장소 컨테이너, pfSense 경유 복귀 경로`

### Task 3: Graylog와 탐지 설정 자동 반입

**파일**
- 만들기:
  - `infra/graylog/compose.yaml`(팀 compose 기반, 고정 IP, `name:`·VPN 주석 제거)
  - `infra/graylog/bootstrap.py`
  - `infra/graylog/content-pack.json`(반입 후 내보낸 것)
  - `tests/test_graylog_bootstrap.py`
- 사용: `infra/graylog/pipelines/pfsense-parse.txt`, `lab/s1s4/graylog/s1-login-bruteforce.json`, `lab/s8s10/graylog/{s8-scan-then-login,s10-three-layer,s8-s10-n8n-notification}.json`, `infra/graylog/notifications/s1-n8n-haedam-s1.json`

**인터페이스**
- 만드는 것: `python infra/graylog/bootstrap.py --url http://127.0.0.1:9000`(자격 증명은 환경 변수 `GRAYLOG_ADMIN_PASSWORD`). 이름 기준으로 이미 있으면 건너뛰므로 다시 실행해도 안전하다.
- 입력 3개:
  - GELF TCP 12201
  - Syslog UDP 1514(호스트 매핑 불필요, pfSense가 lan에서 직접 전송)
  - Raw TCP 5514
- 스트림 `haedam-portal`(`source=haedam-portal`), `pfsense`, 파이프라인 `pfsense-parse`
- 이벤트 정의 3개: 정의 JSON의 `REPLACE_haedam-portal_stream_id`·`REPLACE_pfsense_stream_id`를 실제 ID로 치환한다.
- 알림 URL:
  - `http://10.250.0.103:5678/webhook/haedam-s1`
  - `http://10.250.0.103:5678/webhook/haedam-s8-s10`
  - 둘 다 URL 허용 목록에 Exact로 등록한다.
- 함수:
  - `replace_stream_ids(defn: dict, ids: dict[str, str]) -> dict`
  - `notification_url(raw: dict, base: str) -> dict`

- [x] **1단계:** 실패하는 테스트를 쓴다.
  - `test_replace_stream_ids`: s10 정의 → `streams == [ids['haedam-portal'], ids['pfsense']]`, 결과 JSON에 `REPLACE_` 문자열이 없음
  - `test_notification_url_rewritten`: `host.docker.internal` 주소가 `http://10.250.0.103:5678/webhook/haedam-s8-s10`로 바뀜
- [x] **2단계:** `python -m pytest tests/test_graylog_bootstrap.py -v` → FAIL
- [x] **3단계:** `bootstrap.py`를 구현한다. `urllib.request`만 쓰고 헤더는 `X-Requested-By: bootstrap`이다. 이벤트 정의는 `POST /api/events/definitions?schedule=true`로 넣는다.
- [x] **4단계:** 같은 명령으로 PASS를 확인한다.
- [x] **5단계:** 실제 기동 후 bootstrap을 실행하고 다음을 확인한다.
  - `normal`에서 포털 요청 1건을 보내면 Search `source:haedam-portal`에 1건이 뜬다.
  - Task 1의 ping 1건이 `rule:"pfsense-block"`으로 정규화돼 보인다.
  - bootstrap을 두 번째 실행하면 "생성 0" 출력
- [ ] **6단계(생략, 11/09):** 알림 헤더에 n8n 웹훅 키가 들어가 내보내면 비밀값이 남고, bootstrap과 내용이 겹친다. `System > Content Packs > Create`로 입력·스트림·파이프라인·이벤트·알림을 묶어 `content-pack.json`으로 저장한다. 수동 업로드 경로로도 쓸 수 있다.
- [x] **7단계:** 커밋한다. `feat(graylog): 단일 PC 구성, 탐지 설정 bootstrap·콘텐츠 팩`

### Task 4: n8n 워크플로·자격 증명 반입

**파일**
- 만들기: `infra/n8n/compose.yaml`(외부 볼륨 → 일반 볼륨, 고정 IP), `infra/n8n/import.ps1`, `infra/n8n/make_credentials.py`, `tests/test_n8n_credentials.py`
- 수정: `infra/n8n/workflows/*.json`. `10.250.0.3:55000` → `10.250.0.4:55000`(Wazuh)만 바꾼다. 나머지 주소는 그대로다.
- 반입하지 않음: `tools/gen_n8n_*.py` 생성기 체인. 생성된 JSON을 원본으로 삼고, 그 이유를 저널에 적는다.

**인터페이스**
- 만드는 것: `python infra/n8n/make_credentials.py > (컨테이너 임시 경로)`는 `.env`를 읽어 n8n `import:credentials` 형식 JSON 배열을 출력한다. 파일로 남기지 않고 파이프로 넘긴다.
- 자격 증명 이름은 워크플로가 참조하는 그대로 쓴다.
  - `haedam-s1 caller`, `haedam-s4 caller`, `haedam-s8-s10 caller`, `haedam-s12 caller`, `haedam-s7 caller`, `haedam-s7-live caller`(httpHeaderAuth, 값 `N8N_WEBHOOK_KEY`)
  - `haedam-pf-response D`(sshPrivateKey, 값 `PF_SSH_PRIVATE_KEY_FILE` 파일 내용)
  - 포털·티켓 저장소 키 자격 증명: 이름은 1단계에서 `haedam-12`·`haedam-10`의 httpRequest 노드를 읽어 확정한다.
- 함수: `build_credentials(env: dict[str, str]) -> list[dict]`
- `import.ps1`: `docker exec n8n n8n import:workflow --separate --input=/workflows` → 자격 증명 반입 → `n8n update:workflow --all --active=false` → S1·S8/S10 주 워크플로와 하위 워크플로 활성화
- 실제 조치 스위치(`dry_run:false`, `store_real:true`)는 팀 문서 `docs/S8S10-COMPLETION.md`·S1 카드의 방식을 따른다. 스위치를 켜는 방법은 README에 적는다.

- [ ] **1단계:** `haedam-10/11/12/14` JSON에서 credentials 참조 이름을 모두 뽑아 위 목록을 확정하고 테스트에 넣는다.
- [ ] **2단계:** 실패하는 테스트를 쓴다.
  - `test_all_referenced_credentials_built`: 모든 워크플로의 참조 이름 집합 ⊆ `build_credentials(...)`의 이름 집합
  - `test_missing_env_raises`: `PORTAL_RESPONSE_KEY`가 없으면 `KeyError` 메시지에 변수 이름이 들어감
- [ ] **3단계:** `python -m pytest tests/test_n8n_credentials.py -v` → FAIL
- [ ] **4단계:** `make_credentials.py`를 구현한다.
- [ ] **5단계:** 같은 명령으로 PASS를 확인한다.
- [ ] **6단계:** 실제 반입 후 다음을 확인한다.
  - n8n 화면에서 각 노드의 자격 증명 연결을 확인한다. 반입 뒤 연결이 지워지는 문제(팀 f5a4b6a)가 생기면 재연결 절차를 README에 적는다.
  - `haedam-14`를 `status`로 수동 실행 → pfSense 응답 OK
  - `haedam-01` → 티켓 저장소 check 200
- [ ] **7단계:** 커밋한다. `feat(n8n): 단일 PC 반입 스크립트, .env 기반 자격 증명 생성`

### Task 5: Wazuh single-node

**파일**
- 만들기: `infra/wazuh/compose.yaml`(wazuh-docker v4.9.2 single-node 기반, 고정 IP, `mem_limit`: indexer 1.5g(heap 1g)·manager 1g·dashboard 768m), `infra/wazuh/generate-certs.yml`, `infra/wazuh/config/`(원본 그대로, 출처 표기)

**인터페이스**
- 만드는 것: `wazuh.manager` 10.250.0.4(1514·1515·55000), 대시보드 `https://127.0.0.1:5601`
- MVP에서는 구동과 접속만 확인한다. Graylog 연동은 S7 단계에서 한다.

- [x] **1단계:** compose·인증서 생성 설정을 쓴다. 인증서는 `docker compose -f infra/wazuh/generate-certs.yml run --rm generator`로 만들고, `infra/wazuh/config/wazuh_indexer_ssl_certs/`는 `.gitignore`에 넣는다.
- [x] **2단계:** `up -d` 뒤 3분 안에 `curl -k -u wazuh-wui:$WAZUH_API_PASSWORD https://<manager>:55000/security/user/authenticate`(n8n 컨테이너 안에서 실행)이 토큰을 반환하고, 대시보드 로그인이 되는지 확인한다.
- [x] **3단계:** 커밋한다. `feat(wazuh): single-node 4.9.2 단일 PC 구성`

### Task 6: 최상위 compose·.env.example·동시 기동 검증

**파일**
- 만들기: `compose.yaml`(`networks: wan 203.0.113.0/24 gw .254, lan 10.250.0.0/24 gw .254`, 각 구성 `include`, 프로필 `soc`·`wazuh`·`pfsense`·`lab`), `.env.example`(모든 변수, 생성 명령 주석 포함), `tools/check_stack.py`
- 만들기: `lab/Dockerfile`(`python:3.12-slim` + `iputils-ping` + `curl`), 서비스 `attacker`(203.0.113.11, 별칭 IP `.21`·`.22`는 entrypoint의 `ip addr add`), `normal`(203.0.113.100)

**인터페이스**
- 만드는 것: `python tools/check_stack.py`는 구성별로 다음을 점검하고 `OK/FAIL 이름 상세`를 출력한다. 하나라도 FAIL이면 종료 1이다.
  - 포털 health 200
  - Graylog `/api/system/lbstatus`
  - n8n `/healthz`
  - Wazuh API 토큰
  - pfSense(`normal`에서 203.0.113.1:80 → 200)
  - 티켓 저장소 check

- [ ] **1단계:** compose와 `.env.example`을 쓴다. `.env`의 필수 값을 하나 지운 상태에서 `docker compose config`를 실행해, 변수 이름이 든 오류로 멈추는지 확인한다(리뷰 중점 5).
- [ ] **2단계:** `docker compose --profile "*" up -d` 뒤 `python tools/check_stack.py` → 6개 모두 OK. 10분 뒤 `docker stats --no-stream`을 저널에 붙인다(OOM·재시작 0 확인).
- [ ] **3단계:** 메모리가 부족하면 `mem_limit`를 조정하고 근거를 저널에 적는다. 조정 대상은 OpenSearch heap 1g → 768m, Wazuh indexer 1g → 768m 순서로 한다.
- [ ] **4단계:** 커밋한다. `feat: 최상위 compose, 5개 구성 동시 기동 점검 도구`

### Task 7: 티켓 실행기와 S10 → S8 → S1 실측

**파일**
- 만들기: `lab/run_ticket.py`, `tests/test_run_ticket.py`, `docs/tickets/{S10,S8,S1}/README.md`, 캡처 `docs/tickets/*/img/`
- 재사용: `tools/s8s10_input.py`(김명준, S8·S10 입력), `lab/s1s4/a_s1_step.py`(본인, S1 입력). 둘 다 `attacker` 컨테이너 안에서 실행한다.

**인터페이스**
- 만드는 것: `python lab/run_ticket.py {S1|S8|S10} [--restore]`(호스트 실행)
- 단계:
  1. 사전 점검: 잔여 차단 0, 직전 실행 창 확인
  2. 입력 시각 기록
  3. `docker exec attacker ...`로 입력
  4. 티켓 저장소에서 해당 출발지 티켓 대기(최대 180초)
  5. 효과 확인: 공격자 403·S10은 pfSense 경유 연결 실패, `normal` 200
  6. `--restore`일 때만 해제(S10은 PF 먼저) → 공격자 200 → 티켓 closed
  7. 결과를 `docs/tickets/<ID>/runs.jsonl`에 한 줄 추가
- 함수:
  - `window_blocked(last_run: datetime | None, now: datetime, minutes: int) -> int | None`: 남은 초, 창 밖이면 `None`
  - `precheck(blocked_ips: list[str], pf_table: list[str], src: str) -> list[str]`: 문제 목록
  - `mttd(condition_met_at: datetime, detected_at: datetime) -> float`
- 창 길이: S1 30분, S8·S10 15분
- 출발지: S1 `203.0.113.11`, S8 `.21`, S10 `.22`

- [ ] **1단계:** 실패하는 테스트를 쓴다.
  - `test_window_blocks_rerun_within_15min`: `window_blocked(now-10분, now, 15) == 300`
  - `test_window_allows_after`: `window_blocked(now-16분, now, 15) is None`
  - `test_precheck_flags_leftover`: `precheck(['203.0.113.22'], [], '203.0.113.22') == ['portal_block_left:203.0.113.22']`
  - `test_precheck_flags_pf_leftover`: `precheck([], ['203.0.113.22'], '203.0.113.22') == ['pf_block_left:203.0.113.22']`
  - `test_mttd_seconds`: 시각 차 49.281초 → `49.281`
- [ ] **2단계:** `python -m pytest tests/test_run_ticket.py -v` → FAIL
- [ ] **3단계:** `run_ticket.py`를 구현한다. HTTP는 `urllib.request`, 컨테이너 실행은 `subprocess.run(['docker','exec',...])`를 쓴다.
- [ ] **4단계:** 같은 명령으로 PASS를 확인한다.
- [ ] **5단계(S10 실측):** `python lab/run_ticket.py S10 --restore`를 실행하고 다음을 확인한다.
  - 포털 403과 pfSense 차단 중 연결 실패, `normal` 200
  - PF 해제 후 포털 단독 403, 포털 해제 후 200, 티켓 closed
  - MTTD와 탐지→차단 시간을 `docs/tickets/S10/README.md` 표에 적는다(명령·기대 결과·실측·캡처, 비밀값 가림).
- [ ] **6단계(S8 실측):** `python lab/run_ticket.py S8 --restore`를 실행한다. PF 호출 0, 포털 403 → 해제 → 200을 확인하고 기록한다.
- [ ] **7단계(S1 실측):** `python lab/run_ticket.py S1 --restore`를 실행한다. 같은 계정 실패 9회 → 탐지 → `.11` 403, `normal`의 같은 계정 로그인 200 → 해제 → 200을 확인하고 기록한다.
- [ ] **8단계:** 같은 티켓을 출발지 창을 피해 2회씩 더 돌려 3회 값을 표에 적는다. 실패 회차도 실패로 남긴다.
- [ ] **9단계:** 커밋한다. `feat(lab): 티켓 실행기, S10·S8·S1 단일 PC 실측 기록`

### Task 8: README와 새 설치 리허설

**파일**
- 만들기: `README.md`, `docs/journal/*.md` 정리

**README 순서**
1. **맨 위:** 팀 원본 저장소 3개 주소, 팀원 4명과 자리, 본인 역할(A · 포털 서비스·대응 API, S1·S4)과 기여 범위(`CREDITS.md` 요약), 이 저장소가 팀 결과물을 PC 한 대로 재구성했다는 설명
2. **구성도:** mermaid, 주소 표
3. **사전 준비:** Docker Desktop, `.wslconfig` 두 줄과 `wsl --shutdown`, pfSense ISO 받기
4. **설치:**
   - `.env` 만들기(생성 명령 포함)
   - Wazuh 인증서
   - `docker compose --profile "*" up -d`
   - pfSense 설치(`infra/pfsense/INSTALL.md`)와 `config.xml` 복원
   - Graylog bootstrap 또는 콘텐츠 팩 업로드
   - n8n `import.ps1`
   - `tools/check_stack.py`
5. **구성별 표:** 실행 명령·접속 주소·포트·기본 설정 방법
6. **티켓 실측:** `lab/run_ticket.py`, 티켓 문서 링크
7. **문제 해결:** 저널에서 뽑은 증상 → 원인 → 조치

- [ ] **1단계:** README를 쓴다.
- [ ] **2단계(리허설):** `docker compose --profile "*" down -v`로 볼륨을 지운다. pfSense 디스크도 지우고 `.env`를 새로 만든다. 그다음 **README만 보고** 처음부터 설치한다. 막힌 지점마다 README를 고치고 저널에 적는다. 끝나면 `check_stack.py` 전부 OK, S10 1회 완주를 확인한다.
- [ ] **3단계:** `python tools/secret_scan.py` → 0건, `git status`에 `.env`가 없는지 확인한다.
- [ ] **4단계:** 커밋한다. `docs: README 설치 순서·구성별 접속·티켓 실측 안내`
- [ ] **5단계:** 사용자 확인을 받은 뒤 `gh repo edit --visibility public --accept-visibility-change-consequences`로 공개 전환한다. 외부 게시이므로 확인 없이 진행하지 않는다.

### Task 9: 정량평가 요약

**파일**
- 만들기: `tools/summarize_runs.py`, `tests/test_summarize_runs.py`, `docs/정량평가.md`

**인터페이스**
- 사용: Task 7의 `docs/tickets/*/runs.jsonl`. 한 줄 필드는 `ticket, run_id, src, condition_met_at, detected_at, responded_at, restored_at, auto_ok, restore_ok, normal_ok`이다.
- 만드는 것: `summarize(rows: list[dict]) -> dict` → 티켓별·전체 `runs`, `auto_rate`, `restore_rate`, `normal_fail_runs`, `mttd_median`, `detect_to_respond_median`, `mttr_median`(초)
- 지표 정의(앞의 네 개는 팀 정량평가 리포트와 같다):
  - **MTTD:** 탐지 시각 − 조건 충족 시각
  - **탐지→대응:** 조치 시각 − 탐지 시각
  - **자동 대응률:** 사람 개입 없이 조치와 효과가 확인된 회차 / 전체
  - **원복률:** 해제·복원 후 정상 동작이 확인된 회차 / 원복 시도
  - **정상 사용자 영향:** 대응 중 정상 요청이 실패한 회차 수
  - **오탐:** 기준선 입력 회차(`baseline: true` 행)에서 발동한 수
- `python tools/summarize_runs.py`는 `docs/정량평가.md`의 표를 다시 쓴다.

- [ ] **1단계:** 실패하는 테스트를 쓴다.
  - `test_rates`: 3회 중 auto_ok 2 → `auto_rate == 2/3`
  - `test_median_ignores_failed`: detected_at이 없는 회차는 MTTD 중앙값에서 빠지고 `runs`에는 포함
- [ ] **2단계:** `python -m pytest tests/test_summarize_runs.py -v` → FAIL
- [ ] **3단계:** `statistics.median`으로 구현한다.
- [ ] **4단계:** 같은 명령으로 PASS를 확인한다.
- [ ] **5단계:** `docs/정량평가.md`를 작성한다. 이 PC 실측 표와 팀 리포트 수치(자동 대응 8/9·원복 8/8·MTTD 중앙값 51.4초, "팀 공통·4대 분산")를 나란히 두고 차이의 원인(UDP→TCP, 단일 PC 지연 등)을 적는다.
- [ ] **6단계:** 커밋한다. `feat: 실측 결과 정량평가 요약`
