from datetime import datetime
from pydantic import BaseModel


class EmailEventIn(BaseModel):
    email_id: int
    event_type: str
    provider_id: str | None = None
    event_time: datetime | None = None
    reply_text: str | None = None
    sentiment: str | None = None
