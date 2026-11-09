# S10 pfSense 차단·해제 실행 경계 (B)

상태: **구현·격리 검증, pfSense 읽기 점검. 미배포·실차단/원복·D SSH/n8n 미연동.**
대상 장비는 실측 pfSense CE 2.7.2, WAN `em0 / 203.0.113.1`이다. 이 버전/매핑과 다르면 거부한다.

## 10/27 추가: 설치 패키지 준비

### 10/28 선행 조건 갱신

- C #62는 #67 최종 main `87997dd5bfae66cad955bb5211e5e85c8c9a99a6`에 포함됐고, C 재빌드 후 S1에서 실제 조회·기록·새 회차 분리·종료를 확인했다. 아래 10/26 당시의 미반영 조건을 현재 차단 사유로 재사용하지 않는다.
- S1 포털 단독 시험은 `.11/.13`에서 차단·정상 `.12` 로그인·수동 해제·원복까지 완료했다. 이것이 PF 대상 `.22` 시험이나 pfSense 설치·효과·원복 완료를 뜻하지 않는다. `.22` 현재 할당·반환 경로·앱/장비 차단 여부는 시험 전 별도 확인한다.
- 실제 PF 연결은 D 전용 공개키/호스트 키 검증·제한 명령과 SSH 최소 경로·워크플로 요청/응답 매핑·다른 티켓 소유권 대조가 남았다. `fw_block` 과거 기록은 통합 저장소가 `block`으로 읽기 호환하지만 새 실행 계약은 이 문서의 `block/unblock`을 사용한다.
- S7 AR 시험 준비와 겹치지 않는 별도 PF 작업 구간을 잡는다. 이 PR/설치 패키지로 실제 설치·방화벽 변경·SSH 키 등록을 실행하지 않는다.

[설치 인수 안내](INSTALL.md)와 `tools/build_pfsense_bundle.py`로 검토된 원본 해시의
도구·계약·설치기·설명서를 새 디렉터리에 묶는다. 기본 설치기와 `--verify`는
파일 검증만 수행한다. `--install`도 도구 한 파일만 게시하며 기존 다른 버전,
symlink, 동시 설치 파일을 덮어쓰지 않는다. SSH·규칙·journal은 별도 단계다.

10/27 15:12 KST 실제 pfSense Python3.11.6에서 도구와 설치기 문법을 메모리에서
컴파일했다. 버전·WAN 매핑·설치 부모 경로 전제, 기존 도구 파일 없음과 설정
바이트 불변을 읽기 확인했다. 파일 설치나 후보 실행은 하지 않았다.
격리 검사: 패키지15개 + 기존 도구36개, 해당 작업트리 전체158개 통과.
이 결과는 D SSH 인증·실제 설치·차단·state 제거·효과·원복 성공을 뜻하지 않는다.

## 범위와 확인 수준

- 승인한 S10 출발지 **`203.0.113.22` 하나만** 허용한다. 관리망·팀 VPN·정상 출발지·CIDR·IPv6·다른 주소를 받지 않는다.
- EasyRule의 **WAN** 차단 목록을 사용한다. 다른 인터페이스의 수동 차단을 해제하지 않는다.
- `easyrule block/unblock wan <IP>` 종료 코드만 믿지 않고 설정 alias·PF 테이블·실행 규칙/순서를 대조한다. 새 규칙이 없거나 표가 어긋나면 성공으로 답하지 않는다.
- 차단 적용 후 `pfctl -k 203.0.113.22`로 **해당 출발지**의 기존 state를 제거하고 남은 state를 확인한다. 전체 state flush·방화벽 해제·서비스 재시작은 사용하지 않는다.
- `applied_verified`는 관리 항목·실행 규칙 확인이다. 실제 HTTP 효과는 시험 담당이 확인한다. 도구는 `effect_verified:null`을 유지한다.
- 이 동작은 WAN에서 `.22`의 모든 목적지 트래픽을 차단한다. 포털만 차단하는 앱 API와 다른 집행 위치다.

## 호출 계약

```text
haedam-pf-response ACTION TARGET REQUEST_ID OWNER_ID
```

