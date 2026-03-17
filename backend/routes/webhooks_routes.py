from fastapi import APIRouter, HTTPException

from ..database import Db, utcnow_iso
from ..schemas.webhook_schema import EmailEventIn


router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/email")
def email_webhook(body: EmailEventIn, db=Db) -> dict:
    email = db.execute("SELECT * FROM email_variants WHERE email_id = ?", (body.email_id,)).fetchone()
    if not email:
        raise HTTPException(status_code=404, detail="email not found")

    event_time = body.event_time.isoformat() if body.event_time else utcnow_iso()
    db.execute(
        "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, ?, ?, ?)",
        (body.email_id, body.event_type, body.provider_id, event_time),
    )

    if body.event_type == "replied" and body.reply_text:
        db.execute(
            """
            INSERT INTO replies (email_id, lead_id, reply_text, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (body.email_id, email["lead_id"], body.reply_text, body.sentiment, utcnow_iso()),
        )

    db.commit()
    return {"ok": True}
