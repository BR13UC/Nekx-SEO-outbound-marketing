from fastapi import APIRouter, HTTPException

from ..database import Db, row_to_dict, utcnow_iso
from ..schemas.seo_schema import SeoAnalyzeIn, SeoInsightOut
from ..services.seo_service import analyze_lead_opportunities


router = APIRouter(tags=["seo"])


@router.post("/seo/analyze", response_model=list[SeoInsightOut])
def seo_analyze(body: SeoAnalyzeIn, db=Db):
    lead = db.execute("SELECT * FROM leads WHERE lead_id = ?", (body.lead_id,)).fetchone()
    if not lead:
        raise HTTPException(status_code=404, detail="lead not found")

    website = body.website or lead["website"]
    insights = analyze_lead_opportunities(dict(lead), website=website)

    now = utcnow_iso()
    created: list[dict] = []
    for insight in insights:
        cur = db.execute(
            """
            INSERT INTO seo_insights (lead_id, issue_type, issue_description, severity, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (body.lead_id, insight["issue_type"], insight["issue_description"], insight["severity"], now),
        )
        row = db.execute("SELECT * FROM seo_insights WHERE insight_id = ?", (cur.lastrowid,)).fetchone()
        created.append(row_to_dict(row))

    db.commit()
    return created


@router.get("/seo/{lead_id}", response_model=list[SeoInsightOut])
def get_seo_insights(lead_id: int, db=Db):
    rows = db.execute(
        "SELECT * FROM seo_insights WHERE lead_id = ? ORDER BY severity DESC, created_at DESC",
        (lead_id,),
    ).fetchall()
    return [row_to_dict(row) for row in rows]
