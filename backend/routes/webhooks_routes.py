from fastapi import APIRouter, HTTPException

from ..database import Db, utcnow_iso
from ..domain_types import (
    DeliveryStatus,
    EmailEventType,
    LeadStatus,
    can_transition_delivery_status,
    can_transition_lead_status,
)
from ..schemas.webhook_schema import EmailEventIn


router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/email")
def email_webhook(body: EmailEventIn, db=Db) -> dict:
    email = db.execute("SELECT * FROM email_variants WHERE email_id = ?", (body.email_id,)).fetchone()
    if not email:
        raise HTTPException(status_code=404, detail="email not found")

    event_type = body.event_type.value
    current_status = str(email["delivery_status"] or "")
    if event_type == EmailEventType.READY.value and not can_transition_delivery_status(
        current_status, DeliveryStatus.READY.value
    ):
        raise HTTPException(status_code=409, detail=f"invalid delivery transition: {current_status} -> ready")

    if event_type == EmailEventType.SENT.value and not can_transition_delivery_status(
        current_status, DeliveryStatus.SENT.value
    ):
        raise HTTPException(status_code=409, detail=f"invalid delivery transition: {current_status} -> sent")

    event_time = body.event_time.isoformat() if body.event_time else utcnow_iso()
    db.execute(
        "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, ?, ?, ?)",
        (body.email_id, event_type, body.provider_id, event_time),
    )

    if event_type == EmailEventType.SENT.value:
        db.execute(
            "UPDATE email_variants SET delivery_status = ?, sent_at = ? WHERE email_id = ?",
            (DeliveryStatus.SENT.value, event_time, body.email_id),
        )
        lead = db.execute("SELECT status FROM leads WHERE lead_id = ?", (email["lead_id"],)).fetchone()
        if lead:
            current_lead_status = str(lead["status"] or "")
            if (
                can_transition_lead_status(current_lead_status, LeadStatus.CONTACTED.value)
                and current_lead_status != LeadStatus.CONTACTED.value
            ):
                db.execute(
                    "UPDATE leads SET status = ? WHERE lead_id = ?",
                    (LeadStatus.CONTACTED.value, email["lead_id"]),
                )

    if event_type == EmailEventType.REPLIED.value and body.reply_text:
        db.execute(
            """
            INSERT INTO replies (email_id, lead_id, reply_text, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (body.email_id, email["lead_id"], body.reply_text, body.sentiment, utcnow_iso()),
        )

    db.commit()
    return {"ok": True}
