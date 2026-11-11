# S7 홈페이지 파일 변조 — 실습 안내

S7은 포털 정적 파일(`/app/dist`)에 대한 Wazuh FIM 시나리오입니다. 이 저장소에서 **파일 변조 → Wazuh FIM → Graylog 전달·분류 → n8n `haedam-33` → 티켓 → Wazuh Active Response 자동 복구 → 기준 해시 일치**까지 실측했습니다(2026-11-11 UTC, 3/3·기준선 오탐 0/1). 수치는 [S7 티켓](../../docs/tickets/S7/README.md)과 [정량평가](../../docs/정량평가.md)에 있습니다.

> Discord 알림은 `.env`의 `DISCORD_WEBHOOK_URL`이 있어야 전송됩니다. 비어 있으면 마지막 알림 단계만 실패하고, 복구·티켓 기록은 그 앞에서 끝납니다. 이 PC 실측에서는 Discord 수신을 확인하지 못했습니다.

## 1. 준비

```powershell
docker compose --profile soc --profile wazuh up -d
python infra/wazuh/enable_s7.py
python infra/graylog/bootstrap.py --live
python infra/n8n/load.py --s7
```

- `enable_s7.py`는 Wazuh Manager의 FIM 경보를 Graylog UDP 5514로 전달합니다(이미 켜져 있으면 `already`).
- `bootstrap.py --live`는 Graylog 알림 본문에 `dry_run:false`를 실어 n8n이 실제 Active Response를 호출하게 합니다. 빼면 관찰 모드(`dry_run`)입니다.
- `load.py --s7`은 S7과 의존 워크플로 5개만 반입·게시합니다(pfSense 개인 키 불필요).

다음 명령이 Agent `haedam-portal` `Active`와 `wazuh-syscheckd is running`을 보여야 합니다. Code 노드를 돌리는 외부 Runner는 `docker logs haedam-n8n`의 `Registered runner`로 확인합니다.

```powershell
docker exec haedam-wazuh-manager /var/ossec/bin/agent_control -l
docker exec haedam-portal /var/ossec/bin/wazuh-control status
```

## 2. 변조와 자동 복구

기준 파일 4개(`index.html`, `favicon.svg`, `assets/*.css`, `assets/*.js`)의 해시는 `/opt/haedam-s7/baseline.sha256`에 있습니다. 끝에 주석 한 줄을 붙이면 화면은 그대로이고 해시만 바뀝니다.

```powershell
docker exec haedam-portal python /opt/haedam-s7/bin/s7_restore.py verify      # result: ok
docker exec haedam-portal sh -c 'printf "\n<!-- s7 lab -->\n" >> /app/dist/favicon.svg'
# 30~60초 뒤
docker exec haedam-portal sha256sum /app/dist/favicon.svg                       # 기준 해시 5186e8e9…로 복구
docker exec haedam-portal python /opt/haedam-s7/bin/s7_restore.py verify      # result: ok
```

Graylog에서는 `file_key:"favicon.svg"` 메시지에 `signal_kind:fim-change`, `s7_change_type:modified`, `wazuh_agent_name:haedam-portal`이 보입니다. 티켓 대시보드의 S7 티켓에는 `wazuh-ar restore applied`가 기록됩니다.

- 새 파일(기준본에 없는 파일)을 추가하면 같은 경로로 **격리**(`quarantine`)됩니다.
- 같은 파일을 다시 바꾸면 haedam-33은 열린 티켓을 다시 쓰고 복구를 한 번 더 실행합니다.
- AR 복구가 만든 FIM 경보는 해시가 기준본과 같아 Graylog가 신호에서 빼므로 복구가 반복되지 않습니다.

## 3. 실측 실행기와 제어판

```powershell
python lab/s7/live.py --file favicon.svg                 # 한 회차: 변조 → 티켓 → 복구 → 해시·권한 판정 → runs.jsonl
python lab/s7/live.py --file index.html --baseline       # 같은 내용 재배포: 티켓이 없어야 pass
python tools/summarize_runs.py                           # 정량평가 표 갱신
```

제어판(`python lab/panel.py`)의 S7 탭은 **[공격]**(favicon.svg 변조) → ①~⑤ 자동 확인 → **[해제]**(전체 `verify`) 순서입니다.

## 4. 권한 경계

- 키(`X-Haedam-Key`) 없이 `haedam-33` 웹훅을 부르면 `403`.
- AR 도구는 웹 루트 밖 경로를 거부합니다: `s7_restore.py restore ../../etc/passwd` → `error path_outside_web_root`.
- Wazuh AR 명령은 `s7-restore-ar` 하나만 등록돼 있고, 실행 ID는 `[A-Za-z0-9._-]{1,64}`만 받습니다.
