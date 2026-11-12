# S7 · 홈페이지 파일 변조 대응 (Wazuh FIM · Active Response)

팀 티켓 S7(원작 C)을 PC 한 대 구성에서 실측한 기록입니다. 포털 컨테이너(`haedam-portal`) 안의 Wazuh Agent가 정적 파일 경로 `/app/dist`를 실시간 FIM으로 감시합니다.

## 흐름

```text
/app/dist 파일 변경 ─▶ Wazuh Agent FIM ─▶ Manager 규칙 550(변경)·554(추가)
   ─▶ Graylog UDP 5514 ─▶ s7-wazuh 파이프라인(file_key, 기준 해시 조회로 정상 배포 제외)
   ─▶ 이벤트 "S7 홈페이지 파일 변조" (1분 평가) ─▶ n8n haedam-33
   ─▶ 티켓 detected ─▶ Wazuh API Active Response `!s7-restore-ar`
   ─▶ 에이전트의 s7_restore.py: 바뀐 파일은 기준본으로 복구, 새 파일은 격리 ─▶ 티켓 applied ─▶ Discord 알림
```

- 기준본: `/opt/haedam-s7/baseline/`(읽기 전용 복사본)과 `baseline.sha256`(파일 4개).
- 정상 배포 제외: Graylog 조회 테이블 `s7_baseline_hashes`에 있는 해시이고 그 해시의 파일 키가 같을 때만 신호에서 뺍니다. 그래서 AR 복구가 다시 일으키는 FIM 경보도 티켓을 만들지 않습니다.
- 같은 파일을 다시 변조하면 haedam-33은 열린 티켓을 다시 쓰고 복구를 다시 실행합니다(복구는 유지되는 차단이 아니라 한 번의 동작). 그래서 회차마다 다른 기준 파일을 씁니다.

## 실측 방법

```powershell
python infra/graylog/bootstrap.py --live
python lab/s7/live.py --file favicon.svg
python lab/s7/live.py --file assets/index-B-UW_yMb.css
python lab/s7/live.py --file assets/index-BlaKRntd.js
python lab/s7/live.py --file index.html --baseline
```

- 공격 입력: 기준 파일 끝에 주석 한 줄을 덧붙입니다(화면에는 영향 없음, sha256만 바뀜).
- "공격자" 열: 변조된 경로가 지금 내주는 내용이 기준 해시와 같으면 `baseline_hash`(복구됨).
- "normal" 열: 시민이 받는 포털 첫 화면(`http://127.0.0.1:8080/`)의 HTTP 상태.
- "해제 후 공격자" 열: 복구 뒤 같은 경로 응답(`200` + 기준 해시).
- 권한: 키 없는 haedam-33 호출 `403`, AR 도구에 웹 루트 밖 경로(`../../etc/passwd`)를 주면 `path_outside_web_root`로 거부.
- 기준선: 같은 바이트로 `index.html`을 다시 쓰고 `touch`(정상 재배포 흉내). Wazuh는 규칙 550을 냈지만 해시가 기준본과 같아 Graylog가 신호에서 제외했고, 150초 동안 새 티켓·새 조치가 없어 `pass`.

## 실측 3회·기준선 (2026-11-11 UTC)

<!-- runs:start -->
| 회차 | 입력(UTC) | 티켓 | 결과 | 자동 대응 | MTTD | 탐지→차단 | 입력→차단 | 공격자 / normal | 해제 후 공격자 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-11-11 17:51:21 | T-20261111-0008 | pass | 예 | 0.425초 | 3.783초 | 29.528초 | baseline_hash / 200 | 200 |
| 2 | 2026-11-11 17:52:06 | T-20261111-0009 | pass | 예 | 0.097초 | 3.512초 | 43.256초 | baseline_hash / 200 | 200 |
| 3 | 2026-11-11 17:52:59 | T-20261111-0010 | pass | 예 | 0.204초 | 5.341초 | 52.792초 | baseline_hash / 200 | 200 |
| 4 | 2026-11-11 17:54:18 | — | pass (기준선) | 아니요 | — | — | — | — / — | — |
<!-- runs:end -->

## 시험 회차(표에 넣지 않음)

- `T-20261111-0007` (17:47 UTC): 실행기를 만들기 전에 `index.html`을 손으로 변조해 본 회차입니다. FIM 550(2초) → 티켓 → AR 복구까지 이어져 17:49:19에 원래 해시(`57126da8…`)로 돌아왔습니다. 같은 절차를 `lab/s7/live.py`로 옮긴 뒤 위 3회를 새로 셌습니다.
- 그 전 제어판 회차(`T-20261111-0005`·`0006`, 새 파일 추가 → 격리)는 Live AR 전 로컬 격리 확인용이라 지표에 넣지 않았습니다.

## 한계

- **Discord 수신 미검증:** 이 PC의 `.env`에 `DISCORD_WEBHOOK_URL`이 비어 있어 마지막 알림 단계는 전송되지 않습니다. 복구 조치와 티켓 기록은 알림보다 앞에서 끝나므로 지표에는 영향이 없습니다.
- **티켓 상태:** 복구 뒤 티켓은 `responding`입니다. 제어판 S7 [해제]가 웹 루트 전체를 기준 해시로 검증해 `ok`이면 열린 S7 티켓에 효과 확인 기록을 남겨 `verified`로 바꾸고, 사람이 대시보드에서 닫습니다. Wazuh `restore`는 되돌리기 자체라 풀 대상이 아니므로 닫기를 막지 않습니다(2026-11-12 티켓 저장소 수정 전에는 S7 티켓을 닫을 수 없었음).
- **입력→복구 29~53초:** Graylog 1분 평가 주기와 알림 전달 대기가 대부분입니다. 탐지(MTTD)는 0.1~0.4초, 탐지→복구는 4초 안팎입니다.
