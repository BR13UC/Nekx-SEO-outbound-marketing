from pydantic import BaseModel


class ExperimentCreate(BaseModel):
    segment: str
    messaging_angle: str
    email_format: str
    subject_variant: str | None = None
    active: bool = True


class ExperimentOut(BaseModel):
    experiment_id: int
    segment: str
    messaging_angle: str
    email_format: str
    subject_variant: str | None = None
    created_at: str
    active: int
