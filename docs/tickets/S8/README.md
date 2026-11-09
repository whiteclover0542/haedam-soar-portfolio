# S8 포털 스캔 · 로그인 반복

- **원작:** 김명준(B) — 탐지 정의 `lab/s8s10/graylog/s8-scan-then-login.json`, 입력 도구 `tools/s8s10_input.py`

## 시나리오

| 단계 | 내용 |
| --- | --- |
| 입력 | `203.0.113.21`이 스캔 경로 `GET`(404) → CSRF 확보(200) → 로그인 실패(401). ping 없음 |
| 탐지 | Graylog 정의 "S8 포털 스캔·로그인 반복": 15분 안에 같은 `src_ip`의 `web-scan`·`login-bruteforce`(`card(rule) > 1`) |
| 대응 | n8n `haedam-32` → 포털 IP 차단만. pfSense 호출 없음(경계 신호가 없으므로) |
| 효과 | 공격자 `.21` 403(`IP_BLOCKED`), `normal` 200 |
| 원복 | `haedam-50`: 포털 해제 → 공격자 200, 티켓 `restored` |

## 실행

```powershell
python lab/run_ticket.py S8 --restore
```

기대: `actions`에 `pfsense` 없음, `effect.attacker` `"403"`, `restore.attacker_after` `"200"`.

## 실측

<!-- runs:start -->
| 회차 | 입력(UTC) | 티켓 | 결과 | 자동 대응 | MTTD | 탐지→차단 | 입력→차단 | 공격자 / normal | 해제 후 공격자 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-11-09 03:34:00 | T-20261109-0002 | pass | 예 | 0.049초 | 0.55초 | 46.384초 | 403 / 200 | 200 |
| 2 | 2026-11-09 03:49:16 | T-20261109-0005 | pass | 예 | 0.63초 | 0.479초 | 30.527초 | 403 / 200 | 200 |
| 3 | 2026-11-09 04:04:36 | T-20261109-0007 | pass | 예 | 0.921초 | 0.523초 | 10.985초 | 403 / 200 | 200 |
<!-- runs:end -->
