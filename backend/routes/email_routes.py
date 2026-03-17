from fastapi import APIRouter, HTTPException

from ..database import Db, row_to_dict, utcnow_iso
from ..schemas.email_schema import EmailGenerateIn, EmailOut, EmailSendIn
from ..services.email_service import render_email


router = APIRouter(tags=["emails"])


@router.post("/emails/generate", response_model=EmailOut)
def generate_email(body: EmailGenerateIn, db=Db):
    lead = db.execute("SELECT * FROM leads WHERE lead_id = ?", (body.lead_id,)).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")

    exp = db.execute("SELECT * FROM experiments WHERE experiment_id = ?", (body.experiment_id,)).fetchone()
    if not exp:
        raise HTTPException(status_code=404, detail="experiment not found")

    insights = db.execute(
        "SELECT * FROM seo_insights WHERE lead_id = ? ORDER BY severity DESC, created_at DESC LIMIT 3",
        (body.lead_id,),
    ).fetchall()

    subject, content = render_email(dict(lead), dict(exp), [dict(i) for i in insights])
    now = utcnow_iso()
    cur = db.execute(
        """
        INSERT INTO email_variants (lead_id, experiment_id, subject, content, created_at, sent_at)
        VALUES (?, ?, ?, ?, ?, NULL)
        """,
        (body.lead_id, body.experiment_id, subject, content, now),
    )
    db.commit()
    email_id = cur.lastrowid
    row = db.execute("SELECT * FROM email_variants WHERE email_id = ?", (email_id,)).fetchone()
    return row_to_dict(row)


@router.get("/emails/{email_id}", response_model=EmailOut)
def get_email(email_id: int, db=Db):
    row = db.execute("SELECT * FROM email_variants WHERE email_id = ?", (email_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="email not found")
    return row_to_dict(row)


@router.post("/emails/send")
def send_email(body: EmailSendIn, db=Db) -> dict:
    email = db.execute("SELECT * FROM email_variants WHERE email_id = ?", (body.email_id,)).fetchone()
    if not email:
        raise HTTPException(status_code=404, detail="email not found")

    now = utcnow_iso()
    db.execute("UPDATE email_variants SET sent_at = ? WHERE email_id = ?", (now, body.email_id))
    db.execute(
        "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, ?, ?, ?)",
        (body.email_id, "sent", None, now),
    )
    db.commit()

    # Provider integration (Resend) is intentionally stubbed for v0.
    return {"ok": True, "email_id": body.email_id, "sent_at": now}
