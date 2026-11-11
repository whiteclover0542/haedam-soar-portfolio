# 로컬 MVP 실행 모드

Docker Desktop 엔진이 꺼져 있어도 `python tools/offline_check.py`로 소스 구성과 pfSense 네트워크 매핑을 확인할 수 있다. 이 검사는 비밀값을 출력하지 않는다.

Docker Desktop을 켠 뒤에는 다음처럼 실행한다.

```powershell
# 전체 MVP: 로그 파이프라인, 자동화, pfSense까지 모두 실행
.\tools\mvp.ps1 start

# 경량 데모: 포털, MySQL, 티켓 저장소만 실행
.\tools\mvp.ps1 lite

# 게임 전: 컨테이너만 중지하고 데이터 볼륨은 유지
.\tools\mvp.ps1 stop

# 컨테이너와 메모리 사용량 확인
.\tools\mvp.ps1 status
```

`lite` 모드는 화면 데모용이다. Graylog, OpenSearch, Wazuh, n8n, pfSense가 실행되지 않으므로 탐지·자동 대응·방화벽 검증이 포함된 전체 MVP가 아니다.

pfSense는 첫 전체 기동 후 콘솔 메뉴 `2`에서 WAN `203.0.113.1/24`, LAN `10.250.0.1/24`를 설정한다. 두 인터페이스 모두 IPv6 주소와 DHCP 서버를 사용하지 않는다.
