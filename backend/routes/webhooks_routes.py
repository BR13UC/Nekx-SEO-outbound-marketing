import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from ..database import Db, utcnow_iso
from ..domain_types import DeliveryStatus, EmailEventType, LeadStatus, can_transition_delivery_status, can_transition_lead_status
from ..schemas.webhook_schema import EmailEventIn

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/email")
async def email_webhook(request: Request, db=Db) -> dict:
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if isinstance(payload, dict) and "email_id" in payload and "event_type" in payload:
        return _handle_manual_event(payload, db)

    event_type = payload.get("type")
    data = payload.get("data", {})
    provider_id = data.get("email_id")

    if not event_type or not provider_id:
        return {"ok": False, "detail": "Missing type or email_id in payload"}

    resend_mapping = {
        "email.delivered": "delivered",
        "email.opened": "opened",
        "email.clicked": "clicked",
        "email.bounced": "bounced",
        "email.complained": "complained"
    }

    internal_event = resend_mapping.get(event_type)
    if not internal_event:
        logger.info(f"Événement Resend ignoré : {event_type}")
        return {"ok": True, "detail": f"Event {event_type} ignored"}

    # Retrieve the email's internal ID using the provider_id
    event_row = db.execute(
        "SELECT email_id FROM email_events WHERE provider_id = ? LIMIT 1",
        (provider_id,)
    ).fetchone()

    if not event_row:
        logger.warning(f"Webhook reçu pour un provider_id inconnu : {provider_id}")
        return {"ok": True, "detail": "Unknown provider_id"}

    email_id = event_row["email_id"]
    event_time = payload.get("created_at") or utcnow_iso()

    db.execute(
        "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, ?, ?, ?)",
        (email_id, internal_event, provider_id, event_time),
    )

    db.commit()
    logger.info(f"Événement {internal_event} enregistré pour l'email_id {email_id}")
    
    return {"ok": True}


def _handle_manual_event(payload: dict, db) -> dict:
    try:
        body = EmailEventIn.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    email = db.execute("SELECT * FROM email_variants WHERE email_id = ?", (body.email_id,)).fetchone()
    if not email:
        raise HTTPException(status_code=404, detail="email not found")

    event_time = body.event_time.isoformat() if body.event_time else utcnow_iso()
    event_type = body.event_type.value

    if body.event_type == EmailEventType.SENT:
        current_status = str(email["delivery_status"] or "")
        if not can_transition_delivery_status(current_status, DeliveryStatus.SENT.value):
            raise HTTPException(status_code=409, detail=f"invalid email delivery status: {current_status or 'unknown'}")
        db.execute(
            "UPDATE email_variants SET delivery_status = ?, sent_at = ? WHERE email_id = ?",
            (DeliveryStatus.SENT.value, event_time, body.email_id),
        )
        lead = db.execute("SELECT * FROM leads WHERE lead_id = ?", (email["lead_id"],)).fetchone()
        if lead:
            current_lead_status = str(lead["status"] or "")
            if can_transition_lead_status(current_lead_status, LeadStatus.CONTACTED.value):
                db.execute(
                    "UPDATE leads SET status = ? WHERE lead_id = ?",
                    (LeadStatus.CONTACTED.value, lead["lead_id"]),
                )
    elif body.event_type == EmailEventType.READY:
        current_status = str(email["delivery_status"] or "")
        if not can_transition_delivery_status(current_status, DeliveryStatus.READY.value):
            raise HTTPException(status_code=409, detail=f"invalid email delivery status: {current_status or 'unknown'}")

    db.execute(
        "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, ?, ?, ?)",
        (body.email_id, event_type, body.provider_id, event_time),
    )

    if body.event_type == EmailEventType.REPLIED and body.reply_text:
        db.execute(
            """
            INSERT INTO replies (email_id, lead_id, reply_text, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (body.email_id, email["lead_id"], body.reply_text, body.sentiment, event_time),
        )

    db.commit()
    return {"ok": True}
