# H2 타인 민원 엿보기

`input.py`는 요청 계획만 만드는 도구이고, 실제 실측은 `lab/run_ticket.py H2 --restore` 또는 제어판 H2 탭으로 실행한다. 두 경로 모두 회차마다 새 피해 시민·새 공격 시민·새 민원만 사용한다.

```powershell
python lab/h2/input.py --username <공격_시민_계정> --petition-id <타인_민원_ID_1> --petition-id <타인_민원_ID_2> --petition-id <타인_민원_ID_3> --out lab/h2/plan.json
```

계획의 각 요청은 `GET /api/v1/petitions/{id}`이며, 기대 결과는 모두 `403`이다. 같은 `username`·`src_ip` 조합의 거부 이벤트 3건이 5분 안에 발생해야 H2 Graylog 초안의 조건(`count() > 2`)을 만족한다.

## 실제 실측

```powershell
python tools/check_stack.py
python infra/n8n/load.py
python infra/graylog/bootstrap.py --live
python lab/run_ticket.py H2 --restore
```

기대 흐름은 타인 민원 상세 `403` 세 건 → Graylog 탐지 → n8n H2 티켓 → 포털 IP 차단·공격 계정 잠금이다. 원복은 IP 해제 요청을 먼저 보류하고, 실습 계정의 비밀번호 재설정 뒤 최종 해제를 수행한다. 이후 공격 계정 로그인은 `200`, 타인 민원 상세는 계속 `403`이어야 한다.

제어판은 `python lab/panel.py`로 열어 H2의 **공격 → 효과 확인 → 해제**를 같은 로컬 실행 경로로 보여 준다.
