# infra/n8n · D PC n8n

수업용 n8n 컨테이너(`n8nio/n8n:latest`, `0.0.0.0:5678`)를 같은 이름·같은 볼륨으로 대체하는 compose다. 10/22 D PC에서 적용했다.

| 항목 | 값 |
| --- | --- |
| 이미지 | `n8nio/n8n:2.39.5` (고정. 올릴 때는 볼륨 백업 후 이 파일을 PR로 변경) |
| 게시 주소 | `${BIND_IP:-127.0.0.1}:5678`. 팀 VPN(`team-d`) 연결 뒤 그 주소로만 바꾼다 |
| 볼륨 | 외부 볼륨 `n8n_data`(수업 때 만든 것). 워크플로·자격 증명·암호화 키가 들어 있어 **삭제하지 않는다** |
| 수업 compose | `C:\gov\Git-Connection\n8n\docker-compose.yml`은 건드리지 않았다. 다시 쓰면 5678이 0.0.0.0으로 열린다 |

```powershell
# 적용·변경 (BIND_IP 기본 127.0.0.1)
docker compose -f infra/n8n/docker-compose.yml up -d
# 팀 VPN 주소로 바꿀 때만
$env:BIND_IP = "<team-d 주소>"; docker compose -f infra/n8n/docker-compose.yml up -d
```

## 10/22 적용 결과 (D PC에서 실제 확인)

- 적용 전: 컨테이너 `n8n`, 5678이 `0.0.0.0`과 `[::]`에 게시. 워크플로 11개(활성 6개: 4·5·6·7·8번 봇, 9-S11), 수업 용도.
- 볼륨 백업: `n8n_data` 전체를 tar로 PC 안의 저장소 밖 폴더에 저장(자격 증명·암호화 키가 있어 저장소에 넣지 않음).
- 적용 후: 5678이 `127.0.0.1`에만 게시. 이 PC에서 `/healthz` `{"status":"ok"}`, 유선 주소 `192.168.3.6:5678`은 연결 거부. 워크플로 11개·활성 6개 그대로.
- **미확인:** 활성 6개가 수업 때의 Graylog·pfSense를 가리키는지(재생성 전후로 동작은 비교하지 않았다). 해담 용도 워크플로는 아직 없다. `WEBHOOK_URL`은 `http://127.0.0.1:5678/`이라 다른 PC가 부를 Webhook 주소는 팀 VPN 연결 뒤 정한다.

## pfSense·Wazuh 실제 호출 노드 (10/27, 전부 dry_run 기본, 아직 한 번도 실행하지 않음)
`haedam-14`·`haedam-15`의 자리표시를 실제 호출로 바꿨다. 생성은 `tools/gen_n8n_actions.py`(순서는 위 생성 명령). `dry_run !== false`이면 외부로 나가지 않고 보낼 내용만 돌려준다. 로컬에서는 코드 노드를 Node로 직접 돌려 입력 검사·보호 목록·출력 해석 33건을 확인했고, **n8n에 올려 돌려 보거나 실제 장비·API를 부른 적은 없다.**

