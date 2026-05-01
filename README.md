# Nekx SEO - AI Outbound Experimentation Platform

## What This Repository Does
This project runs an auditable outbound experimentation loop:
1. Source and manage leads.
2. Generate SEO opportunity insights (currently case-based).
3. Generate personalized outreach emails.
4. Send emails (current send endpoint is a stub flow).
5. Track events and compare experiments (including A/B tests).

The platform is designed for attribution: generated emails are linked to lead and experiment context in SQLite.

## Current Status (April 10, 2026)
- Backend stack: FastAPI + SQLite.
- Email generation: Gemini-first, with template fallback mode.
- SEO insights: case-based benchmark opportunities (no live technical website audit yet).
- Sending: `/emails/send` marks provider-confirmed sent status only when provider metadata is present.
- Scheduler: built-in app loop + manual/cron runner (`run_outbound_cycle`).
- Admin panel: one-page operations UI at `/admin`.

## Quick Start
### Docker quick start
```bash
docker compose up --build
```

Then open:
```text
http://127.0.0.1:8000/admin
```

Docker keeps SQLite and scheduler data persistent by mounting `./data` into the container at `/app/data`. Docker Compose automatically reads a local `.env` file for values such as `GOOGLE_API_KEY`; do not commit secrets.

Run one outbound cycle from the container:
```bash
docker compose exec app python -m backend.tools.run_outbound_cycle
```

### Local Python quick start
### 1) Create virtual environment
```bash
python3 -m venv .venv && source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 3) Reset DB, import leads, and seed experiments
```bash
python -m backend.tools.reset_and_import_leads \
  --db-path data/nekx.db \
  --xlsx-path data/groningen_food_drink_leads.xlsx
```

### 4) Run API server
```bash
uvicorn backend.main:app --reload
```

### 5) Health check
```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 6) Open admin panel
```bash
open http://127.0.0.1:8000/admin
```
Dashboard is also available at `/`.

## End-to-End Example
### Generate SEO opportunities for one lead
```bash
curl -X POST http://127.0.0.1:8000/api/v1/seo/analyze \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1}'
```

### Generate one email
```bash
curl -X POST http://127.0.0.1:8000/api/v1/emails/generate \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1, "experiment_id": 1}'
```

### Mark email as sent (stub flow)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/emails/send \
  -H 'Content-Type: application/json' \
  -d '{"email_id": 1}'
```

## API Surface (Base: `/api/v1`)
### Core
- `GET /health`
- `POST /leads`
- `GET /leads`
- `GET /leads/{lead_id}`
- `PATCH /leads/{lead_id}`
- `GET /leads/segments`
- `GET /leads/sources`
- `GET /leads/countries`
- `POST /seo/analyze`
- `GET /seo/{lead_id}`
- `POST /experiments`
- `GET /experiments`
- `GET /experiments/options`
- `GET /experiments/{experiment_id}/results`
- `POST /ab-tests`
- `GET /ab-tests`
- `GET /ab-tests/{ab_test_id}/results`
- `GET /ab-tests/{ab_test_id}/details`
- `POST /emails/generate`
- `GET /emails/{email_id}`
- `POST /emails/send`
- `POST /webhooks/email`

### Analytics + Scheduler
- `GET /analytics/summary?segment=&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /analytics/segments?segment=&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /analytics/messaging?segment=&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /analytics/recent-emails?limit=10&segment=&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
- `GET /analytics/queue?limit=20`
- `GET /analytics/activity?limit=40`
- `GET /analytics/cron-status`
- `GET /scheduler/config`
- `PATCH /scheduler/config`
- `POST /scheduler/run` (`mode=live|test`)

## Manual or Cron Outbound Cycle
Run one manual cycle:
```bash
python -m backend.tools.run_outbound_cycle
```

Dry run:
```bash
python -m backend.tools.run_outbound_cycle --dry-run
```

Test mode (enforces dry-run and logs `mode=test`):
```bash
python -m backend.tools.run_outbound_cycle --mode test
```

Example cron (every minute, throttled by scheduler config):
```bash
* * * * * cd /home/brieuc/AIAndYourProfession/Nekx-SEO-outbound-marketing && ./.venv/bin/python -m backend.tools.run_outbound_cycle >> /tmp/nekx-cron.log 2>&1
```

## Environment Variables
- `NEKX_DB_PATH` (default: `data/nekx.db`)
- `NEKX_LEADS_XLSX_PATH` (default: `data/groningen_food_drink_leads.xlsx`)
- `NEKX_CASE_INSIGHTS_PATH` (default: `backend/data/case_insights.json`)
- `NEKX_EMAIL_MODE` (`gemini` or `template`, default: `gemini`)
- `NEKX_EMAIL_FALLBACK_MODE` (`fallback` or `strict`, default: `fallback`)
- `GOOGLE_API_KEY` (required for Gemini mode)
- `NEKX_GEMINI_MODEL` (default: `gemini-2.5-flash`)
- `NEKX_SCHEDULER_CONFIG_PATH` (default: `data/scheduler_config.json`)

## Data Model (Core Tables)
- `leads`
- `seo_insights`
- `experiments`
- `ab_tests`
- `ab_test_variants`
- `email_variants`
- `email_events`
- `replies`
- `experiment_results`

## Operational Notes
- Current Step 1 insights are benchmark-based opportunities, not direct technical claims.
- Keep compliance elements in generated emails (identity + unsubscribe).
- Scheduler guardrails enforce minimum interval and deterministic lead picking.
