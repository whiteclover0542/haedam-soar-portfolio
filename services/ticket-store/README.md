# 티켓 저장소(114)·보안 대시보드 (C PC)

> **이 포트폴리오에서는:** 최상위 `compose.yaml`의 `ticket-store` 서비스로 띄운다(lan 10.250.0.3, 대시보드 127.0.0.1:8089, 키는 최상위 `.env`의 `TICKET_STORE_KEY`). 아래 내용은 팀 4대 환경 당시의 원문이다.

설계: [C 티켓 저장소 설계](../../docs/C-티켓저장소-설계.md) · 계약: `contracts/ticket*.schema.json` · 상태: **n8n check·record와 화면 구현(10/23, 로컬 컨테이너 시험만).** 10/26 C #59에는 D 인증 조회·쓰기 연결 보고가 있다. 아래 서비스 원본에는 10/26 집 후보 교정이 추가됐으며 학원 운영 버전과 다르다.

| 포트(컨테이너) | 공개(compose) | 내용 |
| --- | --- | --- |
| 8088 | `10.250.0.3:8088` | D n8n check·record (키 필요) — 구현(로컬 시험), 10/26 C 기록상 D 연결 성공, 집 교정 버전은 미배포 |
| 8089 | `127.0.0.1:8089` | 목록 `/`, 상세 `/tickets/<id>`, 닫기·취소 API, 읽기 API — 구현(로컬 시험) |

## 실행

10/29 집 후보: API 게시 주소는 `.env`의 `TICKET_BIND_IP`로 설정한다(기존 기본 10.250.0.3 유지). 격리된 집 확인은 127.0.0.1, 다른 환경에서는 승인된 사설 주소를 사용한다. 대시보드는 계속 loopback이다. 설정 해석과 합성 DB 백업/복원은 검증했지만 새 환경의 컨테이너 배포는 미검증이다. [전체 설치·유지보수·발표 실행 안내](../../docs/final-demo-operations.md), DB 도구 `tools/ticket_db_backup.py`를 참고한다.

```powershell
copy .env.example .env    # TICKET_STORE_KEY에 새 무작위 값(16자 이상). .env는 커밋하지 않음
docker compose up -d --build
```

- `10.250.0.3`에 묶으므로 팀 VPN이 연결돼 있어야 컨테이너가 뜬다. 띄운 뒤 `docker port`만 믿지 말고 실제 접속으로 확인한다.
- 샘플 티켓(`data_origin: sample`)을 보려면 `.env`에서 `TICKET_STORE_SAMPLES=1`, 목록은 `?sample=1`.
- 로컬 확인(10/23, 합친 뒤): 이미지 빌드, 두 포트가 서로 다른 경로만 응답, 샘플 배지·실제 연결 배지, 닫기(출발지 없음·다른 출발지 403, 대응 중 409, 효과 확인 200), 보안 헤더, 키가 로그에 없음, 메모리 약 26MiB. 앱이 본 출발지는 Docker 게이트웨이(`172.17.0.1`)였다 → 출발지 IP로 막지 않고 포트·공개 주소로 나눈 이유.

## 파일과 담당 세션

| 파일 | 내용 | 담당 |
| --- | --- | --- |
| `ticket_store/db.py` | SQLite 표, 읽기 함수, `close_ticket`(해제 안 된 조치가 남으면 거절), `cancel_ticket` | D 협업 세션 |
| `ticket_store/samples.py`, `samples/tickets.json` | 상태 5가지·대응 실패를 담은 샘플 6건 | D 협업 세션 |
| `ticket_store/api_read.py` | 대시보드 읽기 API | D 협업 세션 |
| `ticket_store/app.py`, `__main__.py`, Dockerfile, compose | 두 앱·두 포트 실행 | D 협업 세션 |
| `ticket_store/core.py`, `api_n8n.py`, `validate.py` | check·record, 중복 방지, 상태 규칙, 요청 검사(계약과 같은 규칙) | D 협업 세션 |
| `ticket_store/dashboard.py`, `templates/`, `static/` | 화면(목록·상세·닫기) | 화면 세션 |

시험: `python -m pytest tests/test_ticket_store_*.py -q`

## 10/27 집 통합 후보

[변경·검증·학원 인수](../../docs/home-integration-1027.md)를 따른다. 인증 `/active` 자원 조회, 현재 활성 조치의 중복/효과/해제, 마지막 조치 후 restored, 원복 뒤 새 이벤트 detected의 새 open 회차 예약·과거 재전송 차단, 기존 PF fw_block 읽기 호환을 추가했다. 계약·예시는 contracts/ticket*.schema.json 및 ticket-examples에 함께 반영했다. DB 표 이행은 없고 과거 원문은 보존하지만 운영 DB 복제·백업/되돌리기와 기존 불일치 이력 대조는 배치 전에 필요하다. `/active`는 조회이며 동시 실행 보호가 아니다. C 최신의 늦은 effect409, 활성 조치가 남은 티켓의 close 거절, 실제 조치·실패가 없는 open 시험 티켓의 취소 API도 포함한다. 취소 버튼은 이번 화면에 추가하지 않았으며 API의 Origin·화면 토큰 검사는 유지한다.

## 10/26 보안 대시보드 디자인 후보

목록·상태 카드·필터·샘플/수신 구분, 사건 상세·타임라인·대응/효과 확인과 모바일 카드를 개선했다. 수동 새로고침과 실패 보존·키보드 포커스 보호를 포함하며 종료 정책과 DB/API 계약은 유지한다. [변경·검증·학원 인수](../../docs/security-dashboard-design-1026.md), 집 미리보기는 `python tools/preview_security_dashboard.py --samples`다. 임시 DB와 loopback만 사용하며 실제 C 배포는 별도다.

## 10/29 S12 실측 비교 후보

정상 사용자 probe CSV의 전후 성공률·중앙값·p95를 S12 티켓과 연결해 `/s12` 및 상세에서 표시한다. 기존 DB에 추가 표를 생성하므로 운영 적용 전 백업한다. 샘플은 기본 제외하고 미측정은 0으로 대체하지 않는다. [CSV 등록·발표 사용법](../../docs/s12-dashboard-comparison.md)을 참고한다. 학원 배포·실측은 별도다.
