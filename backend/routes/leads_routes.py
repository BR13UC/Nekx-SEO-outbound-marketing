import sqlite3

from fastapi import APIRouter, HTTPException, Query

from ..database import Db, row_to_dict, utcnow_iso
from ..domain_types import LeadStatus, SortOrder, can_transition_lead_status
from ..schemas.lead_schema import LeadCreate, LeadOut, LeadUpdate


router = APIRouter(tags=["leads"])


@router.post("/leads", response_model=LeadOut)
def create_lead(body: LeadCreate, db=Db):
    now = utcnow_iso()
    try:
        cur = db.execute(
            """
            INSERT INTO leads (company, contact_email, website, segment, industry, country, source, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.company,
                str(body.contact_email),
                str(body.website),
                body.segment,
                body.industry,
                body.country,
                body.source,
                now,
                body.status.value,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="lead already exists for this contact_email + website") from exc
    row = db.execute("SELECT * FROM leads WHERE lead_id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    segment: str | None = None,
    industry: str | None = None,
    status: LeadStatus | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", pattern="^(created_at|company|segment|status|lead_id)$"),
    sort_order: SortOrder = Query(SortOrder.DESC),
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
        args.append(status.value)
    sql = "SELECT * FROM leads"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sort_map = {
        "created_at": "created_at",
        "company": "company",
        "segment": "segment",
        "status": "status",
        "lead_id": "lead_id",
    }
    sort_col = sort_map[sort_by]
    direction = sort_order.value.upper()
    tie_breaker = "lead_id DESC" if sort_col != "lead_id" else f"created_at {direction}"
    sql += f" ORDER BY {sort_col} {direction}, {tie_breaker} LIMIT ? OFFSET ?"
    args.extend([limit, offset])
    rows = db.execute(sql, tuple(args)).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/leads/segments")
def list_lead_segments(db=Db) -> list[str]:
    rows = db.execute(
        """
        SELECT DISTINCT segment
        FROM leads
        WHERE segment IS NOT NULL AND segment != ''
        ORDER BY segment ASC
        """
    ).fetchall()
    return [str(r["segment"]) for r in rows]


@router.get("/leads/sources")
def list_lead_sources(db=Db) -> list[str]:
    rows = db.execute(
        """
        SELECT DISTINCT source
        FROM leads
        WHERE source IS NOT NULL AND source != ''
        ORDER BY source ASC
        """
    ).fetchall()
    return [str(r["source"]) for r in rows]


@router.get("/leads/countries")
def list_lead_countries(db=Db) -> list[str]:
    rows = db.execute(
        """
        SELECT DISTINCT country
        FROM leads
        WHERE country IS NOT NULL AND country != ''
        ORDER BY country ASC
        """
    ).fetchall()
    return [str(r["country"]) for r in rows]


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

    if "status" in patch:
        next_status = patch["status"].value
        current_status = str(existing["status"])
        if not can_transition_lead_status(current_status, next_status):
            raise HTTPException(status_code=409, detail=f"invalid lead status transition: {current_status} -> {next_status}")
        patch["status"] = next_status

    if "contact_email" in patch and patch["contact_email"] is not None:
        patch["contact_email"] = str(patch["contact_email"])
    if "website" in patch and patch["website"] is not None:
        patch["website"] = str(patch["website"])

    cols = ", ".join([f"{k} = ?" for k in patch.keys()])
    args = list(patch.values()) + [lead_id]
    try:
        db.execute(f"UPDATE leads SET {cols} WHERE lead_id = ?", tuple(args))
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="lead already exists for this contact_email + website") from exc
    row = db.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,)).fetchone()
    return row_to_dict(row)
