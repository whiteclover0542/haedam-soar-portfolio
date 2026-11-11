# H2 타인 민원 엿보기 — 실행 전 입력 준비

이 폴더의 도구는 **실제 요청을 보내지 않는다.** H2 실측 전에 사용할 타인 민원 상세 조회 3회 이상의 요청 계획만 JSON으로 만든다.

```powershell
python lab/h2/input.py --username <공격_시민_계정> --petition-id <타인_민원_ID_1> --petition-id <타인_민원_ID_2> --petition-id <타인_민원_ID_3> --out lab/h2/plan.json
```

계획의 각 요청은 `GET /api/v1/petitions/{id}`이며, 기대 결과는 모두 `403`이다. 같은 `username`·`src_ip` 조합의 거부 이벤트 3건이 5분 안에 발생해야 H2 Graylog 초안의 조건(`count() > 2`)을 만족한다.

## 아직 하지 않는 것

- 포털·Graylog·n8n·pfSense에는 요청하거나 설정을 반입하지 않는다.
- 제어판 H2 탭은 대응 워크플로와 배포가 끝날 때까지 `연결 대기`로 둔다.
- 실제 실행은 기준선과 해제 절차가 확정된 뒤 별도 실측에서 한다.
