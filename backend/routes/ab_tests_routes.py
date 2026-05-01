import json

from fastapi import APIRouter, HTTPException, Query

from ..database import Db, row_to_dict, utcnow_iso
from ..domain_types import SortOrder
from ..schemas.ab_test_schema import AbResultsOut, AbTestCreate, AbTestOut


router = APIRouter(tags=["ab-tests"])


def _compute_results(db, ab_test_id: int) -> dict:
    counts = {}
    for side in ("A", "B"):
        written = db.execute(
            "SELECT COUNT(*) AS n FROM email_variants WHERE ab_test_id = ? AND ab_side = ?",
            (ab_test_id, side),
        ).fetchone()["n"]
        sent = db.execute(
            "SELECT COUNT(*) AS n FROM email_variants WHERE ab_test_id = ? AND ab_side = ? AND delivery_status = 'sent'",
            (ab_test_id, side),
        ).fetchone()["n"]
        opened = db.execute(
            """
            SELECT COUNT(DISTINCT ee.email_id) AS n
            FROM email_events ee
            JOIN email_variants ev ON ev.email_id = ee.email_id
            WHERE ev.ab_test_id = ? AND ev.ab_side = ? AND ee.event_type = 'opened'
            """,
            (ab_test_id, side),
        ).fetchone()["n"]
        replied = db.execute(
            """
            SELECT COUNT(DISTINCT r.email_id) AS n
            FROM replies r
            JOIN email_variants ev ON ev.email_id = r.email_id
            WHERE ev.ab_test_id = ? AND ev.ab_side = ?
            """,
            (ab_test_id, side),
        ).fetchone()["n"]
        counts[side] = {"written": written, "sent": sent, "opened": opened, "replied": replied}

    sent_a = counts["A"]["sent"]
    sent_b = counts["B"]["sent"]
    replied_a = counts["A"]["replied"]
    replied_b = counts["B"]["replied"]
    reply_rate_a = float(replied_a / sent_a) if sent_a else 0.0
    reply_rate_b = float(replied_b / sent_b) if sent_b else 0.0
    if sent_a == 0 or sent_b == 0:
        winner_side = "insufficient_data"
    elif abs(reply_rate_a - reply_rate_b) < 1e-12:
        winner_side = "tie"
    elif reply_rate_a > reply_rate_b:
        winner_side = "A"
    else:
        winner_side = "B"

    return {
        "ab_test_id": ab_test_id,
        "written_a": counts["A"]["written"],
        "written_b": counts["B"]["written"],
        "sent_a": sent_a,
        "sent_b": sent_b,
        "opened_a": counts["A"]["opened"],
        "opened_b": counts["B"]["opened"],
        "replied_a": replied_a,
        "replied_b": replied_b,
        "reply_rate_a": reply_rate_a,
        "reply_rate_b": reply_rate_b,
        "winner_side": winner_side,
    }


