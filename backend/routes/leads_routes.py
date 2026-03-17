from fastapi import APIRouter, HTTPException, Query

from ..database import Db, row_to_dict, utcnow_iso
from ..schemas.lead_schema import LeadCreate, LeadOut, LeadUpdate


router = APIRouter(tags=["leads"])


@router.post("/leads", response_model=LeadOut)
def create_lead(body: LeadCreate, db=Db):
    now = utcnow_iso()
    cur = db.execute(
        """
        INSERT INTO leads (company, contact_email, website, segment, industry, country, source, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.company,
            body.contact_email,
            body.website,
            body.segment,
            body.industry,
            body.country,
            body.source,
            now,
            body.status,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM leads WHERE lead_id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    segment: str | None = None,
    industry: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db=Db,
):
    where = []
    args: list[object] = []
    if segment:
        where.append("segment = ?")
        args.append(segment)
    if industry:
        where.append("industry = ?")
        args.append(industry)
    if status:
        where.append("status = ?")
        args.append(status)
    sql = "SELECT * FROM leads"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    rows = db.execute(sql, tuple(args)).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db=Db):
    row = db.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="lead not found")
    return row_to_dict(row)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, body: LeadUpdate, db=Db):
    existing = db.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="lead not found")

    patch = body.model_dump(exclude_unset=True)
    if not patch:
        return row_to_dict(existing)

    cols = ", ".join([f"{k} = ?" for k in patch.keys()])
    args = list(patch.values()) + [lead_id]
    db.execute(f"UPDATE leads SET {cols} WHERE lead_id = ?", tuple(args))
    db.commit()
    row = db.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
    return row_to_dict(row)
