# S4 오프라인 입력 계획

`input.py`는 S4 상관 규칙에 필요한 입력(동일 계정·출발지의 실패 5회 뒤 성공 1회)을 JSON으로만 생성한다. 포털 요청, Docker 실행, n8n/Graylog 반입을 전혀 하지 않는다.

```powershell
python lab/s4/input.py --username zz_s4_test --src-ip 203.0.113.22
```

실측 전에는 `lab/s1s4/graylog/check.py`와 `tests/test_s4_offline.py`를 통과시킨 뒤, H2 종료 및 반입 승인 후에만 별도 절차로 진행한다.
