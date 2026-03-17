import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator

from fastapi import Depends

from .config import settings


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
          subject_variant TEXT,
          created_at TEXT NOT NULL,
          active INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS email_variants (
          email_id INTEGER PRIMARY KEY AUTOINCREMENT,
          lead_id INTEGER NOT NULL,
          experiment_id INTEGER NOT NULL,
          subject TEXT NOT NULL,
          content TEXT NOT NULL,
          created_at TEXT NOT NULL,
          sent_at TEXT,
          FOREIGN KEY (lead_id) REFERENCES leads(lead_id) ON DELETE CASCADE,
          FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id) ON DELETE CASCADE
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
    conn.commit()


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
