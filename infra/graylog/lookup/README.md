# S7 기준본 해시 조회 표 (D)

- 상태: **미반입 · Graylog 미시험** (2026-10-28). 큰 수정은 PR로 정한 뒤 D가 확인하고 반입한다.
- 쓰임: S7 파이프라인 규칙 `S7: FIM signal (not baseline)`이 `lookup_value("s7_baseline_hashes", <FIM 해시>)`로 정상 배포·117 복구 재경보를 거른다. **해시가 표에 있고 그 해시의 `file_key`가 경보의 `file_key`와 같을 때만** 제외한다(해시만 보면 허용된 다른 파일 내용으로 index.html을 덮는 회피가 제외돼 버림 — C 리뷰 10/28).

## `s7_baseline_hashes.csv`

| 열 | 뜻 |
| --- | --- |
| `sha256` (키) | dist 파일의 sha256 |
| `file_key` (값) | 웹 루트(`/home/haedam/haedam-portal-frontend/dist/`) 기준 상대 경로 |

현재 값은 A 프론트 #3 배포(frontend `2836a42`, 2026-10-28 16:18 기준본 교체, 117 verify ok)의 4개 파일이다. A가 준 값이며 D는 파일을 직접 해시하지 않았다(VM 접근 없음). 배포가 바뀌면 A가 새 해시를 주고 이 파일을 PR로 고친다.

| file_key | sha256 | 크기 |
| --- | --- | --- |
| index.html | 2aca4626…a1aa9 | 691B |
| assets/index-CuQfLiw0.js | f4acdd07…c1988 | — |
| assets/index-BXkCLx8z.css | eb760945…3fbc2 | 66,603B |
| favicon.svg | 5186e8e9…8f275c | 272B |

117 `manifest_sha256`은 `158af68…52451`(4개 묶음 단일 해시, 117 verify용이고 파일별 조회에는 쓰지 않음).

## 반입 순서 (D, PR 병합 뒤)

1. **CSV 연결:** `docker compose up -d graylog`로 컨테이너를 다시 만들어 `./lookup`이 `/usr/share/graylog/data/lookup`로 마운트되게 한다(이 PR의 compose 변경). 수신 공백·UDP 재확인은 평소처럼.
2. **CSV Data Adapter:** System → Lookup Tables → Data Adapters에서 `CSV File` 어댑터를 만든다.
   - File path `/usr/share/graylog/data/lookup/s7_baseline_hashes.csv`, Separator `,`, Key column `sha256`, Value column `file_key`, Quote char `"`, Check interval 60s
3. **Cache:** `Node-local, in-memory cache`(기본값) 하나.
4. **Lookup Table:** 이름 `s7_baseline_hashes`(규칙이 이 이름으로 부른다), 위 어댑터·캐시 연결. Default single value는 비운다(없으면 `lookup_value`가 null → 신호로 봄).
5. **규칙:** `pipelines/s7-parse.txt`의 규칙 3개를 넣고 연결한다.
   - `S7: FIM file_key` → `wazuh-parse` stage 2, `S7: FIM signal (not baseline)` → stage 3
   - `S7: web access 2xx` → `haedam-portal` 스트림 파이프라인(없으면 `s7-web-parse`를 만들어 연결)
6. **확인:** 알려진 기준본 해시(예: index.html `2aca4626…`)로 `lookup_value`가 file_key를 돌려주는지, 모르는 해시는 null인지 시험 메시지로 본다. `web.file_access`에 `file_key`가 담기는지 S7 실제 접근 1회로 확인한다.

## 주의

- 이 표가 **비어 있으면** 정상 배포·복구 재경보도 S7 신호가 된다(스펙 3절). 그래서 배포 구간은 결과표에서 제외한다.
- 비밀값은 없다. 해시와 파일 경로만 있다.
