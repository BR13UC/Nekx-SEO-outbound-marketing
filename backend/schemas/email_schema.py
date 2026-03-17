from pydantic import BaseModel


class EmailGenerateIn(BaseModel):
    lead_id: int
    experiment_id: int


class EmailSendIn(BaseModel):
    email_id: int


class EmailOut(BaseModel):
    email_id: int
    lead_id: int
    experiment_id: int
    subject: str
    content: str
    created_at: str
    sent_at: str | None = None
