from pydantic import BaseModel

from ..domain_types import DeliveryStatus


class EmailGenerateIn(BaseModel):
    lead_id: int
    experiment_id: int


class EmailSendIn(BaseModel):
    email_id: int


class EmailOut(BaseModel):
    email_id: int
    lead_id: int
    experiment_id: int | None = None
    subject: str
    content: str
    delivery_status: DeliveryStatus | None = None
    created_at: str
    sent_at: str | None = None
