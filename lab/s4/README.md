# S4 오프라인 입력 계획

`input.py`는 S4 상관 규칙에 필요한 입력(동일 계정·출발지의 실패 5회 뒤 성공 1회)을 JSON으로만 생성한다. 포털 요청, Docker 실행, n8n/Graylog 반입을 전혀 하지 않는다.

```powershell
python lab/s4/input.py --username zz_s4_test --src-ip 203.0.113.22
python lab/s4/preflight.py
python lab/s1s4/graylog/check.py
python -m pytest -q tests/test_s4_offline.py tests/test_s4_preflight.py tests/test_s4_evidence.py
```

`preflight.py`는 파일만 읽어 다음을 확인한다.

- S4 입력이 여섯 이벤트의 오프라인 계획인지
- Graylog 정의가 `username`·`src_ip` 묶기와 10분 창을 쓰는지
- `haedam-31`이 비활성·`dry_run:true`인지
- S4가 Graylog bootstrap과 n8n 반입 범위에 **포함됐는지**(2026-11-11 반입)

`evidence.py`는 실제 실행 뒤에 **복사해 둔** 포털 이벤트 JSONL만 분석한다. S4 조건 시각, 계정 잠금, 비밀번호 재설정, 재로그인 시각과 두 구간의 초 단위 시간을 산출하지만, 서비스에는 요청하지 않는다.

```powershell
python lab/s4/evidence.py docs/tickets/S4/portal-events.jsonl
```

이 분석 방식은 이전 팀 S4 실측 기록의 조건(10분 안에 동일 계정·출발지에서 401 5회와 200 1회, 429 제외) 및 시간 산출만 재사용한 것이다. 이전 VM의 SSH 주소·계정·비밀번호·실행기는 포함하지 않는다.

위 명령은 서비스에 요청하지 않는다. 실측은 `python lab/run_ticket.py S4 --restore`(같은 출발지 5분 간격)로 하고, 결과와 절차는 [S4 티켓](../../docs/tickets/S4/README.md)에 있다.
