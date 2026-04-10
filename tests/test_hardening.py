import dataclasses
import sqlite3

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import backend.config as config_module
import backend.database as database_module
import backend.main as main_module
from backend.schemas.lead_schema import LeadCreate
from backend.schemas.webhook_schema import EmailEventIn


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    test_settings = dataclasses.replace(config_module.settings, db_path=db_path)
    monkeypatch.setattr(config_module, "settings", test_settings)
    monkeypatch.setattr(database_module, "settings", test_settings)
    monkeypatch.setattr(main_module, "settings", test_settings)
    with TestClient(main_module.app) as test_client:
        yield test_client


def _create_lead(client: TestClient, *, email: str, website: str, status: str = "new") -> dict:
    payload = {
        "company": "Acme",
        "contact_email": email,
        "website": website,
        "segment": "food",
        "status": status,
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _create_experiment(client: TestClient, *, segment: str = "food") -> dict:
    payload = {
        "segment": segment,
        "messaging_angle": "local_visibility",
        "email_format": "short",
        "active": True,
    }
    response = client.post("/api/v1/experiments", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_schema_validation_rejects_invalid_email_and_url():
    with pytest.raises(ValidationError):
        LeadCreate(company="A", contact_email="not-email", website="https://example.com", segment="food")
    with pytest.raises(ValidationError):
        LeadCreate(company="A", contact_email="ok@example.com", website="not-a-url", segment="food")
    with pytest.raises(ValidationError):
        EmailEventIn(email_id=1, event_type="invalid")


def test_lead_status_transition_blocks_contacted_back_to_new(client: TestClient):
    lead = _create_lead(client, email="lead1@example.com", website="https://example.com")
    lead_id = lead["lead_id"]

    response = client.patch(f"/api/v1/leads/{lead_id}", json={"status": "contacted"})
    assert response.status_code == 200, response.text

    response = client.patch(f"/api/v1/leads/{lead_id}", json={"status": "new"})
    assert response.status_code == 409


def test_webhook_transition_blocks_sent_to_ready(client: TestClient):
    lead = _create_lead(client, email="lead2@example.com", website="https://example.org")
    experiment = _create_experiment(client)

    generated = client.post(
        "/api/v1/emails/generate",
        json={"lead_id": lead["lead_id"], "experiment_id": experiment["experiment_id"]},
    )
    assert generated.status_code == 200, generated.text
    email_id = generated.json()["email_id"]

    sent = client.post(
        "/api/v1/webhooks/email",
        json={"email_id": email_id, "event_type": "sent", "provider_id": "provider-1"},
    )
    assert sent.status_code == 200, sent.text

    invalid = client.post("/api/v1/webhooks/email", json={"email_id": email_id, "event_type": "ready"})
    assert invalid.status_code == 409


def test_lead_marked_contacted_only_after_sent_event(client: TestClient):
    lead = _create_lead(client, email="lead3@example.com", website="https://example.net")
    experiment = _create_experiment(client)

    generated = client.post(
        "/api/v1/emails/generate",
        json={"lead_id": lead["lead_id"], "experiment_id": experiment["experiment_id"]},
    )
    assert generated.status_code == 200, generated.text
    email_id = generated.json()["email_id"]

    lead_after_generate = client.get(f"/api/v1/leads/{lead['lead_id']}")
    assert lead_after_generate.status_code == 200, lead_after_generate.text
    assert lead_after_generate.json()["status"] == "written"

    sent = client.post(
        "/api/v1/webhooks/email",
        json={"email_id": email_id, "event_type": "sent", "provider_id": "provider-2"},
    )
    assert sent.status_code == 200, sent.text

    lead_after_sent = client.get(f"/api/v1/leads/{lead['lead_id']}")
    assert lead_after_sent.status_code == 200, lead_after_sent.text
    assert lead_after_sent.json()["status"] == "contacted"


def test_pagination_and_sorting_on_leads_and_experiments(client: TestClient):
    for idx in range(3):
        _create_lead(client, email=f"lead{idx+10}@example.com", website=f"https://site{idx}.example.com")
        _create_experiment(client)

    leads_page = client.get("/api/v1/leads?limit=2&offset=1&sort_by=created_at&sort_order=desc")
    assert leads_page.status_code == 200, leads_page.text
    assert len(leads_page.json()) == 2

    exps_page = client.get("/api/v1/experiments?limit=2&offset=1&sort_by=created_at&sort_order=desc")
    assert exps_page.status_code == 200, exps_page.text
    assert len(exps_page.json()) == 2


def test_migration_dedupes_and_creates_unique_index(tmp_path):
    db_path = tmp_path / "migration.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    conn.executescript(
        """
        CREATE TABLE leads (
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
        CREATE TABLE seo_insights (
          insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
          lead_id INTEGER NOT NULL,
          issue_type TEXT NOT NULL,
          issue_description TEXT NOT NULL,
          severity INTEGER NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE experiments (
          experiment_id INTEGER PRIMARY KEY AUTOINCREMENT,
          segment TEXT NOT NULL,
          messaging_angle TEXT NOT NULL,
          email_format TEXT NOT NULL,
          subject_variant TEXT,
          created_at TEXT NOT NULL,
          active INTEGER NOT NULL
        );
        CREATE TABLE email_variants (
          email_id INTEGER PRIMARY KEY AUTOINCREMENT,
          lead_id INTEGER NOT NULL,
          experiment_id INTEGER NOT NULL,
          subject TEXT NOT NULL,
          content TEXT NOT NULL,
          created_at TEXT NOT NULL,
          sent_at TEXT
        );
        CREATE TABLE email_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT,
          email_id INTEGER NOT NULL,
          event_type TEXT NOT NULL,
          provider_id TEXT,
          event_time TEXT NOT NULL
        );
        CREATE TABLE replies (
          reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
          email_id INTEGER NOT NULL,
          lead_id INTEGER NOT NULL,
          reply_text TEXT NOT NULL,
          sentiment TEXT,
          created_at TEXT NOT NULL
        );
        """
    )
    now = "2026-04-10T00:00:00+00:00"
    conn.execute(
        """
        INSERT INTO leads (company, contact_email, website, segment, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("A", "dup@example.com", "https://EXAMPLE.com", "food", now, "new"),
    )
    conn.execute(
        """
        INSERT INTO leads (company, contact_email, website, segment, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("B", "DUP@example.com", "https://example.com", "food", now, "new"),
    )
    conn.execute(
        """
        INSERT INTO seo_insights (lead_id, issue_type, issue_description, severity, created_at)
        VALUES (2, 'x', 'y', 5, ?)
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO experiments (segment, messaging_angle, email_format, subject_variant, created_at, active)
        VALUES ('food', 'local_visibility', 'short', 'subj', ?, 1)
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO email_variants (lead_id, experiment_id, subject, content, created_at, sent_at)
        VALUES (2, 1, 's', 'c', ?, NULL)
        """,
        (now,),
    )
    conn.execute(
        """
        INSERT INTO replies (email_id, lead_id, reply_text, sentiment, created_at)
        VALUES (1, 2, 'hello', NULL, ?)
        """,
        (now,),
    )
    conn.commit()

    database_module._run_migrations(conn)
    conn.commit()

    lead_count = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
    assert lead_count == 1

    repointed = conn.execute("SELECT COUNT(*) AS n FROM seo_insights WHERE lead_id = 1").fetchone()["n"]
    assert repointed == 1

    indexes = conn.execute("PRAGMA index_list(leads)").fetchall()
    assert any("idx_leads_unique_contact_website" in idx["name"] for idx in indexes)

    conn.close()