@router.post("/ab-tests", response_model=AbTestOut)
def create_ab_test(body: AbTestCreate, db=Db):
    now = utcnow_iso()
    cur = db.execute(
        """
        INSERT INTO ab_tests (
          name, segment, country, comparison_mode, max_emails_total, max_emails_a, max_emails_b,
          winner_metric, changed_dimensions, created_at, active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.name.strip(),
            body.segment.strip(),
            body.country.strip(),
            body.comparison_mode.strip(),
            body.max_emails_total,
            body.max_emails_a,
            body.max_emails_b,
            "reply_rate",
            json.dumps(body.changed_dimensions),
            now,
            1 if body.active else 0,
        ),
    )
    ab_test_id = int(cur.lastrowid)
    for side, variant in (("A", body.variant_a), ("B", body.variant_b)):
        db.execute(
            """
            INSERT INTO ab_test_variants (
              ab_test_id, side, messaging_angle, email_format, subject_variant, language, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ab_test_id,
                side,
                variant.messaging_angle,
                variant.email_format.value,
                variant.subject_variant,
                (variant.language or "en").strip() or "en",
                now,
            ),
        )
    db.commit()
    row = db.execute("SELECT * FROM ab_tests WHERE ab_test_id = ?", (ab_test_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="ab test creation failed")
    item = row_to_dict(row)
    item["changed_dimensions"] = json.loads(item["changed_dimensions"])
    metrics = _compute_results(db, ab_test_id)
    item.update(
        {
            "written_a": metrics["written_a"],
            "written_b": metrics["written_b"],
            "sent_a": metrics["sent_a"],
            "sent_b": metrics["sent_b"],
        }
    )
    return item


@router.get("/ab-tests", response_model=list[AbTestOut])
def list_ab_tests(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", pattern="^(created_at|segment|country|name|ab_test_id)$"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    db=Db,
):
    sort_map = {
        "created_at": "created_at",
        "segment": "segment",
        "country": "country",
        "name": "name",
        "ab_test_id": "ab_test_id",
    }
    sort_col = sort_map[sort_by]
    direction = sort_order.value.upper()
    tie_breaker = "ab_test_id DESC" if sort_col != "ab_test_id" else f"created_at {direction}"
    rows = db.execute(
        f"SELECT * FROM ab_tests ORDER BY {sort_col} {direction}, {tie_breaker} LIMIT ? OFFSET ?",
        (limit, offset),
    ).fetchall()
    out: list[dict] = []
    for r in rows:
        item = row_to_dict(r)
        item["changed_dimensions"] = json.loads(item["changed_dimensions"])
        metrics = _compute_results(db, int(item["ab_test_id"]))
        item.update(
            {
                "written_a": metrics["written_a"],
                "written_b": metrics["written_b"],
                "sent_a": metrics["sent_a"],
                "sent_b": metrics["sent_b"],
            }
        )
        out.append(item)
    return out


@router.get("/ab-tests/{ab_test_id}/results", response_model=AbResultsOut)
def get_ab_test_results(ab_test_id: int, db=Db):
    row = db.execute("SELECT ab_test_id FROM ab_tests WHERE ab_test_id = ?", (ab_test_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="ab test not found")
    return _compute_results(db, ab_test_id)


@router.get("/ab-tests/{ab_test_id}/details")
def get_ab_test_details(ab_test_id: int, db=Db) -> dict:
    row = db.execute("SELECT * FROM ab_tests WHERE ab_test_id = ?", (ab_test_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="ab test not found")

    ab_test = row_to_dict(row)
    ab_test["changed_dimensions"] = json.loads(ab_test["changed_dimensions"])
    variants = [
        row_to_dict(r)
        for r in db.execute(
            """
            SELECT *
            FROM ab_test_variants
            WHERE ab_test_id = ?
            ORDER BY CASE side WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END
            """,
            (ab_test_id,),
        ).fetchall()
    ]
    emails = [
        row_to_dict(r)
        for r in db.execute(
            """
            SELECT
              ev.email_id,
              ev.ab_side,
              ev.lead_id,
              l.company,
              l.contact_email,
              l.segment,
              ev.subject,
              ev.content,
              ev.delivery_status,
              ev.created_at,
              ev.sent_at,
              COUNT(DISTINCT ee.event_id) AS event_count,
              COUNT(DISTINCT replies.reply_id) AS reply_count
            FROM email_variants ev
            JOIN leads l ON l.lead_id = ev.lead_id
            LEFT JOIN email_events ee ON ee.email_id = ev.email_id
            LEFT JOIN replies ON replies.email_id = ev.email_id
            WHERE ev.ab_test_id = ?
            GROUP BY ev.email_id
            ORDER BY ev.created_at DESC, ev.email_id DESC
            """,
            (ab_test_id,),
        ).fetchall()
    ]
    return {"ab_test": ab_test, "variants": variants, "results": _compute_results(db, ab_test_id), "emails": emails}