- ACTION: `status` / `block` / `unblock`.
- TARGET: `203.0.113.22` 고정.
- REQUEST_ID: 동작 요청마다 고유하고 재전송 때 동일한 ID. OWNER_ID: 한 차단 수명주기에서 동일한 소유 식별자(티켓 ID 등).
- ID는 영문/숫자로 시작하고 영문·숫자·`_.:-`만 1~96자 허용한다. 셸 문자열을 실행하지 않는다.
- stdout: JSON 1개, 성공 exit0·실패 exit1. [응답 스키마](../../contracts/pfsense-response.schema.json)와 [합성 예시](../../contracts/pfsense-examples/blocked.sample.json)를 사용한다.
- `status`는 방화벽을 바꾸지 않는다. 로컬 직렬화용 lock 디렉터리를 잠깐 만들 수 있다.

동일 요청은 저장된 결과를 재생하며 명령을 다시 실행하지 않는다. 이전 결과와 현재 상태/소유자가 달라졌으면 `replay_needs_reconciliation`로 거부한다. 같은 ID에 다른 요청을 넣으면 `request_id_conflict`다.

## 소유와 불확실한 결과

`/cf/conf/haedam-pf-response`는 root0700, journal은 root0600이다. 원자 저장·fsync로 **변경 전 의도/소유자**를 먼저 남긴다. 재시작해도 유지한다.

- 기존에 외부에서 차단한 `.22`는 채택하거나 해제하지 않는다.
- 다른 OWNER_ID는 활성 소유자의 차단을 채택/해제하지 못한다.
- timeout·일부 적용·state 제거 실패는 성공으로 만들지 않고 pending과 실패 영수증을 남긴다. `changed:null`은 변경 여부가 불확실함을 뜻한다.
- 불확실한 결과에 자동 재시도를 하지 않는다. 운영자가 실제 설정/테이블/규칙과 journal을 대조한다. 같은 소유자는 **새 요청 ID의 unblock**으로 자기 부분 적용을 보상할 수 있다. 오래된 실패 요청을 자동 재실행하지 않는다.
- 프로세스 중단 뒤 lock이 남으면 자동 만료/탈취하지 않는다. 운영자가 실행 중 프로세스와 pending을 대조한 뒤 **빈 lock 디렉터리만** 정리한다. journal을 지워 재시도를 허용하지 않는다.
- 이 소유자는 pfSense 도구 내부의 단일 소유다. C 티켓 저장소를 대신하지 않으며, D는 다른 티켓의 자원 점유 확인·직렬화 정책을 따로 적용해야 한다.

EasyRule은 마지막 IP를 해제해도 빈 alias/GUI 규칙을 남길 수 있다. 원복은 해당 IP의 관리 차단이 사라지고 정상 HTTP가 돌아오는 것으로 확인하며, 설정 revision 시각까지 원래 해시가 같아야 한다고 판정하지 않는다. 다른 alias 항목은 전후 같아야 한다.

## 배포·D 연결 전 준비 (아직 미실행)

1. D 측정/동결 종료와 시험 구간을 맞춘다. A는 포털 단독 차단·조회·재전송·해제 시험을 먼저 제안했고 B도 이 순서를 따른다.
2. C의 PR62 반영·컨테이너 재빌드와 재차단/자리 간 조회 미반영 조건을 확인한다. 실제 자동 해제는 다른 티켓의 차단이 없는지 확인한 뒤 진행한다.
3. B가 스크립트를 pfSense root 소유 `/usr/local/sbin/haedam-pf-response`로 검토 배포한다. shebang의 `/usr/local/bin/python3.11` 존재를 확인한다. 배포 전후 해시·관리 경로·설정/전송기 상태를 보존한다.
4. D가 **전용 SSH 공개키**를 준비한다. B 관리자 개인키는 전달하지 않는다. root 권한이 필요한 실행은 전용 키의 forced command로 제한하고 source는 D VPN `.100`으로 제한한다. 기존 SSH 전역 정책/기존 관리자 키를 바꾸지 않는다. 현재 이 키·계정·접속 경로는 미구축이다.
5. forced command 후보는 `command="/usr/local/sbin/haedam-pf-response",from="10.250.0.100",restrict`다. 설치 장비의 지원·소유 계정·권한·호스트 키 검증을 확인한 뒤 실제 키 줄에 적용한다. 원격 명령은 `SSH_ORIGINAL_COMMAND`를 엄격 파싱하며 임의 셸 명령을 실행하지 않는다.
6. D가 pfSense VPN 주소 `10.250.0.1:22`에 접속할 때 현재 수신/규칙부터 확인한다. 필요하다면 D→서버 TCP22 하나만 연다. 현재 LAN 관리자 SSH 성공을 D SSH 성공으로 확대하지 않는다.
7. 먼저 status만 조회한다. D n8n `haedam-14`의 실제 호출 후보는 PR #72로 준비됐지만 미반입·미실행 보고 상태다. workflow ID·자격 증명·호스트 키·B 제한 명령 계약을 실제 확인하기 전 자동 활성화하지 않는다.

