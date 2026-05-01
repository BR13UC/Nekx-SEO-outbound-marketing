# Operations Guide

## 1) Environment Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
```

Docker alternative:
```bash
docker compose up --build
```

The admin UI is available at:
```text
http://127.0.0.1:8000/admin
```

Docker mounts `./data` to `/app/data`, so SQLite, imported leads, scheduler config, and scheduler logs stay on the host. Docker Compose reads a local `.env` file automatically for variable interpolation; use it for `GOOGLE_API_KEY` or email mode overrides, and do not commit secrets.

## 2) Reset DB and Import Leads
```bash
python -m backend.tools.reset_and_import_leads \
  --db-path data/nekx.db \
  --xlsx-path data/groningen_food_drink_leads.xlsx
```

Expected outcome:
- outreach tables reset
- leads imported
- baseline experiments seeded by discovered segments

## 3) Start API
```bash
uvicorn backend.main:app --reload
```

## 4) Smoke Test Core Endpoints
Health:
```bash
curl http://127.0.0.1:8000/api/v1/health
```

Generate insights:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/seo/analyze \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1}'
```

Generate email:
```bash
curl -X POST http://127.0.0.1:8000/api/v1/emails/generate \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1, "experiment_id": 1}'
```

Mark as sent (stub):
```bash
curl -X POST http://127.0.0.1:8000/api/v1/emails/send \
  -H 'Content-Type: application/json' \
  -d '{"email_id": 1}'
```

## 5) Run Scheduler Cycle Manually
Live mode:
```bash
python -m backend.tools.run_outbound_cycle
```

Inside Docker:
```bash
docker compose exec app python -m backend.tools.run_outbound_cycle
```

Dry run:
```bash
python -m backend.tools.run_outbound_cycle --dry-run
```

Tagged test mode (`dry-run` enforced):
```bash
python -m backend.tools.run_outbound_cycle --mode test
```

## 6) Scheduler Config
Default file: `data/scheduler_config.json`

```json
{
  "enabled": true,
  "min_interval_minutes": 30,
  "log_level": "INFO",
  "log_file_path": "data/outbound_scheduler.log"
}
```

Config API:
```bash
curl http://127.0.0.1:8000/api/v1/scheduler/config
curl -X PATCH http://127.0.0.1:8000/api/v1/scheduler/config \
  -H 'Content-Type: application/json' \
  -d '{"enabled":true,"min_interval_minutes":30,"log_level":"INFO","log_file_path":"data/outbound_scheduler.log"}'
curl -X POST http://127.0.0.1:8000/api/v1/scheduler/run \
  -H 'Content-Type: application/json' \
  -d '{"mode":"test"}'
```

## 7) Admin and Analytics
Admin UI:
```bash
http://127.0.0.1:8000/admin
```

Analytics helpers:
```bash
curl 'http://127.0.0.1:8000/api/v1/analytics/summary?segment=food&start_date=2026-04-01&end_date=2026-04-10'
curl 'http://127.0.0.1:8000/api/v1/analytics/segments?start_date=2026-04-01&end_date=2026-04-10'
curl 'http://127.0.0.1:8000/api/v1/analytics/messaging?start_date=2026-04-01&end_date=2026-04-10'
curl 'http://127.0.0.1:8000/api/v1/analytics/recent-emails?limit=10&segment=food&start_date=2026-04-01&end_date=2026-04-10'
curl 'http://127.0.0.1:8000/api/v1/analytics/queue?limit=20'
curl 'http://127.0.0.1:8000/api/v1/analytics/activity?limit=40'
curl 'http://127.0.0.1:8000/api/v1/analytics/cron-status'
```

Common lead/experiment helpers:
```bash
curl 'http://127.0.0.1:8000/api/v1/leads/segments'
curl 'http://127.0.0.1:8000/api/v1/leads/sources'
curl 'http://127.0.0.1:8000/api/v1/leads/countries'
curl 'http://127.0.0.1:8000/api/v1/experiments/options'
```

Notes:
- `start_date` / `end_date` format: `YYYY-MM-DD`
- sent metrics use `delivery_status='sent'`
- A/B tests require at least one explicit changed dimension (`messaging_angle`, `email_format`, `subject_variant`, or `language`); dimensions not selected for the test are edited once in the Common column and submitted identically for Variant A and Variant B.

## 8) Example Cron
Every minute (actual sending rate controlled by `min_interval_minutes`):
```bash
* * * * * cd /home/brieuc/AIAndYourProfession/Nekx-SEO-outbound-marketing && ./.venv/bin/python -m backend.tools.run_outbound_cycle >> /tmp/nekx-cron.log 2>&1
```

## Troubleshooting
### Missing `GOOGLE_API_KEY`
- `fallback` mode: template generation is used.
- `strict` mode: generation returns an error.

### Lead import column mismatch
Ensure spreadsheet includes:
- `company`
- `contact_email`
- `website`
- `segment`

### DB path mismatch
Set `NEKX_DB_PATH` or pass `--db-path` explicitly.

### Invalid scheduler JSON
Symptom:
- scheduler exits with code `2`

Behavior:
- logs structured `invalid_json_config`
- skips outreach data writes for that run

### Broken email event foreign keys
Symptom:
- scheduler logs `no such table: main.email_variants_old`

Behavior:
- startup and scheduler migrations repair `email_events` and `replies` foreign keys to reference `email_variants`
- verify with `sqlite3 data/nekx.db "PRAGMA foreign_key_list(email_events); PRAGMA foreign_key_list(replies); PRAGMA foreign_key_check;"`
