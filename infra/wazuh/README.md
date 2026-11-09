# Wazuh 4.9.2 single-node

원본 구성: Wazuh Inc. `wazuh-docker` v4.9.2 single-node(GPLv2). 단일 PC 조정: 반소람.
최상위 `compose.yaml`의 `wazuh` 프로필로 띄운다. manager 10.250.0.4, indexer 10.250.0.6, dashboard 10.250.0.7(https://127.0.0.1:5601).

## 처음 설치

```powershell
docker volume create haedam_wazuh-certs
docker compose -f infra/wazuh/generate-certs.yml run --rm generator   # 인증서를 볼륨에 바로 만든다
python infra/wazuh/make_users.py                                     # .env 비밀번호 → internal_users.yml(git 제외)
docker compose --profile wazuh up -d
```

- 인증서는 Windows 바인드 마운트로 넣으면 키 파일 권한 때문에 indexer가 읽지 못한다. 그래서 볼륨 하나를 세 컨테이너에 마운트하고, 설정 파일은 생성기가 만든 파일 이름(`wazuh.indexer-key.pem` 등)을 그대로 가리킨다.
- dashboard 인증서는 `/usr/share/wazuh-dashboard/certs`에 둔다. `/etc/wazuh-dashboard/certs`에 두면 Docker가 root 소유로 `/etc/wazuh-dashboard`를 만들어 keystore 쓰기가 `EACCES`로 실패한다.
- 비밀번호 3개(`WAZUH_INDEXER_PASSWORD`·`WAZUH_DASHBOARD_PASSWORD`·`WAZUH_API_PASSWORD`)는 `.env`에만 있다. compose와 설정 파일에는 값이 없다.

## 비밀번호 교체 (이미 띄운 뒤)

indexer 보안 인덱스와 API 설정은 볼륨을 처음 만들 때만 값을 받는다. 볼륨을 지우지 않고 바꾸는 순서:

1. `.env`의 값을 바꾼다(대·소문자·숫자·기호, 8~64자, `$`·따옴표 제외).
2. `python infra/wazuh/make_users.py`
3. `docker compose --profile wazuh up -d --force-recreate`
4. indexer에 새 사용자 반영:

   ```sh
   docker exec haedam-wazuh-indexer bash -c 'export JAVA_HOME=/usr/share/wazuh-indexer/jdk; C=/usr/share/wazuh-indexer/certs; bash /usr/share/wazuh-indexer/plugins/opensearch-security/tools/securityadmin.sh -f /usr/share/wazuh-indexer/opensearch-security/internal_users.yml -t internalusers -icl -nhnv -h 127.0.0.1 -cacert $C/root-ca.pem -cert $C/admin.pem -key $C/admin-key.pem'
   ```

5. `docker restart haedam-wazuh-dashboard haedam-wazuh-manager`
6. 확인: `python tools/check_stack.py`의 wazuh OK, dashboard 302, 옛 비밀번호 401.

API(`wazuh-wui`) 비밀번호는 manager가 기동할 때 `API_PASSWORD`로 맞춘다(11/09 확인: 재생성 후 새 값 200, 옛 값 401).
