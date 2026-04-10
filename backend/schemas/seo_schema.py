from pydantic import AnyHttpUrl, BaseModel, field_validator

from ..domain_types import normalize_website


class SeoAnalyzeIn(BaseModel):
    lead_id: int
    website: AnyHttpUrl | None = None

    @field_validator("website", mode="after")
    @classmethod
    def _normalize_website(cls, value: AnyHttpUrl | None) -> str | None:
        if value is None:
            return None
        return normalize_website(str(value))


class SeoInsightOut(BaseModel):
    insight_id: int
    lead_id: int
    issue_type: str
    issue_description: str
    severity: int
    created_at: str
