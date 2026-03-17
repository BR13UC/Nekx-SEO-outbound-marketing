from pydantic import BaseModel


class LeadCreate(BaseModel):
    company: str
    contact_email: str
    website: str
    segment: str
    industry: str | None = None
    country: str | None = None
    source: str | None = None
    status: str = "new"


class LeadUpdate(BaseModel):
    company: str | None = None
    contact_email: str | None = None
    website: str | None = None
    segment: str | None = None
    industry: str | None = None
    country: str | None = None
    source: str | None = None
    status: str | None = None


class LeadOut(BaseModel):
    lead_id: int
    company: str
    contact_email: str
    website: str
    segment: str
    industry: str | None = None
    country: str | None = None
    source: str | None = None
    created_at: str
    status: str
