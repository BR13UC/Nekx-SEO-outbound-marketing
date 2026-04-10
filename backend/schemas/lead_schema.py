from pydantic import AnyHttpUrl, BaseModel, EmailStr, field_validator

from ..domain_types import LeadStatus, normalize_email, normalize_website


class LeadCreate(BaseModel):
    company: str
    contact_email: EmailStr
    website: AnyHttpUrl
    segment: str
    industry: str | None = None
    country: str | None = None
    source: str | None = None
    status: LeadStatus = LeadStatus.NEW

    @field_validator("company", "segment", "industry", "country", "source", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("contact_email", mode="after")
    @classmethod
    def _normalize_contact_email(cls, value: EmailStr) -> str:
        return normalize_email(str(value))

    @field_validator("website", mode="after")
    @classmethod
    def _normalize_website(cls, value: AnyHttpUrl) -> str:
        return normalize_website(str(value))


class LeadUpdate(BaseModel):
    company: str | None = None
    contact_email: EmailStr | None = None
    website: AnyHttpUrl | None = None
    segment: str | None = None
    industry: str | None = None
    country: str | None = None
    source: str | None = None
    status: LeadStatus | None = None

    @field_validator("company", "segment", "industry", "country", "source", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("contact_email", mode="after")
    @classmethod
    def _normalize_contact_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return normalize_email(str(value))

    @field_validator("website", mode="after")
    @classmethod
    def _normalize_website(cls, value: AnyHttpUrl | None) -> str | None:
        if value is None:
            return None
        return normalize_website(str(value))


class LeadOut(BaseModel):
    lead_id: int
    company: str
    contact_email: EmailStr
    website: AnyHttpUrl
    segment: str
    industry: str | None = None
    country: str | None = None
    source: str | None = None
    created_at: str
    status: LeadStatus