**haedam-14 (pfSense, 근거: B의 `lab/pfsense/README.md`, PR #64)**
- n8n SSH 노드가 `haedam-pf-response ACTION TARGET REQUEST_ID OWNER_ID`를 보낸다. 도구는 `203.0.113.22` 하나만 받는다(다른 주소는 도구가 `rejected`). n8n은 그 앞에서 보호 목록도 먼저 거른다.
- `REQUEST_ID`는 `{ticket_id}-pf-{ip}-{action}`(재전송 때 같은 값), `OWNER_ID`는 티켓 ID. 해제(`unblock`)는 요청 ID가 달라진다. `status`도 받는다.
- 출력 JSON: `applied`·`already_applied`→같은 이름, `released`→`released`, `status`→`listed`, `ok:false`→`rejected` 또는 `failed`. 출력 파싱 실패·비정상 종료·`changed:null`(불확실)은 **성공으로 두지 않고 `failed`**, 자동 재시도 없음(도구 문서).
- 필요한 것: n8n 자격 증명 `SSH Private Key`(D가 새로 만든 **전용 공개키**의 개인키. 값은 저장소·채팅에 넣지 않음), pfSense 쪽 forced command(`from="10.250.0.100"`)와 D→`10.250.0.1:22` 허용(B 작업). 둘 다 아직 없다.
- 티켓 기록 이름: 지금은 pfSense 줄을 `action=fw_block`으로 기록한다(C 저장소가 `via`를 안 봐서). B는 `block`+`via=pfsense`를 쓰자고 했으므로 C의 PR #62 배포 뒤 `fw_block`→`block`으로 한꺼번에 바꿔야 한다(check·applied·effect·released 전부).
- 효과(`effect`)는 도구가 `null`로 둔다. `.22` 접근 실패·정상 출발지 200 확인은 이 워크플로가 하지 않는다.

**haedam-15 (Wazuh active response, 근거: C의 `lab/s7/restore/README.md`)**
- `POST /security/user/authenticate?raw=true`로 토큰을 받고 `PUT /active-response?agents_list=010`에 `{command:"!s7-restore-ar", arguments:[file_key, run_id]}`를 보낸다(10/28 C의 API 직접 호출과 같은 형식). `file_key`는 웹 루트 기준 경로다. 토큰을 만들고 쓰는 호출은 하위 워크플로 `haedam-17`(실행 기록 저장 안 함)에만 있고, `haedam-15`는 입력 검사·dry_run·응답 해석을 맡으며 **실행 기록을 저장한다**(노드별 증적). 11/03 변경 전에는 `haedam-15` 전체가 실행 기록을 저장하지 않았다.
- `file_key`는 웹 루트(`/home/haedam/haedam-portal-frontend/dist`) 아래 상대 경로로 보고, `..`·공백·루트 밖 경로는 거부한다.
- Wazuh API 응답은 "에이전트에 보냈다"까지만 알려 준다. 그래서 성공하면 `applied`이되 `applied_verified:null`로 두고, 복구가 실제로 됐는지(`sha256_after`가 기준 해시와 같은지)는 따로 확인해야 한다 — 아직 없다.
- 필요한 것: n8n 자격 증명 `Basic Auth`(이제 `haedam-17`의 "Wazuh 로그인" 노드에 연결)(계정 `n8n-s7`, C가 만든 것). 값은 읽지 않았다. TLS는 자체 서명이라 인증서 검증을 끈 상태(`allowUnauthorizedCerts`)다 — 팀 VPN 안이라는 전제이며 C와 정리가 필요하다.
- **확인됨(C, 10/28 API 직접 호출)**: `n8n-s7`의 active response 권한, manager 명령 등록 없이 `!` 접두로 agent의 `s7-restore-ar` 실행, 에이전트 ID `010`. **미시험**: n8n에서 이 워크플로로 호출하는 경로, D→C `55000` 연결, n8n 자격 증명 연결.

**haedam-17 (Wazuh 토큰·전송, 11/03 분리)**
- `haedam-15`가 `ctx`·`file_key`·`run_id` 등을 넘기면 `haedam-17`이 로그인 → active response 전송 → **허용된 형태의 요약만**(`status`, `affected`, `failed_count`, 3자리 agent ID `failed_ids`, 고정 단어 `reason`) 돌려준다. 응답 원문·오류 메시지는 토큰이 섞일 수 있어 넘기지 않는다.
- 입구 검증: 실행 의도(`execute: true`, haedam-15가 dry_run 아님·입력 검사 통과 뒤에만 만듦), 대상 API·agent·명령(고정값과 같아야 함), `file_key`·`run_id` 형식을 확인한다. 어긋나면 로그인(자격 증명 사용)과 AR 전에 `rejected`로 끝낸다. 회차별 승인 절차를 대체하지는 않는다.
- 설정 `saveDataSuccessExecution/ErrorExecution: "none"`, `saveExecutionProgress: false`, `saveManualExecutions: false`. 토큰이 n8n DB의 실행 기록에 남지 않는다. `haedam-15`·`haedam-33`·`haedam-34`와 부모 실행은 기록이 남아 실행 807처럼 하위 실행이 `running`으로만 보이던 문제를 줄인다(`haedam-17` 실행 자체는 여전히 저장되지 않는다).
- 반입: `haedam-17`을 `haedam-15`보다 먼저(또는 같이) 반입한다. 반입은 비활성이며, Basic Auth 자격 증명(`wazuh-api`)은 `haedam-17`의 "Wazuh 로그인" 노드에 다시 연결하고 `haedam-15`의 "Wazuh 호출 (haedam-17)" 노드가 `haedamWazuhToken01`을 가리키는지 확인한다. 하위 워크플로는 게시하지 않는다.
- 이 변경으로 실제 조치(dry_run 기본)·`run_id`·범위 제한 동작은 바뀌지 않는다. n8n에 올려 돌려 본 것은 아직 없다(로컬 테스트만).

## S7 공용 경로 티켓 실기록·호출자 인증 (haedam-33, 11/02)

- `haedam-33`의 CFG는 `dry_run: true, store_real: true`입니다. Wazuh 조치는 보내지 않고, 티켓만 C 저장소(`10.250.0.3:8088`)에 기록합니다. dry_run 조치는 `stage detected`, `action: null`로만 남아 조치 행은 생기지 않습니다. 같은 열린 `group_key`는 기존 티켓을 재사용하므로, 대조는 건수가 아니라 생성 응답·티켓 ID·`event_ids`로 합니다.
- 웹훅 `haedam-s7`에는 헤더 인증이 걸려 있습니다(자격 증명 이름 `haedam-s7 caller`). 반입 직후에는 자격 증명이 연결돼 있지 않아 게시되지 않습니다(fail-closed). 미인증·오인증 요청은 워크플로 첫 노드 전에 n8n이 거절합니다.
- 반입 시 순서: n8n에 Header Auth 자격 증명 `haedam-s7 caller`를 만들고(헤더 이름·값은 D가 정함, 값은 채팅·증적·저장소에 남기지 않음) 웹훅 노드에 연결 → 저장·게시 → Graylog S7 알림의 `headers`에 같은 헤더를 넣음 → 헤더 없는 요청·틀린 헤더는 거절, 맞는 헤더만 통과하는지 확인.
- **11/03 변경: 다른 케이스 메인도 케이스별 회차에서 티켓을 실기록할 수 있습니다.** `haedam-20`(S12)·`haedam-30`(S1)·`haedam-31`(S4)·`haedam-32`(S8·S10)의 CFG 기본은 `dry_run: true, store_real: false`(관찰)입니다. 요청 본문에 불리언 `store_real: true`를 넣은 회차만 티켓·결과를 C 저장소에 기록하고(문자열·숫자는 무시), 일괄 활성화하지 않습니다. 실제 조치는 하지 않습니다(S1의 `dry_run:false` 본문 스위치는 기존 그대로, D 명시 승인 전에는 쓰지 않음).
- 웹훅마다 헤더 인증(fail-closed)을 겁니다. 자격 증명 이름은 `haedam-s12 caller`·`haedam-s1 caller`·`haedam-s4 caller`·`haedam-s8-s10 caller`이며 값은 채팅·저장소에 두지 않습니다. 반입 직후에는 연결돼 있지 않아 게시되지 않습니다.
- 반입 순서(케이스마다): n8n에서 Header Auth 자격 증명을 만들고 웹훅 노드에 연결 → 저장·게시 → 그 케이스 Graylog 알림의 `headers`에 같은 헤더를 넣음(파일에서 직접, 값은 기록하지 않음) → 헤더 없음·틀린 헤더는 거절, 맞는 헤더만 통과하는지 확인. 지금 Graylog에 남아 있는 `n8n haedam-s1`·`haedam-s12` 알림은 이 헤더가 없으므로, 헤더를 넣기 전에는 호출이 거절됩니다(정의가 비활성이라 당장 호출은 없음).
- 실제 조치(`dry_run:false`)는 이 변경에 포함되지 않습니다. 회차마다 D의 별도 승인이 필요합니다.
- S8·S10(`haedam-32`)에도 불리언 `dry_run:false` 본문 스위치가 있습니다(기본 true, 문자열·숫자는 무시). S4(`haedam-31`)도 같은 불리언 `dry_run:false` 스위치로 실제 계정 잠금을 켭니다. 단, 사용자명이 시험 계정(`zz_` 접두어)일 때만이며 그 밖의 계정은 `protected_account`로 조치 없이 끝납니다. 잠금 해제(unlock) 경로는 아직 없습니다(`haedam-13`은 lock만). S1·S4·S8/S10은 티켓 detected 저장이 실패하면 `저장 실패 응답`(`ticket_store_failed_no_action`)으로 끝나 조치 노드에 가지 않습니다. S7(`haedam-33`)은 그대로입니다. S8/S10이 동시에 들어오는 경쟁은 이 변경으로 막지 않습니다(중복 확인과 저장이 원자적이지 않음).

## S7 실제 AR 시험 전용 복사본 (haedam-34, 11/02)

공용 `haedam-33`(웹훅 `haedam-s7`)은 `dry_run: true`(조치 없음)가 코드에 고정된 채로 둡니다(티켓은 `store_real: true`로 C 저장소에 기록). 실제 Wazuh AR 격리 시험은 `haedam-34`(웹훅 `haedam-s7-live`)로만 합니다.

- 만들기: `python tools/make_s7_live_copy.py` (`--check`는 저장소 파일과 같은지만 확인). `haedam-33` JSON을 변환하며 네트워크·대상 실행은 없습니다.
- 다른 점: 워크플로 id·이름·웹훅 경로 분리, 입력 검증 노드의 `CFG`를 `dry_run:false, store_real:true`로 고정, 범위 제한(자산 `haedam-portal`, 파일 `assets/zz_s7_1102_ar01.txt`, `change_type: added`=quarantine만, 그 밖은 `out_of_scope`로 대응 없음). payload로 모드·승인을 바꿀 수 없습니다. 중복 확인·티켓 기록 ACK·현재 티켓 재조회·결과 기록은 `haedam-33`과 같습니다.
- 회차 승인 기본 OFF: 저장소 파일은 `APPROVED_RUN_ID`가 비어 있어 모든 입력을 `approval_off`로 끝냅니다(기록·AR 노드 전이라 호출 0건). 승인 회차 반입본은 `python tools/make_s7_live_copy.py --approve-run-id S7-20261102-AR01 --out <저장소 밖 경로>`로만 만들고, 저장소 안에는 쓸 수 없습니다. 승인 run_id는 `S7-20261102-AR01`만 받습니다.
- run_id 전달: 승인 run_id를 `ctx.run_id`로 실어 haedam-15 입력까지 보내고, haedam-15는 `S7-YYYYMMDD-XXXX` 형식이면 Wazuh AR 인자 `[file_key, run_id]`에 그대로 씁니다(형식이 다르면 기존대로 event_id 기반).
- 호출자 인증: 웹훅에 헤더 인증(자격 증명 이름 `haedam-s7-live caller`)을 겁니다. 반입 직후에는 자격 증명이 연결돼 있지 않아 게시할 수 없습니다(fail-closed). 승인 회차에 D가 헤더 자격 증명을 만들어 연결하고, 같은 헤더를 Graylog 알림 `headers`에 넣습니다. 미인증·오인증 요청은 워크플로 실행 전에 거절됩니다.
- 운영: 항상 **비게시**로 반입합니다(import는 어차피 비활성). 승인된 회차 직전에만 게시하고, 끝나면 바로 비게시로 돌린 뒤 웹훅이 닫혔는지 읽어 확인합니다. 게시만으로 실행되지는 않으며 실제 호출은 호출별로 D가 사용자 승인을 받은 뒤에 합니다.
- dry-run 시험(`S7-20261102-01`, `assets/zz_s7_1102_01.txt`)은 공용 `haedam-33`으로 하고, 이 복사본의 범위에는 들어가지 않습니다.
- 원복: 비게시 + 임시 알림·허용 목록 제거 + 격리 파일은 A가 기준본으로 정리. 시험 뒤 복사본을 비활성으로 두거나 삭제합니다.

## 반입 뒤 자격 증명 재연결 (10/30·11/02 확인)

- 이 저장소의 워크플로 JSON에는 자격 증명 참조(`credentials`)가 없다. `n8n import:workflow`로 반입하면 **기존에 노드에 연결돼 있던 자격 증명 연결이 지워진다**. n8n 안의 자격 증명 자체(`ticket-store (C)`, `wazuh-api (n8n-s7)`, `haedam-portal-response`, `Discord Webhook account`)는 그대로 남는다.
- 10/30 #114 반입으로 haedam-10의 HTTP 노드 2개에서 `ticket-store (C)` 연결이 빠졌다. `store_real:false`로만 돌릴 때는 드러나지 않다가, 11/02에 D→C 인증 조회(haedam-01)가 `Credentials not found`로 실패해서 알게 됐다. 반입 전 백업에는 연결이 있었다.
- 반입 직후 해야 할 일:
  1. 반입 전에 대상 워크플로를 `n8n export:workflow --id=<ID> --output=<파일>`로 백업한다. 백업에 `credentials`가 있는지 본다.
  2. 반입·게시 뒤 n8n 화면에서 자격 증명이 필요한 노드(HTTP Request, Discord)를 열어 자격 증명을 다시 고르고 **저장한 뒤 게시**한다. 저장만 하고 게시하지 않으면 실제로 도는 게시본에는 반영되지 않는다.
  3. 다시 내보내서 해당 노드에 `credentials`가 있는지, 저장 버전과 게시 버전이 같은지 확인한다(`versionId`와 `activeVersionId`).
  4. 읽기 전용 확인(예: haedam-01 티켓 저장소 연결 확인)을 한 번 돌려 `ok:true`를 확인한다. 값이 필요한 연결은 이 확인으로만 점검하고, 자격 증명 값은 열어 보거나 기록하지 않는다.
- 연결이 필요한 워크플로: haedam-10(`ticket-store (C)`), haedam-12·13(`haedam-portal-response`), haedam-11(`Discord Webhook account`), haedam-15·17(`wazuh-api (n8n-s7)`), haedam-14(`haedam-pf-response D`, 11/03 연결), 케이스 메인의 웹훅 노드(`haedam-s1/s4/s7/s8-s10/s12 caller`).
- **웹훅은 CLI 반입·게시만으로 서버에 등록되지 않는다(11/03 S8 LIVE01 404 사례).** `import:workflow`는 워크플로를 비활성으로 만들고 웹훅 행을 지우며, `publish:workflow`는 실행 중인 서버에 웹훅을 등록하지 않는다. 반입한 웹훅 워크플로는 n8n 화면에서 다시 게시한 뒤 `webhook_entity`에 해당 경로 행이 있는지, **키 없는 POST가 403**인지(404면 미등록), 틀린 키가 403인지, 올바른 키에 빈 본문이 `no_action`으로 끝나는지 확인한다. 케이스를 켜기 전에 이 확인을 마친다.
- Header Auth 자격 증명은 **헤더 Name이 `X-Haedam-Key`**이고 Value가 키다. Name에 자격 증명 이름을 넣으면 호출자가 보내는 헤더와 맞지 않아 올바른 키도 403이 된다(11/03 S12 반입에서 실제로 발생, 확인 뒤 수정). 키 값은 채팅·증적·저장소에 남기지 않는다.
- haedam-14의 SSH 노드는 작업 디렉터리(cwd)를 비운다(표현식 `={{ '' }}`). 값이 있으면 node-ssh가 `cd '<cwd>' ;`를 앞에 붙여 PF의 forced command가 `invalid_ssh_command`로 거부한다(11/03).
- 화면에서 노드를 열어 고르기만 해도 n8n이 초안을 **자동 저장**한다. 시험 중 노드를 고치거나 데이터를 고정(pin)하면 그대로 남으므로, 저장하지 않을 변경은 만들지 않는다. 게시본은 영향을 받지 않지만 초안에는 남는다.
