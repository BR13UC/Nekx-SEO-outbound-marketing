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
from backend.domain_types import LeadStatus, can_transition_lead_status
from backend.services.email_service import render_email
from backend.services.seo_service import analyze_lead_opportunities
from backend.services.delivery_service import send_email_via_resend


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


def select_active_ab_test(conn) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT t.*
        FROM ab_tests t
        WHERE t.active = 1
          AND (
            SELECT COUNT(*)
            FROM email_variants ev
            WHERE ev.ab_test_id = t.ab_test_id
          ) < t.max_emails_total
          AND EXISTS (
            SELECT 1
            FROM leads l
            WHERE l.status = 'new'
              AND l.segment = t.segment
              AND COALESCE(l.country, '') = t.country
              AND NOT EXISTS (
                SELECT 1
                FROM email_variants ev2
                WHERE ev2.lead_id = l.lead_id
                  AND ev2.delivery_status IN ('ready', 'sent')
              )
          )
        ORDER BY t.created_at ASC, t.ab_test_id ASC
        LIMIT 1
        """
    ).fetchone()
    if not row:
        return None
    return row_to_dict(row)


def select_next_lead_for_ab_test(conn, ab_test: dict[str, Any]) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT l.*
        FROM leads l
        WHERE l.status = 'new'
          AND l.segment = ?
          AND COALESCE(l.country, '') = ?
          AND NOT EXISTS (
            SELECT 1
            FROM email_variants ev
            WHERE ev.lead_id = l.lead_id
              AND ev.delivery_status IN ('ready', 'sent')
          )
        ORDER BY l.created_at ASC, l.lead_id ASC
        LIMIT 1
        """,
        (ab_test["segment"], ab_test["country"]),
    ).fetchone()
    if not row:
        return None
    return row_to_dict(row)


def select_ab_variant(conn, ab_test: dict[str, Any]) -> dict[str, Any] | None:
    ab_test_id = int(ab_test["ab_test_id"])
    variants = conn.execute(
        "SELECT * FROM ab_test_variants WHERE ab_test_id = ? ORDER BY side ASC",
        (ab_test_id,),
    ).fetchall()
    if len(variants) != 2:
        return None
    by_side = {r["side"]: row_to_dict(r) for r in variants}
    if "A" not in by_side or "B" not in by_side:
        return None

    written_a = conn.execute(
        "SELECT COUNT(*) AS n FROM email_variants WHERE ab_test_id = ? AND ab_side = 'A'",
        (ab_test_id,),
    ).fetchone()["n"]
    written_b = conn.execute(
        "SELECT COUNT(*) AS n FROM email_variants WHERE ab_test_id = ? AND ab_side = 'B'",
        (ab_test_id,),
    ).fetchone()["n"]

    max_a = int(ab_test["max_emails_a"])
    max_b = int(ab_test["max_emails_b"])
    a_available = written_a < max_a
    b_available = written_b < max_b

    if not a_available and not b_available:
        return None
    if a_available and not b_available:
        return by_side["A"]
    if b_available and not a_available:
        return by_side["B"]

    # Strict alternation with deterministic tie-breaker.
    if written_a <= written_b:
        return by_side["A"]
    return by_side["B"]


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
    last_activity = conn.execute(
        """
        SELECT MAX(created_at) AS last_activity_at
        FROM email_variants
        WHERE delivery_status = 'sent'
        """
    ).fetchone()
    last_activity_at = last_activity["last_activity_at"] if last_activity else None
    if not last_activity_at:
        return True, None

    last_dt = _parse_iso_datetime(last_activity_at)
    next_allowed = last_dt + timedelta(minutes=min_interval_minutes)
    now = datetime.now(timezone.utc)
    if now < next_allowed:
        return False, f"next_allowed_at={next_allowed.isoformat()}"
    return True, None


