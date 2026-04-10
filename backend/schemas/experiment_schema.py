from pydantic import BaseModel, Field

from ..domain_types import EmailFormat


class ExperimentCreate(BaseModel):
    segment: str
    messaging_angle: str
    email_format: EmailFormat
    max_emails_total: int | None = Field(default=None, ge=0)
    subject_variant: str | None = None
    active: bool = True


class ExperimentOut(BaseModel):
    experiment_id: int
    segment: str
    messaging_angle: str
    email_format: EmailFormat
    max_emails_total: int | None = None
    subject_variant: str | None = None
    created_at: str
    active: int
    sent_count: int | None = None
