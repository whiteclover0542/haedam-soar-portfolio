# H2 타인 민원 엿보기 구현 계획

## 목표

시민 계정이 타인의 민원 상세를 반복 조회하면 Graylog가 탐지하고, n8n이 계정 잠금과 포털 IP 차단을 기록 가능한 티켓으로 연결한다.

## 범위와 안전 기준

- 시민이 **존재하는 타인 민원**을 상세 조회하면 `403`과 `petition.access_denied` 이벤트를 남긴다.
- 없는 민원은 기존처럼 `404`를 유지한다.
- 일반 목록 조회, 본인 민원 조회, 담당자의 업무 범위는 바꾸지 않는다.
- 탐지 키는 `username`과 `src_ip`를 함께 사용한다. 한 시민의 실수나 다른 출발지의 요청이 합쳐지지 않는다.
- 임계값 N은 정상 사용 중 403 기준선을 측정한 뒤 확정한다. 정의 파일의 N=3은 배포 전 초안이다.

## 작업 순서

### H2-1 포털 이벤트

- `petitions.detail()`에서 시민의 타인 민원 상세 조회를 판별한다.
- `petition.access_denied`, `outcome=failure`, `status=403`, `username`, `src_ip`를 GELF 이벤트로 남긴다.
- 테스트: 타인 조회는 403·이벤트 1건, 본인 조회는 200·이벤트 없음, 없는 ID는 404.

### H2-2 Graylog 정의

- 쿼리: `source:haedam-portal AND event_type:"petition.access_denied" AND status:403`
- 창: 5분, 평가: 60초, 키: `username`, `src_ip`.
- 조건: `count() > 2`로 3건 이상을 탐지한다. 기준선 뒤 값은 함께 수정한다.
- 배포 전 `lab/h2/graylog/check.py`로 JSON 구조와 경계 사례를 확인한다.

### H2-3 대응 및 티켓

- 기존 `haedam-13` 계정 잠금과 `haedam-12` 포털 IP 차단을 순서대로 호출한다.
- 티켓에는 `restrict/lock`, `portal/block`, 결과, 대상 계정·IP를 기록하고 Discord 알림으로 연결한다.
- 해제 뒤 본인 민원은 200, 타인 민원은 계속 403인지 확인한다.

### H2-4~6 기준선·실측·증적

- 정상 탐색 중 403 빈도를 두 번 이상 측정한다.
- 독립 실측 3회에서 차단, 정상 사용자 영향 없음, 해제를 확인한다.
- `docs/tickets/H2/`에 회차·수치·캡처를 남긴 뒤 PROGRESS를 갱신한다.

