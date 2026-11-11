"""H1 민원 도배: 계정별 민원 작성 제한(로그인·조회는 유지)과 대응 API. 작성: A."""
import itertools

from conftest import PASSWORD, Actor
from test_ip_block_and_file_key import events, respond

PETITION = {"title": "보행로 가로등 점검 요청", "content": "가로등이 켜지지 않아 점검을 요청합니다.", "category": "안전·시설"}
_keys = itertools.count()


def restrict(app, username, restricted, key=None):
    return respond(app, "POST", "/accounts/posting", {"username": username, "restricted": restricted},
                   key=key or f"posting-key-{next(_keys):04d}")


def post(actor):
    return actor.call("POST", "/petitions", PETITION)


def test_restricted_user_gets_429_and_others_are_fine(app):
    citizen, other = Actor(app, "citizen"), Actor(app, "other")
    assert restrict(app, "citizen", True).status_code == 200
    refused = post(citizen)
    assert refused.status_code == 429 and refused.json["error"]["code"] == "POSTING_RESTRICTED"
    assert post(other).status_code == 201


def test_restricted_user_can_still_login_and_list(app):
    restrict(app, "citizen", True)
    citizen = Actor(app, "citizen")  # login asserts 200 inside
    assert citizen.call("GET", "/petitions").status_code == 200
    assert citizen.call("GET", "/auth/me").json["data"]["user"]["posting_restricted"] is True


def test_allow_restores_201(app):
    citizen = Actor(app, "citizen")
    restrict(app, "citizen", True)
    allowed = restrict(app, "citizen", False)
    assert allowed.json["data"] == {"user_id": allowed.json["data"]["user_id"], "username": "citizen",
                                    "posting_restricted": False, "changed": True}
    assert post(citizen).status_code == 201


def test_restrict_is_idempotent(app):
    assert restrict(app, "citizen", True).json["data"]["changed"] is True
    assert restrict(app, "citizen", True).json["data"]["changed"] is False
    first = restrict(app, "citizen", False, key="same-key-123")
    assert restrict(app, "citizen", False, key="same-key-123").json == first.json


def test_restrict_refuses_admin(app):
    assert restrict(app, "admin", True).status_code == 403


def test_restrict_unknown_user_404(app):
    assert restrict(app, "nobody", True).status_code == 404


def test_restrict_requires_boolean(app):
    assert restrict(app, "citizen", "yes").status_code == 400


def test_restrict_requires_response_key_and_network(app):
    no_key = app.test_client().post("/api/v1/response/accounts/posting", json={"username": "citizen", "restricted": True},
                                    headers={"Idempotency-Key": "posting-no-key-1"})
    assert no_key.status_code == 403
    outside = respond(app, "POST", "/accounts/posting", {"username": "citizen", "restricted": True},
                      key="posting-outside-1", addr="203.0.113.11")
    assert outside.status_code == 403


def test_restriction_and_refusal_are_logged(app):
    citizen = Actor(app, "citizen")
    restrict(app, "citizen", True)
    post(citizen)
    kinds = [(e["event_type"], e["username"], e["details"]["status"]) for e in events(app)]
    assert ("auth.posting_restricted", "citizen", 200) in kinds
    assert ("petition.create_refused", "citizen", 429) in kinds
