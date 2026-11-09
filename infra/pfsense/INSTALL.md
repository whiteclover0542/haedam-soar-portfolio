# pfSense CE 2.7.2 설치 (QEMU 컨테이너)

진짜 pfSense를 컨테이너 안 QEMU/KVM VM으로 띄운다. 처음 한 번만 콘솔에서 설치하고, 설치 디스크는 볼륨 `haedam_pfsense-data`에 남는다.

## 1. ISO 받기

```powershell
curl.exe -fSL -C - --retry 5 -o infra\pfsense\iso\pfSense-CE-2.7.2-RELEASE-amd64.iso.gz https://atxfiles.netgate.com/mirror/downloads/pfSense-CE-2.7.2-RELEASE-amd64.iso.gz
(Get-FileHash infra\pfsense\iso\pfSense-CE-2.7.2-RELEASE-amd64.iso.gz).Hash
# 883FB7BC64FE548442ED007911341DD34E178449F8156AD65F7381A02B7CD9E4 이어야 한다
```

압축은 풀지 않는다. 컨테이너가 처음 켜질 때 직접 푼다.

## 2. 기동과 설치

```powershell
docker compose --profile pfsense up -d --build
```

http://127.0.0.1:8006/vnc.html → Connect

1. Accept → Install → 키맵 기본값
2. 파티션 Auto (ZFS) → **stripe** → `vtbd0`를 스페이스바로 체크 → Last Chance에서 YES
3. 설치가 끝나면 Reboot. 인터페이스는 WAN `em0`, LAN `em1`로 자동 지정된다.
4. 메뉴 `2`에서 두 인터페이스를 설정한다.
   - WAN: DHCP `n`, `203.0.113.1` / `24`, 게이트웨이 없음, IPv6 없음
   - LAN: `10.250.0.1` / `24`, 게이트웨이 없음, IPv6 없음, DHCP 서버 `n`

## 3. 웹 설정

https://127.0.0.1:8443 (포트를 빼면 다른 서비스로 간다), 첫 로그인 `admin` / `pfsense`

- 설정 마법사: Timezone `Asia/Seoul`. WAN 페이지 맨 아래 **Block RFC1918**과 **Block bogon**의 체크를 둘 다 푼다(203.0.113.0/24는 bogon 목록에 있다). admin 비밀번호를 새로 정하고 `.env`의 `PFSENSE_ADMIN_PASSWORD`에 적는다.
- Firewall → NAT → Port Forward: WAN, TCP, WAN address:80 → `10.250.0.2:5000`, Add associated filter rule
- Status → System Logs → Settings: Log default blocks 체크, Remote Logging `10.250.0.100:514`, Firewall Events만 체크
- System → Advanced → Admin Access: Enable Secure Shell

[config.xml](config.xml)은 위 설정을 마친 상태를 내보낸 것이다. 비밀번호 해시·SSH 키·인증서는 자리표시로 바꿨으므로, 복원에 쓰려면 그 값을 다시 설정해야 한다.

## 4. 대응 도구와 n8n 전용 키

```powershell
mkdir .local  # git에서 제외됨
python tools\build_pfsense_bundle.py --out .local\pfsense-bundle
python .local\pfsense-bundle\install_bundle.py --verify
```

pfSense에 묶음을 올리고 root(admin)로 `install_bundle.py --install`을 실행하면 `/usr/local/sbin/haedam-pf-response`가 설치된다.

도구는 root 권한이 필요하므로 별도 계정을 두지 않는다. 대신 n8n 전용 ed25519 키(`.local/haedam-pf`)를 admin에 **제한 옵션을 붙여** 등록한다. config.xml의 admin `authorizedkeys`로 넣어야 재부팅 뒤에도 유지된다.

```text
from="10.250.0.103",restrict,command="/usr/local/sbin/haedam-pf-response" ssh-ed25519 AAAA... haedam-pf-response
```

원격 명령은 `haedam-pf-response <status|block|unblock> 203.0.113.22 <요청ID> <소유자ID>` 형식만 받는다.

## 확인 (2026-11-09 실측)

| 확인 | 결과 |
| --- | --- |
| `203.0.113.100` → `203.0.113.1:80` → `10.250.0.2:5000` | HTTP 200 |
| 받는 쪽에서 본 출발지 | `203.0.113.100` (보존) |
| `203.0.113.22` ping | 차단, `filterlog ... block,in ... 203.0.113.22` 원격 syslog 전송 |
| 전용 키, `.103`에서 `status` | `ok: true`, `ready: true` |
| 전용 키로 임의 명령 / `.104`에서 접속 | `invalid_ssh_command` / `Permission denied` |

## 알려진 함정

- **브리지 MAC 학습:** Docker 쪽이 VM 프레임을 되돌려 보내 VM MAC이 바깥 포트에 학습되면 통신이 끊긴다. entrypoint에서 바깥 포트 `learning off`로 막았다.
- **wan 마스커레이드:** 켜 두면 `br_netfilter` 때문에 lan으로 포워딩된 203.0.113.x 출발지가 `10.250.0.254`로 바뀐다. compose에서 wan 망만 `enable_ip_masquerade: "false"`로 둔다. 그래서 wan 컨테이너는 인터넷에 나가지 못하며, 도구는 이미지 빌드 때 설치한다.
