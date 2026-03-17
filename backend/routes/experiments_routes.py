from fastapi import APIRouter, HTTPException

from ..database import Db, row_to_dict, utcnow_iso
from ..schemas.experiment_schema import ExperimentCreate, ExperimentOut


router = APIRouter(tags=["experiments"])


@router.post("/experiments", response_model=ExperimentOut)
def create_experiment(body: ExperimentCreate, db=Db):
    now = utcnow_iso()
    cur = db.execute(
        """
        INSERT INTO experiments (segment, messaging_angle, email_format, subject_variant, created_at, active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (body.segment, body.messaging_angle, body.email_format, body.subject_variant, now, 1 if body.active else 0),
    )
    db.commit()
    row = db.execute("SELECT * FROM experiments WHERE experiment_id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(db=Db):
    rows = db.execute("SELECT * FROM experiments ORDER BY created_at DESC").fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/experiments/{experiment_id}/results")
def get_experiment_results(experiment_id: int, db=Db) -> dict:
    exp = db.execute("SELECT * FROM experiments WHERE experiment_id = ?", (experiment_id,)).fetchone()
    if not exp:
        raise HTTPException(status_code=404, detail="experiment not found")

    row = db.execute("SELECT * FROM experiment_results WHERE experiment_id = ?", (experiment_id,)).fetchone()
    if row:
        return row_to_dict(row)

    # If no aggregate row exists yet, return computed v0 metrics.
    opened = db.execute(
        """
        SELECT COUNT(DISTINCT ee.email_id) AS n
        FROM email_events ee
        JOIN email_variants ev ON ev.email_id = ee.email_id
        WHERE ev.experiment_id = ? AND ee.event_type = 'opened'
        """,
        (experiment_id,),
    ).fetchone()["n"]
    replied = db.execute(
        """
        SELECT COUNT(DISTINCT r.email_id) AS n
        FROM replies r
        JOIN email_variants ev ON ev.email_id = r.email_id
        WHERE ev.experiment_id = ?
        """,
        (experiment_id,),
    ).fetchone()["n"]
    return {"experiment_id": experiment_id, "opens": opened, "replies": replied}
