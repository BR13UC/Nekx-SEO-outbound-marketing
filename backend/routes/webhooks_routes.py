from fastapi import APIRouter, HTTPException, Request
import logging

from ..database import Db, utcnow_iso
from ..domain_types import EmailEventType

logger = logging.getLogger(__name__)
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/email")
async def email_webhook(request: Request, db=Db) -> dict:
    # Resend envoie une structure JSON spécifique, on utilise donc Request directement
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

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