## D 출력 매핑

도구 입력의 `block`·`unblock`은 실행 동작이다. 결과 기록에는 bot `"112"`, via `"pfsense"`, target `.22`, 도구의 result·applied_verified·requested_at·finished_at을 사용한다. `ctx`·`n8n_execution_id`·티켓 필드는 D가 자기 실행 문맥에서 붙인다.

- 다른 집행 위치 `portal`과 중복 처리하지 않는다. PR62의 `via` 기준에 맞춘다.
- D 기존 `fw_block` 우회 명칭과 새 계약의 `block`을 임의 혼용하지 않는다. D가 check/applied/effect/released 전체의 조치 이름을 맞춰야 한다.
- `ok:false`·비정상 exit·출력 파싱 실패는 대응 성공으로 record하지 않는다. 실패·보류와 원인 코드를 기록하고 자동 재실행하지 않는다.
- `effect`는 실제 `.22` 접근 실패·정상 출발지 성공 대조 후에만 기록한다. `released`는 실행 목록에서 해제됐다는 근거와 실제 재접근을 구분한다.
- 이 도구가 자체 생성한 시간은 실행 요청/완료 시각이다. Graylog의 조건 충족·탐지 시각을 대신하지 않는다.

## 실제 사전 시험 카드 (미실행)

1. A·D의 포털 단독 시험: `.22`가 앱403, 검증한 정상 출발지가200인지 확인하고 `.22` 앱 차단을 해제한다. **이때 pfSense 차단은 걸지 않는다.** `.12`는 제안일 뿐 실제 Kali 주소·A 반환 경로를 확인해야 한다.
2. B/D pfSense 단독 시험 시작: `.22` 관리 차단 없음과 journal 상태, A 앱 blocked_ips0, 정상 출발지·동결/시계를 확인한다. 새 단일 request/owner ID를 기록한다.
3. block → 설정/table/우선 규칙·대상 state 제거 확인 → `.22`의 새 HTTP 연결 실패·정상 출발지200 확인. 같은 요청 재전송은 별도 명령을 다시 실행하지 않아야 한다.
4. 같은 소유자의 새 unblock 요청 → alias/table에서 `.22` 없음 → `.22` HTTP200·정상 출발지200 → A 앱 차단 목록0 유지 확인.
5. 요청·조회·원복 시각/결과/로그를 기록한다. 명령 적용·HTTP 효과·티켓 기록·정상 업무·원복을 따로 판정한다. 실패 시 새 입력을 반복하지 않고 현재 상태와 pending을 먼저 확인한다.
6. 이 사전 시험을 마친 뒤 D가 S10 실제 자동 호출에 연결한다. 공격→Graylog→n8n→효과→티켓→원복 완주는 별도 실행이다.

## 공식 근거

- [Netgate EasyRule](https://docs.netgate.com/pfsense/en/latest/firewall/easyrule.html)
- [Netgate 방화벽 테이블](https://docs.netgate.com/pfsense/en/latest/monitoring/status/firewall-tables.html)
- [Netgate 실행 규칙 조회](https://docs.netgate.com/pfsense/en/latest/firewall/pf-ruleset.html)

EasyRule/PF 읽기 검사는 설치된 2.7.2 소스와 실제 장비를 기준으로 했다. `contracts/pfsense-examples`는 합성 데이터이며 실제 차단 성공 증거가 아니다.