def run_cycle(dry_run: bool = False, mode: str = "live") -> int:
    mode = (mode or "live").strip().lower()
    if mode not in {"live", "test"}:
        mode = "live"
    effective_dry_run = dry_run or mode == "test"

    config_path = Path(settings.scheduler_config_path)
    fallback_logger = setup_logger(DEFAULT_CONFIG)

    try:
        config = load_scheduler_config(config_path)
    except json.JSONDecodeError as exc:
        log_event(fallback_logger, "error", reason="invalid_json_config", detail=str(exc), mode=mode)
        return 2
    except Exception as exc:
        log_event(fallback_logger, "error", reason="invalid_scheduler_config", detail=str(exc), mode=mode)
        return 2

    logger = setup_logger(config)
    log = lambda event, **fields: log_event(logger, event, mode=mode, dry_run=effective_dry_run, **fields)

    log("start", config_path=str(config_path))

    if not bool(config.get("enabled", True)):
        log("skip", reason="scheduler_disabled")
        return 0

    min_interval_raw = config.get("min_interval_minutes", DEFAULT_CONFIG["min_interval_minutes"])
    try:
        min_interval_minutes = max(0, int(min_interval_raw))
    except (TypeError, ValueError):
        log("error", reason="invalid_min_interval_minutes", value=min_interval_raw)
        return 2

    conn = connect()
    try:
        init_db(conn)

        # Prioritize delivery of existing ready emails before generating new ones.
        if not effective_dry_run:
            ready_emails = conn.execute(
                """
                SELECT ev.*, l.contact_email
                FROM email_variants ev
                JOIN leads l ON ev.lead_id = l.lead_id
                WHERE ev.delivery_status = 'ready'
                """
            ).fetchall()

            if ready_emails:
                log("dispatch_started", count=len(ready_emails), detail="Processing existing ready emails queue")
                for r_email in ready_emails:
                    email_dict = row_to_dict(r_email)
                    to_email = email_dict.get("contact_email")

                    if not to_email:
                        conn.execute("UPDATE email_variants SET delivery_status = 'failed' WHERE email_id = ?", (email_dict["email_id"],))
                        continue

                    result = send_email_via_resend(
                        to_email=to_email,
                        subject=email_dict["subject"],
                        html_body=email_dict["content"]
                    )

                    if result.get("success"):
                        now_sent_iso = utcnow_iso()
                        conn.execute(
                            "UPDATE email_variants SET delivery_status = 'sent', sent_at = ? WHERE email_id = ?",
                            (now_sent_iso, email_dict["email_id"])
                        )
                        conn.execute(
                            "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, 'sent', ?, ?)",
                            (email_dict["email_id"], result.get("provider_id"), now_sent_iso)
                        )
                        conn.execute("UPDATE leads SET status = ? WHERE lead_id = ?", (LeadStatus.WRITTEN.value, email_dict["lead_id"]))
                        log("email_dispatched_successfully", email_id=email_dict["email_id"])
                    else:
                        log("email_dispatch_failed", email_id=email_dict["email_id"], error=result.get("error"))

                conn.commit()

        # Enforce interval security before searching for new leads.
        if effective_dry_run:
            log("throttle_bypassed", reason="dry_run")
        else:
            allowed, reason = interval_guard(conn, min_interval_minutes)
            if not allowed:
                log("skip", reason="interval_not_reached", detail=reason)
                return 0

        ab_test = select_active_ab_test(conn)
        if not ab_test:
            log("skip", reason="no_active_ab_test")
            return 0

        selected_side: str | None = None
        variant_language = "en"

        lead = select_next_lead_for_ab_test(conn, ab_test)
        if not lead:
            log("skip", reason="no_eligible_lead_for_ab_test", ab_test_id=ab_test["ab_test_id"])
            return 0
        variant = select_ab_variant(conn, ab_test)
        if not variant:
            log("skip", reason="no_available_ab_variant", ab_test_id=ab_test["ab_test_id"])
            return 0
        selected_side = str(variant["side"])
        variant_language = str(variant.get("language") or "en")
        experiment = {
            "messaging_angle": variant["messaging_angle"],
            "email_format": variant["email_format"],
            "subject_variant": variant.get("subject_variant"),
        }
        log(
            "selected_ab_test",
            ab_test_id=ab_test["ab_test_id"],
            side=selected_side,
            segment=ab_test["segment"],
            country=ab_test["country"],
            lead_id=lead["lead_id"],
        )

        now_iso = utcnow_iso()
        insights = ensure_insights(conn, lead, now_iso, dry_run=effective_dry_run)
        log("insights_ready", count=len(insights))

        subject, content = render_email(lead, experiment, insights, language=variant_language)

        if effective_dry_run:
            log(
                "generated_email",
                lead_id=lead["lead_id"],
                experiment_id=experiment.get("experiment_id"),
                ab_test_id=ab_test["ab_test_id"],
                ab_side=selected_side,
                subject=subject,
                content=content,
            )
            log(
                "done",
                lead_id=lead["lead_id"],
                experiment_id=experiment.get("experiment_id"),
                ab_test_id=ab_test["ab_test_id"],
                ab_side=selected_side,
            )
            return 0

        cur = conn.execute(
            """
            INSERT INTO email_variants (
              lead_id, experiment_id, ab_test_id, ab_side, subject, content, delivery_status, created_at, sent_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                lead["lead_id"],
                experiment.get("experiment_id"),
                ab_test["ab_test_id"],
                selected_side,
                subject,
                content,
                "ready",
                now_iso,
            ),
        )
        email_id = int(cur.lastrowid)
        conn.execute(
            """
            INSERT INTO email_events (email_id, event_type, provider_id, event_time)
            VALUES (?, ?, ?, ?)
            """,
            (email_id, "ready", None, now_iso),
        )
        current_status = str(lead.get("status") or "")
        if (
            can_transition_lead_status(current_status, LeadStatus.WRITTEN.value)
            and current_status != LeadStatus.WRITTEN.value
        ):
            conn.execute("UPDATE leads SET status = ? WHERE lead_id = ?", (LeadStatus.WRITTEN.value, lead["lead_id"]))
        conn.commit()

        log(
            "generated_email",
            email_id=email_id,
            lead_id=lead["lead_id"],
            experiment_id=experiment.get("experiment_id"),
            ab_test_id=ab_test["ab_test_id"],
            ab_side=selected_side,
            subject=subject,
            content=content,
        )
        log("ready", email_id=email_id)
        log("done", email_id=email_id, lead_id=lead["lead_id"])
        return 0
    except Exception as exc:
        log("error", reason="unexpected_exception", detail=str(exc))
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
    parser.add_argument(
        "--mode",
        choices=["live", "test"],
        default="live",
        help="Execution mode. 'test' enforces dry-run and writes mode=test logs.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(run_cycle(dry_run=args.dry_run, mode=args.mode))


if __name__ == "__main__":
    main()
