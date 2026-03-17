from fastapi import APIRouter

from ..database import Db, row_to_dict


router = APIRouter(tags=["analytics"])


@router.get("/analytics/summary")
def analytics_summary(db=Db) -> dict:
    # Lightweight v0: compute counts; rates can be derived client-side.
    sent = db.execute("SELECT COUNT(*) AS n FROM email_variants WHERE sent_at IS NOT NULL").fetchone()["n"]
    opened = db.execute(
        "SELECT COUNT(DISTINCT email_id) AS n FROM email_events WHERE event_type = 'opened'"
    ).fetchone()["n"]
    replied = db.execute("SELECT COUNT(DISTINCT email_id) AS n FROM replies").fetchone()["n"]
    return {"sent": sent, "opened": opened, "replied": replied}


@router.get("/analytics/segments")
def analytics_segments(db=Db) -> list[dict]:
    rows = db.execute(
        """
        SELECT
          l.segment AS segment,
          COUNT(DISTINCT ev.email_id) AS sent,
          COUNT(DISTINCT CASE WHEN ee.event_type='opened' THEN ev.email_id END) AS opened,
          COUNT(DISTINCT r.email_id) AS replied
        FROM leads l
        LEFT JOIN email_variants ev ON ev.lead_id = l.lead_id AND ev.sent_at IS NOT NULL
        LEFT JOIN email_events ee ON ee.email_id = ev.email_id
        LEFT JOIN replies r ON r.email_id = ev.email_id
        GROUP BY l.segment
        ORDER BY sent DESC
        """
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/analytics/messaging")
def analytics_messaging(db=Db) -> list[dict]:
    rows = db.execute(
        """
        SELECT
          e.messaging_angle AS messaging_angle,
          COUNT(DISTINCT ev.email_id) AS sent,
          COUNT(DISTINCT CASE WHEN ee.event_type='opened' THEN ev.email_id END) AS opened,
          COUNT(DISTINCT r.email_id) AS replied
        FROM experiments e
        LEFT JOIN email_variants ev ON ev.experiment_id = e.experiment_id AND ev.sent_at IS NOT NULL
        LEFT JOIN email_events ee ON ee.email_id = ev.email_id
        LEFT JOIN replies r ON r.email_id = ev.email_id
        GROUP BY e.messaging_angle
        ORDER BY sent DESC
        """
    ).fetchall()
    return [row_to_dict(r) for r in rows]
