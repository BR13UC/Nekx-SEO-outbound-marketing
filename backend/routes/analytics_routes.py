import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Query

from ..config import settings
from ..database import Db, row_to_dict
from ..domain_types import SortOrder


router = APIRouter(tags=["analytics"])


def _choose_next_side(written_a: int, written_b: int, max_a: int, max_b: int) -> str | None:
    a_available = written_a < max_a
    b_available = written_b < max_b
    if not a_available and not b_available:
        return None
    if a_available and not b_available:
        return "A"
    if b_available and not a_available:
        return "B"
    return "A" if written_a <= written_b else "B"


def _build_ab_queue(db, limit: int) -> list[dict]:
    tests = db.execute(
        "SELECT * FROM ab_tests WHERE active = 1 ORDER BY created_at ASC, ab_test_id ASC"
    ).fetchall()
    if not tests:
        return []

    test_ids = [int(t["ab_test_id"]) for t in tests]
    placeholders = ",".join("?" for _ in test_ids)
    variants_rows = db.execute(
        f"SELECT * FROM ab_test_variants WHERE ab_test_id IN ({placeholders})",
        tuple(test_ids),
    ).fetchall()
    variants_by_test: dict[int, dict[str, dict]] = defaultdict(dict)
    for row in variants_rows:
        variants_by_test[int(row["ab_test_id"])][str(row["side"])] = row_to_dict(row)

    counts_rows = db.execute(
        f"""
        SELECT
          ab_test_id,
          COUNT(*) AS written_total,
          SUM(CASE WHEN ab_side = 'A' THEN 1 ELSE 0 END) AS written_a,
          SUM(CASE WHEN ab_side = 'B' THEN 1 ELSE 0 END) AS written_b
        FROM email_variants
        WHERE ab_test_id IN ({placeholders})
        GROUP BY ab_test_id
        """,
        tuple(test_ids),
    ).fetchall()
    counts = {
        int(r["ab_test_id"]): {
            "written_total": int(r["written_total"] or 0),
            "written_a": int(r["written_a"] or 0),
            "written_b": int(r["written_b"] or 0),
        }
        for r in counts_rows
    }

    eligible_leads = db.execute(
        """
        SELECT
          l.lead_id,
          l.company,
          l.contact_email,
          l.segment,
          COALESCE(l.country, '') AS country,
          l.created_at
        FROM leads l
        WHERE l.status = 'new'
          AND NOT EXISTS (
            SELECT 1
            FROM email_variants ev
            WHERE ev.lead_id = l.lead_id
              AND ev.delivery_status IN ('ready', 'sent')
          )
        ORDER BY l.created_at ASC, l.lead_id ASC
        """
    ).fetchall()
    leads_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for l in eligible_leads:
        item = row_to_dict(l)
        leads_by_key[(str(item["segment"]), str(item["country"]))].append(item)

    queue: list[dict] = []
    reserved_lead_ids: set[int] = set()
    while len(queue) < limit:
        chosen = None
        for t in tests:
            test = row_to_dict(t)
            tid = int(test["ab_test_id"])
            if tid not in variants_by_test or "A" not in variants_by_test[tid] or "B" not in variants_by_test[tid]:
                continue
            c = counts.setdefault(tid, {"written_total": 0, "written_a": 0, "written_b": 0})
            if c["written_total"] >= int(test["max_emails_total"]):
                continue
            side = _choose_next_side(c["written_a"], c["written_b"], int(test["max_emails_a"]), int(test["max_emails_b"]))
            if not side:
                continue
            key = (str(test["segment"]), str(test["country"]))
            lead = next((ld for ld in leads_by_key.get(key, []) if int(ld["lead_id"]) not in reserved_lead_ids), None)
            if not lead:
                continue
            chosen = (test, side, lead, variants_by_test[tid][side], c)
            break

        if not chosen:
            break

        test, side, lead, variant, c = chosen
        reserved_lead_ids.add(int(lead["lead_id"]))
        c["written_total"] += 1
        if side == "A":
            c["written_a"] += 1
        else:
            c["written_b"] += 1
        queue.append(
            {
                "position": len(queue) + 1,
                "ab_test_id": int(test["ab_test_id"]),
                "ab_test_name": str(test["name"]),
                "segment": str(test["segment"]),
                "country": str(test["country"]),
                "lead_id": int(lead["lead_id"]),
                "company": str(lead["company"]),
                "contact_email": str(lead["contact_email"]),
                "side": side,
                "messaging_angle": str(variant["messaging_angle"]),
                "email_format": str(variant["email_format"]),
                "language": str(variant.get("language") or "en"),
            }
        )
    return queue


