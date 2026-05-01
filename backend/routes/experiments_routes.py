from fastapi import APIRouter, HTTPException, Query

from ..database import Db, row_to_dict, utcnow_iso
from ..domain_types import SortOrder
from ..schemas.experiment_schema import ExperimentCreate, ExperimentOut


router = APIRouter(tags=["experiments"])


@router.post("/experiments", response_model=ExperimentOut)
def create_experiment(body: ExperimentCreate, db=Db):
    now = utcnow_iso()
    cur = db.execute(
        """
        INSERT INTO experiments (segment, messaging_angle, email_format, max_emails_total, subject_variant, created_at, active)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.segment,
            body.messaging_angle,
            body.email_format.value,
            body.max_emails_total,
            body.subject_variant,
            now,
            1 if body.active else 0,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM experiments WHERE experiment_id = ?", (cur.lastrowid,)).fetchone()
    out = row_to_dict(row)
    out["sent_count"] = db.execute(
        "SELECT COUNT(*) AS n FROM email_variants WHERE experiment_id = ? AND delivery_status = 'sent'",
        (out["experiment_id"],),
    ).fetchone()["n"]
    return out


@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", pattern="^(created_at|segment|messaging_angle|email_format|experiment_id)$"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    db=Db,
):
    sort_map = {
        "created_at": "created_at",
        "segment": "segment",
        "messaging_angle": "messaging_angle",
        "email_format": "email_format",
        "experiment_id": "experiment_id",
    }
    sort_col = sort_map[sort_by]
    direction = sort_order.value.upper()
    tie_breaker = "experiment_id DESC" if sort_col != "experiment_id" else f"created_at {direction}"
    rows = db.execute(
        f"SELECT * FROM experiments ORDER BY {sort_col} {direction}, {tie_breaker} LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        item = row_to_dict(r)
        item["sent_count"] = db.execute(
            "SELECT COUNT(*) AS n FROM email_variants WHERE experiment_id = ? AND delivery_status = 'sent'",
            (item["experiment_id"],),
        ).fetchone()["n"]
        out.append(item)
    return out


@router.get("/experiments/options")
def experiments_options(db=Db) -> dict:
    segments = [
        r["segment"]
        for r in db.execute("SELECT DISTINCT segment FROM leads WHERE segment IS NOT NULL AND segment != '' ORDER BY segment").fetchall()
    ]
    messaging_angles = [
        r["messaging_angle"]
        for r in db.execute(
            "SELECT DISTINCT messaging_angle FROM experiments WHERE messaging_angle IS NOT NULL AND messaging_angle != '' ORDER BY messaging_angle"
        ).fetchall()
    ]
    email_formats = [
        r["email_format"]
        for r in db.execute(
            "SELECT DISTINCT email_format FROM experiments WHERE email_format IS NOT NULL AND email_format != '' ORDER BY email_format"
        ).fetchall()
    ]
    default_angles = ["quick_win_audit", "local_visibility", "technical_cleanup"]
    default_formats = ["short", "medium"]
    languages = [
        r["language"]
        for r in db.execute(
            "SELECT DISTINCT language FROM ab_test_variants WHERE language IS NOT NULL AND language != '' ORDER BY language"
        ).fetchall()
    ]
    default_languages = ["en", "fr", "nl", "de"]
    return {
        "segments": segments,
        "messaging_angles": list(dict.fromkeys(default_angles + messaging_angles)),
        "email_formats": list(dict.fromkeys(default_formats + email_formats)),
        "languages": list(dict.fromkeys(default_languages + languages)),
    }


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
