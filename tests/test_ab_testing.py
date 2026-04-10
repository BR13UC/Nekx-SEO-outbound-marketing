import dataclasses
import json
from pathlib import Path

from fastapi.testclient import TestClient

import backend.config as config_module
import backend.database as database_module
import backend.main as main_module
import backend.tools.run_outbound_cycle as cycle_module


def _build_settings(tmp_path: Path):
    scheduler_path = tmp_path / "scheduler.json"
    scheduler_path.write_text(
        json.dumps(
            {
                "enabled": False,
                "min_interval_minutes": 0,
                "log_level": "ERROR",
                "log_file_path": str(tmp_path / "scheduler.log"),
            }
        ),
        encoding="utf-8",
    )
    return dataclasses.replace(
        config_module.settings,
        db_path=tmp_path / "test.db",
        scheduler_config_path=scheduler_path,
        email_mode="template",
        email_fallback_mode="fallback",
    )


def _create_lead(client: TestClient, idx: int, *, segment: str = "food", country: str = "NL") -> dict:
    payload = {
        "company": f"Lead {idx}",
        "contact_email": f"lead{idx}@example.com",
        "website": f"https://example{idx}.com",
        "segment": segment,
        "country": country,
        "status": "new",
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _create_ab_test(client: TestClient, *, max_emails_total: int = 5) -> dict:
    payload = {
        "name": "Food NL angle test",
        "segment": "food",
        "country": "NL",
        "comparison_mode": "custom",
        "changed_dimensions": ["messaging_angle", "language"],
        "max_emails_total": max_emails_total,
        "active": True,
        "variant_a": {
            "messaging_angle": "local_visibility",
            "email_format": "short",
            "subject_variant": "A subject",
            "language": "en",
        },
        "variant_b": {
            "messaging_angle": "cost_saving",
            "email_format": "short",
            "subject_variant": "A subject",
            "language": "fr",
        },
    }
    response = client.post("/api/v1/ab-tests", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_ab_create_validation_and_split(tmp_path, monkeypatch):
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(config_module, "settings", settings)
    monkeypatch.setattr(database_module, "settings", settings)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(cycle_module, "settings", settings)
    monkeypatch.setattr(main_module, "_start_scheduler_loop", lambda: None)
    monkeypatch.setattr(main_module, "_stop_scheduler_loop", lambda: None)

    with TestClient(main_module.app) as client:
        invalid_payload = {
            "name": "Invalid",
            "segment": "food",
            "country": "NL",
            "comparison_mode": "custom",
            "changed_dimensions": ["messaging_angle"],
            "max_emails_total": 3,
            "active": True,
            "variant_a": {
                "messaging_angle": "same",
                "email_format": "short",
                "subject_variant": None,
                "language": "en",
            },
            "variant_b": {
                "messaging_angle": "same",
                "email_format": "short",
                "subject_variant": None,
                "language": "en",
            },
        }
        invalid = client.post("/api/v1/ab-tests", json=invalid_payload)
        assert invalid.status_code == 422

        created = _create_ab_test(client, max_emails_total=5)
        assert created["max_emails_a"] == 3
        assert created["max_emails_b"] == 2


def test_ab_results_and_winner(tmp_path, monkeypatch):
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(config_module, "settings", settings)
    monkeypatch.setattr(database_module, "settings", settings)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(cycle_module, "settings", settings)
    monkeypatch.setattr(main_module, "_start_scheduler_loop", lambda: None)
    monkeypatch.setattr(main_module, "_stop_scheduler_loop", lambda: None)

    with TestClient(main_module.app) as client:
        for i in range(1, 5):
            _create_lead(client, i)
        ab = _create_ab_test(client, max_emails_total=4)
        ab_test_id = ab["ab_test_id"]

        for _ in range(4):
            # Override scheduler config to enabled for direct cycle invocation.
            settings.scheduler_config_path.write_text(
                json.dumps(
                    {
                        "enabled": True,
                        "min_interval_minutes": 0,
                        "log_level": "ERROR",
                        "log_file_path": str(tmp_path / "scheduler.log"),
                    }
                ),
                encoding="utf-8",
            )
            assert cycle_module.run_cycle(dry_run=False, mode="live") == 0

        conn = database_module.connect()
        try:
            created_rows = conn.execute(
                "SELECT email_id FROM email_variants WHERE ab_test_id = ? ORDER BY email_id ASC",
                (ab_test_id,),
            ).fetchall()
            created_emails = [int(r["email_id"]) for r in created_rows]
        finally:
            conn.close()

        assert len(created_emails) == 4

        # Mark all as sent; reply only to A to make A winner.
        for email_id in created_emails:
            sent = client.post(
                "/api/v1/webhooks/email",
                json={"email_id": email_id, "event_type": "sent", "provider_id": f"provider-{email_id}"},
            )
            assert sent.status_code == 200, sent.text

        conn = database_module.connect()
        try:
            rows = conn.execute(
                "SELECT email_id, ab_side FROM email_variants WHERE ab_test_id = ? ORDER BY email_id ASC",
                (ab_test_id,),
            ).fetchall()
            assert len(rows) == 4
            side_by_email = {int(r["email_id"]): str(r["ab_side"]) for r in rows}
        finally:
            conn.close()

        for email_id, side in side_by_email.items():
            if side != "A":
                continue
            replied = client.post(
                "/api/v1/webhooks/email",
                json={"email_id": email_id, "event_type": "replied", "reply_text": "Sounds good"},
            )
            assert replied.status_code == 200, replied.text

        results = client.get(f"/api/v1/ab-tests/{ab_test_id}/results")
        assert results.status_code == 200, results.text
        payload = results.json()
        assert payload["sent_a"] == 2
        assert payload["sent_b"] == 2
        assert payload["replied_a"] == 2
        assert payload["replied_b"] == 0
        assert payload["winner_side"] == "A"


def test_cycle_ab_assignment_and_caps(tmp_path, monkeypatch):
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(config_module, "settings", settings)
    monkeypatch.setattr(database_module, "settings", settings)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(cycle_module, "settings", settings)
    monkeypatch.setattr(main_module, "_start_scheduler_loop", lambda: None)
    monkeypatch.setattr(main_module, "_stop_scheduler_loop", lambda: None)

    with TestClient(main_module.app) as client:
        for i in range(1, 10):
            _create_lead(client, i, segment="food", country="NL")
        ab = _create_ab_test(client, max_emails_total=3)

        settings.scheduler_config_path.write_text(
            json.dumps(
                {
                    "enabled": True,
                    "min_interval_minutes": 0,
                    "log_level": "ERROR",
                    "log_file_path": str(tmp_path / "scheduler.log"),
                }
            ),
            encoding="utf-8",
        )
        assert cycle_module.run_cycle(dry_run=False, mode="live") == 0
        assert cycle_module.run_cycle(dry_run=False, mode="live") == 0
        assert cycle_module.run_cycle(dry_run=False, mode="live") == 0
        # cap reached: no new A/B email is generated.
        assert cycle_module.run_cycle(dry_run=False, mode="live") == 0

        conn = database_module.connect()
        try:
            rows = conn.execute(
                "SELECT ab_side FROM email_variants WHERE ab_test_id = ? ORDER BY email_id ASC",
                (ab["ab_test_id"],),
            ).fetchall()
            sides = [str(r["ab_side"]) for r in rows]
            assert sides == ["A", "B", "A"]
        finally:
            conn.close()


def test_scheduler_queue_and_waiting_status(tmp_path, monkeypatch):
    settings = _build_settings(tmp_path)
    monkeypatch.setattr(config_module, "settings", settings)
    monkeypatch.setattr(database_module, "settings", settings)
    monkeypatch.setattr(main_module, "settings", settings)
    monkeypatch.setattr(cycle_module, "settings", settings)
    monkeypatch.setattr(main_module, "_start_scheduler_loop", lambda: None)
    monkeypatch.setattr(main_module, "_stop_scheduler_loop", lambda: None)

    with TestClient(main_module.app) as client:
        for i in range(1, 6):
            _create_lead(client, i, segment="food", country="NL")
        _create_ab_test(client, max_emails_total=4)

        queue = client.get("/api/v1/analytics/queue?limit=3")
        assert queue.status_code == 200, queue.text
        rows = queue.json()
        assert len(rows) == 3
        assert [r["side"] for r in rows] == ["A", "B", "A"]

        status = client.get("/api/v1/analytics/cron-status")
        assert status.status_code == 200, status.text
        assert status.json()["status"] in {"waiting", "paused", "running"}