def _build_email_filters(
    segment: str | None,
    start_date: str | None,
    end_date: str | None,
    *,
    email_alias: str = "ev",
    lead_alias: str = "l",
) -> tuple[str, list[object]]:
    clauses = [f"{email_alias}.delivery_status = 'sent'"]
    args: list[object] = []

    if segment:
        clauses.append(f"{lead_alias}.segment = ?")
        args.append(segment)
    if start_date:
        clauses.append(f"substr(COALESCE({email_alias}.sent_at, {email_alias}.created_at), 1, 10) >= ?")
        args.append(start_date)
    if end_date:
        clauses.append(f"substr(COALESCE({email_alias}.sent_at, {email_alias}.created_at), 1, 10) <= ?")
        args.append(end_date)

    return " AND ".join(clauses), args


def _build_written_filters(
    segment: str | None,
    start_date: str | None,
    end_date: str | None,
    *,
    email_alias: str = "ev",
    lead_alias: str = "l",
) -> tuple[str, list[object]]:
    clauses = [f"{email_alias}.delivery_status IN ('ready','sent')"]
    args: list[object] = []

    if segment:
        clauses.append(f"{lead_alias}.segment = ?")
        args.append(segment)
    if start_date:
        clauses.append(f"substr({email_alias}.created_at, 1, 10) >= ?")
        args.append(start_date)
    if end_date:
        clauses.append(f"substr({email_alias}.created_at, 1, 10) <= ?")
        args.append(end_date)

    return " AND ".join(clauses), args


@router.get("/analytics/summary")
def analytics_summary(
    segment: str | None = Query(None),
    start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db=Db,
) -> dict:
    # Rates are still derived client-side.
    where_sql, args = _build_email_filters(segment, start_date, end_date, email_alias="ev", lead_alias="l")

    sent = db.execute(
        f"""
        SELECT COUNT(DISTINCT ev.email_id) AS n
        FROM email_variants ev
        JOIN leads l ON l.lead_id = ev.lead_id
        WHERE {where_sql}
        """,
        tuple(args),
    ).fetchone()["n"]

    opened = db.execute(
        f"""
        SELECT COUNT(DISTINCT ee.email_id) AS n
        FROM email_events ee
        JOIN email_variants ev ON ev.email_id = ee.email_id
        JOIN leads l ON l.lead_id = ev.lead_id
        WHERE ee.event_type = 'opened'
          AND {where_sql}
        """,
        tuple(args),
    ).fetchone()["n"]

    replied = db.execute(
        f"""
        SELECT COUNT(DISTINCT r.email_id) AS n
        FROM replies r
        JOIN email_variants ev ON ev.email_id = r.email_id
        JOIN leads l ON l.lead_id = ev.lead_id
        WHERE {where_sql}
        """,
        tuple(args),
    ).fetchone()["n"]

    written_where_sql, written_args = _build_written_filters(
        segment, start_date, end_date, email_alias="ev", lead_alias="l"
    )
    written_emails = db.execute(
        f"""
        SELECT COUNT(DISTINCT ev.email_id) AS n
        FROM email_variants ev
        JOIN leads l ON l.lead_id = ev.lead_id
        WHERE {written_where_sql}
        """,
        tuple(written_args),
    ).fetchone()["n"]

    return {"sent": sent, "opened": opened, "replied": replied, "written_emails": written_emails}


