# 관리자 전체 계정 조회 · WQ04

GET `/api/v1/admin/users`. 기존 관리자 인증/역할 검사와 공개 User 필드만 사용한다. 집 구현 후보이며 학원 배포·운영 DB 검증과 구분한다.

| 입력 | 의미 |
| --- | --- |
| page | 1 이상 정수, 기본1. 범위 밖이면 items=[]이며 실제 total/pages는 유지 |
| page_size | 1~50 정수, 기본10 |
| q | 아이디 또는 표시 이름 부분 검색. 양끝 공백 제거 후 앞40자. `%`/`_`는 SQL 와일드카드가 아닌 문자로 검색 |
| role | 미지정/빈 값은 전체. citizen/staff/admin 중 하나 |
| locked | 미지정/빈 값은 전체. 정확히 true 또는 false. false는 이용 중 계정 |

role/locked의 잘못된 값과 중복 입력은400 VALIDATION_ERROR다. 기존 page/page_size 오류·401·403·DB 오류 규칙은 유지한다. 관리자 외에는 목록과 집계 모두 제공하지 않는다.

응답 스키마: [portal-admin-users.schema.json](../../contracts/portal-admin-users.schema.json), [합성 예시](../../contracts/portal-examples/admin-users-filtered.json).

- items는 q·role·locked의 교집합에 page/page_size를 적용하며 id 오름차순이다. total은 페이지 이전의 교집합 수, pages는 max(1,ceil(total/page_size))다.0건과 범위 밖 페이지는 다르다.
- summary.scope=`search`. summary.total·roles(citizen/staff/admin)·locked/unlocked는 q만 적용한 전체 계정 기준이다. 권한/잠금 필터와 페이지에 따라 숫자가 바뀌지 않는다. 역할별 합과 잠금/이용 중 합은 각각 summary.total과 같다. 검색을 바꾸면 재집계한다.
- 집계는 현재 조회 결과이며 과거 감사 이력·관제 탐지 수가 아니다. 다른 요청이 동시에 계정을 바꾸면 후속 조회가 달라질 수 있고 여러 화면에 걸친 고정 스냅샷은 제공하지 않는다.
- User의 기존 공개 필드(id/username/display_name/role/department/locked/created_at) 외 비밀번호 해시·토큰·세션을 반환하지 않는다. DB 구조·변경 API·잠금 해제/세션 회수·이벤트 스키마는 바꾸지 않는다.

호환: 새 입력과 summary는 부가적이므로 구 프론트는 기존 응답 필드를 계속 읽을 수 있다. 새 프론트는 summary 없는 구 서버에서 추정 숫자를 만들지 않고 계약 오류를 표시한다. 배포 순서는 백엔드→프론트이며 정상 빌드/FIM 기준본은 A/C와 맞춘다. 조회 응답 검증과 실제 학교 장비·MySQL 시험을 별도로 기록한다.
