# S12 요청 폭주

가벼운 요청 버스트로 Graylog 요청 수 탐지 → 포털 IP 차단 → 티켓 → 효과 확인 → 해제까지 1회 확인한다.

```powershell
python infra/graylog/bootstrap.py --live
python infra/n8n/load.py
python lab/run_ticket.py S12 --restore
```

- 탐지: `lab/s12/graylog/s12-request-flood.json`(같은 `src_ip`의 `web.request`가 60초 창에서 N=60 초과). 이 PC 한 대 실습값.
- 부하 도구: `tools/s12_flood.py`(GET만, 속도·시간 상한, 차단되면 멈춤). `haedam-attacker`에서 출발지 `.42`로 실행.
- 대응: `haedam-20`이 요청 수 기준으로 차단(`count_based`, health 게이트 없음). 상세는 [S12 티켓](../../docs/tickets/S12/README.md).

실측 3회·정량평가·검증 체크리스트는 아직이다. 1회 성공만 확인했다.