@router.get("/analytics/segments")
def analytics_segments(
    segment: str | None = Query(None),
    start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db=Db,
) -> list[dict]:
    where_sql, args = _build_email_filters(segment, start_date, end_date, email_alias="ev", lead_alias="l")
    rows = db.execute(
        f"""
        SELECT
          l.segment AS segment,
          COUNT(DISTINCT ev.email_id) AS sent,
          COUNT(DISTINCT CASE WHEN ee.event_type='opened' THEN ev.email_id END) AS opened,
          COUNT(DISTINCT r.email_id) AS replied
        FROM leads l
        LEFT JOIN email_variants ev ON ev.lead_id = l.lead_id AND ev.delivery_status = 'sent'
        LEFT JOIN email_events ee ON ee.email_id = ev.email_id
        LEFT JOIN replies r ON r.email_id = ev.email_id
        WHERE {where_sql}
        GROUP BY l.segment
        ORDER BY sent DESC
        """,
        tuple(args),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/analytics/messaging")
def analytics_messaging(db=Db) -> list[dict]:
    rows = db.execute(
        """
        SELECT
          e.messaging_angle AS messaging_angle,
          COUNT(DISTINCT ev.email_id) AS sent,
          COUNT(DISTINCT CASE WHEN ee.event_type='opened' THEN ev.email_id END) AS opened,
          COUNT(DISTINCT r.email_id) AS replied
        FROM experiments e
        LEFT JOIN email_variants ev ON ev.experiment_id = e.experiment_id AND ev.delivery_status = 'sent'
        LEFT JOIN email_events ee ON ee.email_id = ev.email_id
        LEFT JOIN replies r ON r.email_id = ev.email_id
        GROUP BY e.messaging_angle
        ORDER BY sent DESC
        """
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/analytics/recent-emails")
def analytics_recent_emails(
    limit: int = Query(12, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("sent_at", pattern="^(sent_at|company|segment)$"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    segment: str | None = Query(None),
    start_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end_date: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db=Db,
) -> list[dict]:
    where_sql, args = _build_email_filters(segment, start_date, end_date, email_alias="ev", lead_alias="l")
    sort_map = {
        "sent_at": "COALESCE(ev.sent_at, ev.created_at)",
        "company": "l.company",
        "segment": "l.segment",
    }
    sort_col = sort_map[sort_by]
    direction = sort_order.value.upper()
    tie_breaker = "ev.email_id DESC"
    rows = db.execute(
        f"""
        SELECT
          ev.email_id,
          ev.subject,
          ev.sent_at,
          ev.delivery_status,
          l.company,
          l.contact_email,
          l.segment,
          e.messaging_angle,
          e.email_format
        FROM email_variants ev
        JOIN leads l ON l.lead_id = ev.lead_id
        LEFT JOIN experiments e ON e.experiment_id = ev.experiment_id
        WHERE {where_sql}
        ORDER BY {sort_col} {direction}, {tie_breaker}
        LIMIT ? OFFSET ?
        """,
        tuple(args + [limit, offset]),
    ).fetchall()
    return [row_to_dict(r) for r in rows]


@router.get("/analytics/queue")
def analytics_queue(limit: int = Query(15, ge=1, le=100), db=Db) -> list[dict]:
    return _build_ab_queue(db, limit)


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_json_payload(line: str) -> dict | None:
    # Scheduler log format: TIMESTAMP | LEVEL | {"event":"..."}
    if "|" not in line:
        return None
    parts = line.split("|", 2)
    if len(parts) != 3:
        return None
    payload = parts[2].strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict):
        return data
    return None


@router.get("/analytics/cron-status")
def analytics_cron_status(db=Db) -> dict:
    config_path = Path(settings.scheduler_config_path)
    config = {
        "enabled": True,
        "min_interval_minutes": 30,
        "log_file_path": "data/outbound_scheduler.log",
    }

    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config.update(loaded)
        except json.JSONDecodeError:
            pass

    log_path = Path(str(config.get("log_file_path") or "data/outbound_scheduler.log"))
    if not log_path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        log_path = (project_root / log_path).resolve()

    last_event: dict | None = None
    last_heartbeat: str | None = None
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in reversed(lines[-400:]):
                payload = _extract_json_payload(line)
                if not payload:
                    continue
                stamp = line.split("|", 1)[0].strip()
                if last_event is None:
                    last_event = {
                        "timestamp": stamp,
                        "event": payload.get("event"),
                        "detail": payload,
                    }
                if payload.get("event") == "start" and last_heartbeat is None:
                    last_heartbeat = stamp
                if last_event is not None and last_heartbeat is not None:
                    break
        except OSError:
            last_event = None

    min_interval_raw = config.get("min_interval_minutes", 30)
    try:
        min_interval_minutes = max(0, int(min_interval_raw))
    except (TypeError, ValueError):
        min_interval_minutes = 30

    last_sent = db.execute(
        "SELECT MAX(sent_at) AS last_sent_at FROM email_variants WHERE delivery_status = 'sent' AND sent_at IS NOT NULL"
    ).fetchone()
    last_sent_at = last_sent["last_sent_at"] if last_sent else None

    now = datetime.now(timezone.utc)
    enabled = bool(config.get("enabled", True))
    next_planned_heartbeat: str | None = None
    due_now = False
    if enabled:
        if last_heartbeat:
            heartbeat_dt = _parse_iso_datetime(last_heartbeat)
            if min_interval_minutes <= 0:
                next_dt = now
            else:
                next_dt = heartbeat_dt + timedelta(minutes=min_interval_minutes)
                while next_dt <= now:
                    next_dt = next_dt + timedelta(minutes=min_interval_minutes)
            next_planned_heartbeat = next_dt.isoformat()
        else:
            due_now = True
            next_planned_heartbeat = now.isoformat()

    if not enabled:
        status = "paused"
    elif not last_heartbeat:
        status = "waiting"
    else:
        heartbeat_dt = _parse_iso_datetime(last_heartbeat)
        stale_grace = timedelta(minutes=max(2, min_interval_minutes + 2))
        if heartbeat_dt + stale_grace < now:
            status = "error"
        else:
            status = "waiting"
            if last_event and last_event.get("event") == "start":
                stamp = str(last_event.get("timestamp") or "")
                if stamp:
                    try:
                        last_start = _parse_iso_datetime(stamp)
                        if now - last_start <= timedelta(seconds=20):
                            status = "running"
                    except Exception:
                        pass

    return {
        "status": status,
        "enabled": enabled,
        "min_interval_minutes": min_interval_minutes,
        "log_file_path": str(log_path),
        "log_exists": log_path.exists(),
        "last_event": last_event,
        "last_heartbeat": last_heartbeat,
        "last_sent_at": last_sent_at,
        "next_planned_heartbeat": next_planned_heartbeat,
        # backward compatibility for existing clients
        "next_allowed_at": next_planned_heartbeat,
        "due_now": due_now,
    }


@router.get("/analytics/activity")
def analytics_activity(
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("event_time", pattern="^(event_time|event_type|company)$"),
    sort_order: SortOrder = Query(SortOrder.DESC),
    db=Db,
) -> dict:
    config_path = Path(settings.scheduler_config_path)
    config = {
        "enabled": True,
        "min_interval_minutes": 30,
        "log_file_path": "data/outbound_scheduler.log",
    }
    if config_path.exists():
        try:
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                config.update(loaded)
        except json.JSONDecodeError:
            pass

    log_path = Path(str(config.get("log_file_path") or "data/outbound_scheduler.log"))
    if not log_path.is_absolute():
        project_root = Path(__file__).resolve().parents[2]
        log_path = (project_root / log_path).resolve()

    scheduler_events_main_all: list[dict] = []
    scheduler_events_test_all: list[dict] = []
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            for line in reversed(lines[-1000:]):
                payload = _extract_json_payload(line)
                if not payload:
                    continue
                stamp = line.split("|", 1)[0].strip()
                item = {
                    "timestamp": stamp,
                    "event": payload.get("event"),
                    "detail": payload,
                }
                if payload.get("mode") == "test":
                    scheduler_events_test_all.append(item)
                else:
                    scheduler_events_main_all.append(item)
                if len(scheduler_events_main_all) >= (offset + limit) and len(scheduler_events_test_all) >= (offset + limit):
                    break
        except OSError:
            scheduler_events_main_all = []
            scheduler_events_test_all = []

    scheduler_events_main = scheduler_events_main_all[offset : offset + limit]
    scheduler_events_test = scheduler_events_test_all[offset : offset + limit]

    sort_map = {
        "event_time": "ee.event_time",
        "event_type": "ee.event_type",
        "company": "l.company",
    }
    sort_col = sort_map[sort_by]
    direction = sort_order.value.upper()

    email_events = db.execute(
        f"""
        SELECT
          ee.event_id,
          ee.email_id,
          ee.event_type,
          ee.event_time,
          ee.provider_id,
          l.lead_id,
          l.company,
          l.contact_email,
          l.segment
        FROM email_events ee
        JOIN email_variants ev ON ev.email_id = ee.email_id
        JOIN leads l ON l.lead_id = ev.lead_id
        ORDER BY {sort_col} {direction}, ee.event_id DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()

    return {
        "scheduler_events_main": scheduler_events_main,
        "scheduler_events_test": scheduler_events_test,
        "email_events": [row_to_dict(r) for r in email_events],
    }
