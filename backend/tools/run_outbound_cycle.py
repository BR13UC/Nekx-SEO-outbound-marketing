import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.database import connect, init_db, row_to_dict, utcnow_iso
from backend.services.email_service import render_email
from backend.services.seo_service import analyze_lead_opportunities


DEFAULT_CONFIG = {
    "enabled": True,
    "min_interval_minutes": 30,
    "log_level": "INFO",
    "log_file_path": "data/outbound_scheduler.log",
}


def _parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_scheduler_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(DEFAULT_CONFIG)

    with path.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    if not isinstance(raw, dict):
        raise ValueError("Scheduler config must be a JSON object.")

    cfg = dict(DEFAULT_CONFIG)
    cfg.update(raw)
    return cfg


class UtcFormatter(logging.Formatter):
    converter = time.gmtime


def setup_logger(config: dict[str, Any]) -> logging.Logger:
    logger = logging.getLogger("nekx.scheduler")
    logger.handlers.clear()
    logger.propagate = False

    level_name = str(config.get("log_level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)

    fmt = UtcFormatter("%(asctime)sZ | %(levelname)s | %(message)s", "%Y-%m-%dT%H:%M:%S")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    log_path = Path(str(config.get("log_file_path") or DEFAULT_CONFIG["log_file_path"])).expanduser()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    return logger


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    payload = {"event": event}
    payload.update(fields)
    logger.info(json.dumps(payload, ensure_ascii=True, sort_keys=True))


def select_next_lead(conn) -> dict[str, Any] | None:
    row = conn.execute(
        """
        WITH eligible AS (
          SELECT l.*
          FROM leads l
          WHERE l.status = 'new'
            AND NOT EXISTS (
              SELECT 1
              FROM email_variants ev
              JOIN email_events ee ON ee.email_id = ev.email_id
              WHERE ev.lead_id = l.lead_id
                AND ee.event_type = 'sent'
            )
        ),
        segment_last_sent AS (
          SELECT
            e.segment AS segment,
            MAX(ev.sent_at) AS last_sent_at
          FROM eligible e
          LEFT JOIN email_variants ev
            ON ev.lead_id = e.lead_id
            AND ev.sent_at IS NOT NULL
          GROUP BY e.segment
        ),
        chosen_segment AS (
          SELECT segment
          FROM segment_last_sent
          ORDER BY (last_sent_at IS NOT NULL), last_sent_at ASC, segment ASC
          LIMIT 1
        )
        SELECT e.*
        FROM eligible e
        JOIN chosen_segment c ON c.segment = e.segment
        ORDER BY e.created_at ASC, e.lead_id ASC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return row_to_dict(row)


def select_experiment(conn, segment: str) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT *
        FROM experiments
        WHERE active = 1 AND segment = ?
        ORDER BY created_at ASC, experiment_id ASC
        LIMIT 1
        """,
        (segment,),
    ).fetchone()
    if row:
        return row_to_dict(row)

    fallback = conn.execute(
        """
        SELECT *
        FROM experiments
        WHERE active = 1
        ORDER BY created_at ASC, experiment_id ASC
        LIMIT 1
        """
    ).fetchone()
    if not fallback:
        return None
    return row_to_dict(fallback)


def ensure_insights(conn, lead: dict[str, Any], now_iso: str, dry_run: bool) -> list[dict[str, Any]]:
    existing = conn.execute(
        """
        SELECT *
        FROM seo_insights
        WHERE lead_id = ?
        ORDER BY severity DESC, created_at DESC
        LIMIT 3
        """,
        (lead["lead_id"],),
    ).fetchall()
    if existing:
        return [row_to_dict(r) for r in existing]

    new_insights = analyze_lead_opportunities(lead, website=lead.get("website"))
    if dry_run:
        return new_insights

    created: list[dict[str, Any]] = []
    for insight in new_insights:
        cur = conn.execute(
            """
            INSERT INTO seo_insights (lead_id, issue_type, issue_description, severity, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                lead["lead_id"],
                insight["issue_type"],
                insight["issue_description"],
                insight["severity"],
                now_iso,
            ),
        )
        row = conn.execute("SELECT * FROM seo_insights WHERE insight_id = ?", (cur.lastrowid,)).fetchone()
        created.append(row_to_dict(row))
    return created


def interval_guard(conn, min_interval_minutes: int) -> tuple[bool, str | None]:
    last_sent = conn.execute(
        "SELECT MAX(sent_at) AS last_sent_at FROM email_variants WHERE sent_at IS NOT NULL"
    ).fetchone()
    last_sent_at = last_sent["last_sent_at"] if last_sent else None
    if not last_sent_at:
        return True, None

    last_dt = _parse_iso_datetime(last_sent_at)
    next_allowed = last_dt + timedelta(minutes=min_interval_minutes)
    now = datetime.now(timezone.utc)
    if now < next_allowed:
        return False, f"next_allowed_at={next_allowed.isoformat()}"
    return True, None


def run_cycle(dry_run: bool = False) -> int:
    config_path = Path(settings.scheduler_config_path)
    fallback_logger = setup_logger(DEFAULT_CONFIG)

    try:
        config = load_scheduler_config(config_path)
    except json.JSONDecodeError as exc:
        log_event(fallback_logger, "error", reason="invalid_json_config", detail=str(exc))
        return 2
    except Exception as exc:
        log_event(fallback_logger, "error", reason="invalid_scheduler_config", detail=str(exc))
        return 2

    logger = setup_logger(config)

    log_event(logger, "start", dry_run=dry_run, config_path=str(config_path))

    if not bool(config.get("enabled", True)):
        log_event(logger, "skip", reason="scheduler_disabled")
        return 0

    min_interval_raw = config.get("min_interval_minutes", DEFAULT_CONFIG["min_interval_minutes"])
    try:
        min_interval_minutes = max(0, int(min_interval_raw))
    except (TypeError, ValueError):
        log_event(logger, "error", reason="invalid_min_interval_minutes", value=min_interval_raw)
        return 2

    conn = connect()
    try:
        init_db(conn)

        if dry_run:
            log_event(logger, "throttle_bypassed", reason="dry_run")
        else:
            allowed, reason = interval_guard(conn, min_interval_minutes)
            if not allowed:
                log_event(logger, "skip", reason="interval_not_reached", detail=reason)
                return 0

        lead = select_next_lead(conn)
        if not lead:
            log_event(logger, "skip", reason="no_eligible_lead")
            return 0
        log_event(logger, "selected_lead", lead_id=lead["lead_id"], segment=lead["segment"])

        experiment = select_experiment(conn, lead["segment"])
        if not experiment:
            log_event(logger, "skip", reason="no_active_experiment")
            return 0
        log_event(logger, "selected_experiment", experiment_id=experiment["experiment_id"])

        now_iso = utcnow_iso()
        insights = ensure_insights(conn, lead, now_iso, dry_run=dry_run)
        log_event(logger, "insights_ready", count=len(insights))

        if dry_run:
            log_event(
                logger,
                "done",
                dry_run=True,
                lead_id=lead["lead_id"],
                experiment_id=experiment["experiment_id"],
            )
            return 0

        subject, content = render_email(lead, experiment, insights)
        cur = conn.execute(
            """
            INSERT INTO email_variants (lead_id, experiment_id, subject, content, created_at, sent_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (lead["lead_id"], experiment["experiment_id"], subject, content, now_iso, now_iso),
        )
        email_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO email_events (email_id, event_type, provider_id, event_time)
            VALUES (?, ?, ?, ?)
            """,
            (email_id, "sent", None, now_iso),
        )
        conn.execute("UPDATE leads SET status = ? WHERE lead_id = ?", ("contacted", lead["lead_id"]))
        conn.commit()

        log_event(
            logger,
            "generated_email",
            email_id=email_id,
            lead_id=lead["lead_id"],
            experiment_id=experiment["experiment_id"],
        )
        log_event(logger, "sent", email_id=email_id)
        log_event(logger, "done", email_id=email_id, lead_id=lead["lead_id"])
        return 0
    except Exception as exc:
        log_event(logger, "error", reason="unexpected_exception", detail=str(exc))
        return 1
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one outbound cycle for cron/manual usage (analyze -> generate -> send)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate selection/throttle logic and insights without writing email/event rows.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(run_cycle(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
