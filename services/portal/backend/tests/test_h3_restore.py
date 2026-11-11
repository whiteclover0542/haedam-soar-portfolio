from datetime import timedelta

from sqlalchemy import select

from test_portal import create
from haedam_portal.models import Petition, PetitionRevision, User, db


def test_staff_status_change_stores_the_complete_prechange_snapshot(app, actors):
    petition = create(actors["citizen"])
    petition_id = petition["id"]
    staff = actors["staff"]

    assigned = staff.call("PATCH", f"/petitions/{petition_id}/assignment", {}).json["data"]
    changed = staff.call("PATCH", f"/petitions/{petition_id}/status", {
        "status": "in_progress", "version": assigned["version"],
    })

    assert changed.status_code == 200
    with app.app_context():
        revision = db.session.scalar(select(PetitionRevision).where(PetitionRevision.petition_id == petition_id))
    assert revision.status == "received"
    assert revision.reply == ""
    assert revision.assignee_id == actors["staff"].client.get("/api/v1/auth/me").json["data"]["user"]["id"]
    assert revision.version == assigned["version"]


def test_response_restore_replays_a_petition_snapshot_once(app, actors):
    staff = actors["staff"]
    petition = create(actors["citizen"])
    petition_id = petition["id"]
    assigned = staff.call("PATCH", f"/petitions/{petition_id}/assignment", {}).json["data"]
    in_progress = staff.call("PATCH", f"/petitions/{petition_id}/status", {
        "status": "in_progress", "version": assigned["version"],
    }).json["data"]
    completed = staff.call("PATCH", f"/petitions/{petition_id}/status", {
        "status": "completed", "reply": "검증용 변경 답변입니다.", "version": in_progress["version"],
    })
    assert completed.status_code == 200
    with app.app_context():
        revision = db.session.scalar(select(PetitionRevision).where(
            PetitionRevision.petition_id == petition_id,
            PetitionRevision.status == "in_progress",
        ))

    headers = {"X-Response-Key": app.config["RESPONSE_API_KEY"], "Idempotency-Key": "h3-restore-0001"}
    client = app.test_client()
    restored = client.post(f"/api/v1/response/petitions/{petition_id}/restore", json={"revision_id": revision.id}, headers=headers)

    assert restored.status_code == 200
    assert restored.json["data"] == {
        "petition_id": petition_id, "revision_id": revision.id, "status": "in_progress",
        "reply": "", "assignee_id": revision.assignee_id, "changed": True,
    }
    assert client.post(f"/api/v1/response/petitions/{petition_id}/restore", json={"revision_id": revision.id}, headers=headers).json == restored.json


def test_response_restore_rejects_a_revision_from_another_petition(app, actors):
    staff = actors["staff"]
    first = create(actors["citizen"])
    assigned = staff.call("PATCH", f"/petitions/{first['id']}/assignment", {}).json["data"]
    assert staff.call("PATCH", f"/petitions/{first['id']}/status", {
        "status": "in_progress", "version": assigned["version"],
    }).status_code == 200
    with app.app_context():
        revision = db.session.scalar(select(PetitionRevision).where(PetitionRevision.petition_id == first["id"]))
    second = create(actors["other"])
    headers = {"X-Response-Key": app.config["RESPONSE_API_KEY"], "Idempotency-Key": "h3-restore-0002"}

    response = app.test_client().post(f"/api/v1/response/petitions/{second['id']}/restore", json={"revision_id": revision.id}, headers=headers)

    assert response.status_code == 409


def test_response_restores_every_recent_petition_changed_by_the_alerted_staff(app, actors):
    staff = actors["staff"]
    old, first, second = create(actors["citizen"]), create(actors["citizen"]), create(actors["other"])
    for petition in (old, first, second):
        assigned = staff.call("PATCH", f"/petitions/{petition['id']}/assignment", {}).json["data"]
        assert staff.call("PATCH", f"/petitions/{petition['id']}/status", {
            "status": "in_progress", "version": assigned["version"],
        }).status_code == 200
    with app.app_context():
        staff_id = db.session.scalar(select(User.id).where(User.username == "staff"))
        revisions = db.session.scalars(
            select(PetitionRevision).where(PetitionRevision.actor_id == staff_id).order_by(PetitionRevision.id)
        ).all()
        revisions[0].created_at -= timedelta(hours=1)
        db.session.commit()
        expected = [{"petition_id": r.petition_id, "revision_id": r.id, "status": "received", "reply": "",
                     "assignee_id": r.assignee_id, "changed": True} for r in revisions[1:]]

    response = app.test_client().post(
        "/api/v1/response/petitions/latest-revision/restore",
        json={"username": "staff"},
        headers={"X-Response-Key": app.config["RESPONSE_API_KEY"], "Idempotency-Key": "h3-latest-restore-0001"},
    )

    assert response.status_code == 200
    assert response.json["data"] == {"username": "staff", "restored": expected}
    with app.app_context():
        assert db.session.get(Petition, old["id"]).status == "in_progress"
