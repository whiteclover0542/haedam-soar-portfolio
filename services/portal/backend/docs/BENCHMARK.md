# 게시판 참고와 변경 사항

출처: `NoBugs-Aleph/flask-board-team`, `74fbb64`. 참고 파일: `flask-board/controllers/{auth_controller,authz,post_controller,gelf,admin_controller}.py`, `models/`, `tests/`.

로그인·서버 권한 검사·SQLAlchemy 분리·GELF rule 이름·실패와 정상 테스트 패턴을 참고했다. 기존 앱을 복사해 실행하지 않고 Flask 팩토리와 기능 경계를 새로 작성했다. 원본 게시판은 수정하지 않았다.

| 게시판 | 포털 |
|---|---|
| 공개 글 목록 | 본인·지정 담당자만 조회, 미배정은 staff 대기열 |
| user/gold/admin 숫자 위계 | citizen/staff/admin 역할 분리, admin 민원 본문 접근 없음 |
| JWT 헤더·쿠키와 localStorage | 서버 저장 세션, 쿠키 HttpOnly, 브라우저에 토큰 저장 안 함 |
| 전달 헤더 우선 | 프록시 없는 경로의 연결 주소만 사용 |
| 로그인 시 잠금 검사 | 매 요청 잠금 확인 + 모든 세션 삭제 |
| 앱 내 보안 대시보드·티켓 | 관제 서비스 링크만 제공, 미설정 시 링크 없음 |
| 시작 시 create_all/스키마 수정 | 명시적인 Alembic 마이그레이션 |

민원 본문·제목·표시 이름은 이벤트에서 제외한다. 운영 PC의 비밀값·DB·인증서·규칙 설치 상태는 가져오지 않았다. 포털 이벤트는 별도 계약이므로 D의 수집·탐지 연결은 후속 검증 대상이다.
