# H3 민원 처리 결과 조작 대응 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 담당자 계정의 짧은 시간 내 민원 처리 결과 조작을 탐지하고, 변경 전 스냅샷을 바탕으로 안전하게 복원한다.

**Architecture:** 포털은 상태 변경 직전에 불변 `PetitionRevision` 스냅샷을 남기며, 대응 API는 응답망·키·Idempotency-Key를 확인한 뒤 가장 최근 스냅샷으로만 복원한다. Graylog는 `petition.updated`를 담당자 계정별로 묶고, n8n은 계정을 잠근 뒤 티켓을 남기고 각 대상 민원을 복원한다. 실측은 전용 staff 계정과 합성 민원만 사용해 1회 실행하고, 결과는 H3 티켓 문서에 기록한다.

**Tech Stack:** Flask, SQLAlchemy/Alembic, Graylog event definition JSON, n8n workflow JSON, pytest.

**Spec:** `docs/MVP-설계.md` 7절 H3, `docs/검증-체크리스트.md` H3, `docs/PROGRESS.md` H3 표.

## Global Constraints

- 변경 전 상태·답변·담당자·버전을 복원 가능한 스냅샷으로 남긴다.
- 복원은 응답망의 `X-Response-Key`와 `Idempotency-Key`가 있어야 하며 관리자 계정에는 적용하지 않는다.
- H3 실측은 전용 `zz_` staff 계정과 합성 민원만 사용하고 1회 성공 기록 후 중지한다.
- 정량평가 집계 표는 수정하지 않는다.
- 스택 반입·실제 대응은 모든 정적·로컬 테스트 후 한 번의 승인된 실측에서만 한다.

## Review Focus

- 완료 민원의 답변까지 스냅샷과 동일하게 복원되는지 — Task 1·2 테스트.
- 동일 복원 요청 재전송이 같은 결과를 돌려주고 데이터를 두 번 바꾸지 않는지 — Task 2 테스트.
- 담당자 아닌 계정·관리자 계정·응답망 밖 호출을 차단하는지 — Task 2 테스트.
- 서로 다른 담당자의 변경이 하나의 H3 알림으로 합쳐지지 않는지 — Task 3 정적 경계 검사.
- 1회 실측 기록이 정량평가 표가 아니라 H3 티켓 문서에만 남는지 — Task 5 확인.

---

### Task 1: 포털 변경 전 스냅샷

**Files:**
- Modify: `services/portal/backend/src/haedam_portal/models.py`
- Modify: `services/portal/backend/src/haedam_portal/petitions/__init__.py`
- Create: `services/portal/backend/migrations/versions/<revision>_add_petition_revisions.py`
- Test: `services/portal/backend/tests/test_h3_restore.py`

**Interfaces:**
- Produces `PetitionRevision.snapshot(petition, actor_id) -> PetitionRevision` before a staff status/reply change.
- Produces revision rows containing `status`, `reply`, `assignee_id`, and original `version`.

- [ ] Write a failing test that changes an assigned petition and asserts one revision holds the exact pre-change status, reply, assignee, and version.
- [ ] Run the single test and confirm it fails because `PetitionRevision` does not exist.
- [ ] Add the model, migration, and one snapshot insertion immediately before `petition.status`/`petition.reply` mutate.
- [ ] Run the single test, then the portal test suite with `PYTHONPATH=src python -m pytest -q`.
- [ ] Commit the snapshot implementation and tests.

### Task 2: 관리자 전용 H3 복원 대응 API

**Files:**
- Modify: `services/portal/backend/src/haedam_portal/integration/__init__.py`
- Test: `services/portal/backend/tests/test_h3_restore.py`

**Interfaces:**
- Produces `POST /api/v1/response/petitions/<petition_id>/restore` with JSON `{ "revision_id": <int> }`.
- Returns the restored petition summary plus `changed`, `revision_id`, and `revoked_sessions`.

- [ ] Write failing tests for restoring status/reply/assignee from a named revision, rejecting a revision for another petition, and replaying the same Idempotency-Key.
- [ ] Run those tests and confirm the endpoint is absent.
- [ ] Implement response-network authentication, request receipt replay, administrator exclusion, and transactional restore; emit `petition.restored` only when data changes.
- [ ] Run the H3 tests plus existing response API tests.
- [ ] Commit the restore API and tests.

### Task 3: H3 탐지·대응 정의의 정적 계약

**Files:**
- Create: `lab/h3/graylog/h3-petition-update.json`
- Create: `lab/h3/graylog/check.py`
- Create: `infra/graylog/notifications/h3-n8n-haedam-h3.json`
- Create: `infra/n8n/workflows/haedam-37-h3-main.json`
- Modify: `infra/graylog/bootstrap.py`
- Modify: `infra/n8n/load.py`
- Modify: `infra/n8n/make_credentials.py`
- Test: `tests/test_graylog_bootstrap.py`
- Test: `tests/test_n8n_credentials.py`

**Interfaces:**
- Graylog groups `petition.updated` by `username`, within five minutes, at a threshold encoded once in the definition.
- n8n accepts only case `H3`, records the ticket, locks the actor, and invokes the restore endpoint with the detected petition revisions.

- [ ] Write failing static tests for H3 stream registration, caller credential, inactive workflow default, account lock before restore, and same-user boundary cases.
- [ ] Run the tests/checker and confirm missing assets fail.
- [ ] Add JSON definitions and static checker only; do not import them into a running stack during this task.
- [ ] Run static H3 checks and root `python -m pytest -q tests`.
- [ ] Commit H3 definition and workflow assets.

### Task 4: H3 one-shot runner and panel contract

**Files:**
- Modify: `lab/run_ticket.py`
- Modify: `lab/panel.py`
- Create: `lab/h3/input.py`
- Modify: `tests/test_run_ticket.py`
- Modify: `tests/test_panel.py`

**Interfaces:**
- `lab/h3/input.py` builds the preflight plan without requests.
- `run_ticket.py H3 --restore` uses generated `zz_` staff/account data, makes exactly the threshold update attempts, and checks restored snapshots.

- [ ] Write failing tests for an H3 preflight plan, H3 runner source/seat/window registration, and panel H3 availability.
- [ ] Run the tests and confirm H3 remains pending.
- [ ] Implement the pure plan builder and one-shot runner wiring; preserve the existing H2 runner changes from other work.
- [ ] Run root tests and portal tests.
- [ ] Commit the runner and panel contract.

### Task 5: One successful live run record

**Files:**
- Create: `docs/tickets/H3/README.md`
- Create: `docs/tickets/H3/runs.jsonl`
- Modify: `docs/검증-체크리스트.md`
- Modify: `docs/PROGRESS.md`

- [ ] Confirm the stack import/deployment state and use only a generated `zz_` staff account and generated petitions.
- [ ] Run one H3 flow, record timestamps, ticket ID, observed restored snapshots, normal-user result, and restore authorization result in `docs/tickets/H3/`.
- [ ] Mark only evidence actually observed in the H3 checklist and progress table; leave repeat/median measurement unchecked.
- [ ] Do not edit `docs/정량평가.md`.
- [ ] Run the relevant verifier/tests and commit the one-run evidence.

## Self-review

- H3 requirements map to Tasks 1–5: snapshots (1), safe restoration (2), detection/automation assets (3), reproducible input (4), one-run evidence (5).
- The API and workflow agree on `revision_id`, `petition_id`, `H3`, and a lock-before-restore ordering.
- All review-focus cases are assigned to Tasks 1–5.
- The plan separates implementation from stack import and single live measurement so the latter cannot happen accidentally.
