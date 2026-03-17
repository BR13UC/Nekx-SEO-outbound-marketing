from pydantic import BaseModel


class SeoAnalyzeIn(BaseModel):
    lead_id: int
    website: str | None = None


class SeoInsightOut(BaseModel):
    insight_id: int
    lead_id: int
    issue_type: str
    issue_description: str
    severity: int
    created_at: str
