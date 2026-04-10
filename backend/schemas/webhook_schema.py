from datetime import datetime
from pydantic import BaseModel, field_validator

from ..domain_types import EmailEventType, normalize_text


class EmailEventIn(BaseModel):
    email_id: int
    event_type: EmailEventType
    provider_id: str | None = None
    event_time: datetime | None = None
    reply_text: str | None = None
    sentiment: str | None = None

    @field_validator("provider_id", "reply_text", "sentiment", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_text(str(value))

    @field_validator("provider_id")
    @classmethod
    def _sent_requires_provider_id(cls, value: str | None, info):
        event_type = info.data.get("event_type")
        if event_type == EmailEventType.SENT and not value:
            raise ValueError("provider_id is required when event_type='sent'")
        return value
