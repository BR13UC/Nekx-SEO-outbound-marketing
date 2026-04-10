import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator

from fastapi import Depends

from .config import settings
from .domain_types import DeliveryStatus, EmailEventType, EmailFormat, LeadStatus


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_db_dir() -> None:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    ensure_db_dir()
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    # Schema mirrors docs/Archi.md tables.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS leads (
          lead_id INTEGER PRIMARY KEY AUTOINCREMENT,
          company TEXT NOT NULL,
          contact_email TEXT NOT NULL,
          website TEXT NOT NULL,
          segment TEXT NOT NULL,
          industry TEXT,
          country TEXT,
          source TEXT,
          created_at TEXT NOT NULL,
          status TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS seo_insights (
          insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
          lead_id INTEGER NOT NULL,
          issue_type TEXT NOT NULL,
          issue_description TEXT NOT NULL,
          severity INTEGER NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS experiments (
          experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
          segment TEXT NOT NULL,
          messaging_angle TEXT NOT NULL,
          email_format TEXT NOT NULL,
          max_emails_total INTEGER,
          subject_variant TEXT,
          created_at TEXT NOT NULL,
          active INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ab_tests (
          ab_test_id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          segment TEXT NOT NULL,
          country TEXT NOT NULL,
          comparison_mode TEXT NOT NULL,
          max_emails_total INTEGER NOT NULL,
          max_emails_a INTEGER NOT NULL,
          max_emails_b INTEGER NOT NULL,
          winner_metric TEXT NOT NULL DEFAULT 'reply_rate',
          changed_dimensions TEXT NOT NULL,
          created_at TEXT NOT NULL,
          active INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ab_test_variants (
          variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
          ab_test_id INTEGER NOT NULL,
          side TEXT NOT NULL,
          messaging_angle TEXT NOT NULL,
          email_format TEXT NOT NULL,
          subject_variant TEXT,
          language TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (ab_test_id) REFERENCES ab_tests(ab_test_id) ON DELETE CASCADE,
          UNIQUE(ab_test_id, side)
        );

        CREATE TABLE IF NOT EXISTS email_variants (
          email_id INTEGER PRIMARY KEY AUTOINCREMENT,
          lead_id INTEGER NOT NULL,
          experiment_id INTEGER,
          ab_test_id INTEGER,
          ab_side TEXT,
          subject TEXT NOT NULL,
          content TEXT NOT NULL,
          delivery_status TEXT NOT NULL DEFAULT 'ready',
          created_at TEXT NOT NULL,
          sent_at TEXT,
          FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE,
          FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
          FOREIGN KEY (ab_test_id) REFERENCES ab_tests(ab_test_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS email_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          email_id INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          provider_id TEXT,
          event_time TEXT NOT NULL,
          FOREIGN KEY (email_id) REFERENCES email_variants(email_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS replies (
          reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
          email_id INTEGER NOT NULL,
          lead_id INTEGER NOT NULL,
          reply_text TEXT NOT NULL,
          sentiment TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (email_id) REFERENCES email_variants(email_id) ON DELETE CASCADE,
          FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS experiment_results (
          result_id INTEGER PRIMARY KEY AUTOINCREMENT,
          experiment_id INTEGER NOT NULL UNIQUE,
          opens INTEGER NOT NULL,
          replies INTEGER NOT NULL,
          positive_replies INTEGER NOT NULL,
          conversions INTEGER NOT NULL,
          updated_at TEXT NOT NULL,
          FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
        );
        """
    )
    _run_migrations(conn)
    conn.commit()


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r["name"] == column for r in rows)


def _run_migrations(conn: sqlite3.Connection) -> None:
    # Additive schema upgrades for older local DBs.
    if not _column_exists(conn, "experiments", "max_emails_total"):
        conn.execute("ALTER TABLE experiments ADD COLUMN max_emails_total INTEGER")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ab_tests (
          ab_test_id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          segment TEXT NOT NULL,
          country TEXT NOT NULL,
          comparison_mode TEXT NOT NULL,
          max_emails_total INTEGER NOT NULL,
          max_emails_a INTEGER NOT NULL,
          max_emails_b INTEGER NOT NULL,
          winner_metric TEXT NOT NULL DEFAULT 'reply_rate',
          changed_dimensions TEXT NOT NULL,
          created_at TEXT NOT NULL,
          active INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ab_test_variants (
          variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
          ab_test_id INTEGER NOT NULL,
          side TEXT NOT NULL,
          messaging_angle TEXT NOT NULL,
          email_format TEXT NOT NULL,
          subject_variant TEXT,
          language TEXT,
          created_at TEXT NOT NULL,
          FOREIGN KEY (ab_test_id) REFERENCES ab_tests(ab_test_id) ON DELETE CASCADE,
          UNIQUE(ab_test_id, side)
        )
        """
    )

    _migrate_email_variants_table(conn)

    # Backfill delivery status values.
    conn.execute(
        """
        UPDATE email_variants
        SET delivery_status = CASE
            WHEN sent_at IS NOT NULL THEN ?
            ELSE ?
        END
        WHERE delivery_status IS NULL OR delivery_status = ''
        """,
        (DeliveryStatus.SENT.value, DeliveryStatus.READY.value),
    )

    # Normalize enum-backed values to supported sets.
    conn.execute(
        """
        UPDATE leads
        SET status = ?
        WHERE status IS NULL OR status NOT IN (?, ?, ?)
        """,
        (
            LeadStatus.NEW.value,
            LeadStatus.NEW.value,
            LeadStatus.WRITTEN.value,
            LeadStatus.CONTACTED.value,
        ),
    )
    conn.execute(
        """
        UPDATE email_variants
        SET delivery_status = CASE
            WHEN sent_at IS NOT NULL THEN ?
            ELSE ?
        END
        WHERE delivery_status NOT IN (?, ?)
        """,
        (
            DeliveryStatus.SENT.value,
            DeliveryStatus.READY.value,
            DeliveryStatus.READY.value,
            DeliveryStatus.SENT.value,
        ),
    )
    conn.execute(
        """
        UPDATE experiments
        SET email_format = ?
        WHERE email_format IS NULL OR email_format NOT IN (?, ?)
        """,
        (EmailFormat.SHORT.value, EmailFormat.SHORT.value, EmailFormat.MEDIUM.value),
    )
    conn.execute(
        """
        UPDATE email_events
        SET event_type = ?
        WHERE event_type IS NULL OR event_type NOT IN (?, ?, ?, ?)
        """,
        (
            EmailEventType.READY.value,
            EmailEventType.READY.value,
            EmailEventType.SENT.value,
            EmailEventType.OPENED.value,
            EmailEventType.REPLIED.value,
        ),
    )

    # Cleanup historical pseudo-sent rows (provider_id is null): treat as ready/not sent.
    conn.execute(
        """
        UPDATE email_events
        SET event_type = ?
        WHERE event_type = ?
          AND (provider_id IS NULL OR provider_id = '')
        """,
        (EmailEventType.READY.value, EmailEventType.SENT.value),
    )
    conn.execute(
        """
        UPDATE email_variants
        SET sent_at = NULL, delivery_status = ?
        WHERE email_id IN (
            SELECT ev.email_id
            FROM email_variants ev
            LEFT JOIN email_events ee
              ON ee.email_id = ev.email_id
              AND ee.event_type = ?
              AND ee.provider_id IS NOT NULL
              AND ee.provider_id != ''
            WHERE ee.event_id IS NULL
        )
        """,
        (DeliveryStatus.READY.value, EmailEventType.SENT.value),
    )

    # Merge duplicate leads before enforcing normalized uniqueness.
    _merge_duplicate_leads(conn)

    # Performance indexes for common API filters/joins.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_email_variants_delivery_sent_at ON email_variants(delivery_status, sent_at)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_events_email_event ON email_events(email_id, event_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_segment_status ON leads(segment, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_email_variants_ab_test_side ON email_variants(ab_test_id, ab_side)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ab_tests_active_segment_country ON ab_tests(active, segment, country)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_unique_contact_website "
        "ON leads(lower(contact_email), lower(website))"
    )


def _merge_duplicate_leads(conn: sqlite3.Connection) -> None:
    duplicates = conn.execute(
        """
        SELECT lower(contact_email) AS email_key, lower(website) AS website_key
        FROM leads
        GROUP BY lower(contact_email), lower(website)
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    for dup in duplicates:
        rows = conn.execute(
            """
            SELECT lead_id
            FROM leads
            WHERE lower(contact_email) = ? AND lower(website) = ?
            ORDER BY lead_id ASC
            """,
            (dup["email_key"], dup["website_key"]),
        ).fetchall()
        if len(rows) < 2:
            continue
        canonical_id = int(rows[0]["lead_id"])
        duplicate_ids = [int(r["lead_id"]) for r in rows[1:]]
        for duplicate_id in duplicate_ids:
            conn.execute("UPDATE seo_insights SET lead_id = ? WHERE lead_id = ?", (canonical_id, duplicate_id))
            conn.execute("UPDATE email_variants SET lead_id = ? WHERE lead_id = ?", (canonical_id, duplicate_id))
            conn.execute("UPDATE replies SET lead_id = ? WHERE lead_id = ?", (canonical_id, duplicate_id))
            conn.execute("DELETE FROM leads WHERE lead_id = ?", (duplicate_id,))


def _migrate_email_variants_table(conn: sqlite3.Connection) -> None:
    # Keep migration idempotent across old and new DBs.
    cols = conn.execute("PRAGMA table_info(email_variants)").fetchall()
    if not cols:
        return

    names = {r["name"] for r in cols}
    needs_rebuild = False

    # Older schemas have experiment_id as NOT NULL and no AB fields.
    experiment_col = next((r for r in cols if r["name"] == "experiment_id"), None)
    if experiment_col and int(experiment_col["notnull"]) == 1:
        needs_rebuild = True
    if "ab_test_id" not in names or "ab_side" not in names:
        needs_rebuild = True

    if not needs_rebuild:
        return

    conn.execute("ALTER TABLE email_variants RENAME TO email_variants_old")
    conn.execute(
        """
        CREATE TABLE email_variants (
          email_id INTEGER PRIMARY KEY AUTOINCREMENT,
          lead_id INTEGER NOT NULL,
          experiment_id INTEGER,
          ab_test_id INTEGER,
          ab_side TEXT,
          subject TEXT NOT NULL,
          content TEXT NOT NULL,
          delivery_status TEXT NOT NULL DEFAULT 'ready',
          created_at TEXT NOT NULL,
          sent_at TEXT,
          FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE,
          FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE,
          FOREIGN KEY (ab_test_id) REFERENCES ab_tests(ab_test_id) ON DELETE SET NULL
        )
        """
    )

    old_names = {r["name"] for r in conn.execute("PRAGMA table_info(email_variants_old)").fetchall()}
    has_delivery = "delivery_status" in old_names
    has_ab_test = "ab_test_id" in old_names
    has_ab_side = "ab_side" in old_names

    conn.execute(
        f"""
        INSERT INTO email_variants (
          email_id, lead_id, experiment_id, ab_test_id, ab_side, subject, content, delivery_status, created_at, sent_at
        )
        SELECT
          email_id,
          lead_id,
          experiment_id,
          {"ab_test_id" if has_ab_test else "NULL"},
          {"ab_side" if has_ab_side else "NULL"},
          subject,
          content,
          {"delivery_status" if has_delivery else "'ready'"},
          created_at,
          sent_at
        FROM email_variants_old
        """
    )
    conn.execute("DROP TABLE email_variants_old")


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


DbConn = sqlite3.Connection
Db = Depends(get_db)


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return dict(row)
