from sqlalchemy import select

from test_portal import create
from haedam_portal.models import PetitionRevision, db


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
