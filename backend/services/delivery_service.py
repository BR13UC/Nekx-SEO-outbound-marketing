from __future__ import annotations

import logging
import os
from typing import Any

import resend

logger = logging.getLogger(__name__)


def send_email_via_resend(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    from_email: str | None = None,
    reply_to: str | None = None,
    tags: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("RESEND_API_KEY")
    sender = from_email or os.getenv("RESEND_FROM_EMAIL") or os.getenv("NEKX_FROM_EMAIL")
    if not api_key:
        return {"success": False, "error": "RESEND_API_KEY is missing", "provider_id": None}
    if not sender:
        return {"success": False, "error": "RESEND_FROM_EMAIL or NEKX_FROM_EMAIL is missing", "provider_id": None}

    resend.api_key = api_key
    params: resend.Emails.SendParams = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }
    if reply_to:
        params["reply_to"] = reply_to
    if tags:
        params["tags"] = tags

    try:
        response = resend.Emails.send(params)
    except Exception as exc:
        logger.error("Error during Resend delivery: %s", exc)
        return {"success": False, "error": str(exc), "provider_id": None}

    provider_id = _extract_provider_id(response)
    if not provider_id:
        return {"success": False, "error": f"Resend response did not include an id: {response!r}", "provider_id": None}

    logger.info("Email sent successfully: %s", provider_id)
    return {"success": True, "error": None, "provider_id": provider_id, "response": response}


def _extract_provider_id(response: Any) -> str | None:
    if isinstance(response, dict):
        value = response.get("id")
        return str(value) if value else None

    value = getattr(response, "id", None)
    if value:
        return str(value)

    model_dump = getattr(response, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict) and dumped.get("id"):
            return str(dumped["id"])

    return None
