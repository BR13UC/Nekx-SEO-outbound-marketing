# Nekx SEO - AI Outreach Agent

## What this repo does
This project runs an outbound experimentation loop:

1. import leads
2. generate case-based SEO opportunities
3. generate emails (Gemini by default)
4. send emails (provider stub in v0)
5. track events and compare experiment variants

The system is intentionally auditable: every generated email is linked to lead and experiment records in SQLite.

## Current workflow (implemented)
- Step 1 uses a local case-insights snapshot derived from existing Nekx result examples.
- Step 2 uses Gemini by default (`NEKX_EMAIL_MODE=gemini`) with automatic template fallback unless strict mode is enabled.
- Step 3 `/emails/send` is still a provider stub that marks an email as sent and records a `sent` event.

## Quick start

### 0) Start python environment
```bash
python3 -m venv .venv && source .venv/bin/activate
```

### 1) Install dependencies
```bash
pip install -r backend/requirements.txt
```

### 2) Reset DB + import leads + seed experiments
```bash
python -m backend.tools.reset_and_import_leads \
  --db-path data/nekx.db \
  --xlsx-path data/groningen_food_drink_leads.xlsx
```

### 3) Run API
```bash
uvicorn backend.main:app --reload
```

### 4) Check health
```bash
curl http://127.0.0.1:8000/api/v1/health
```

## End-to-end example
### Generate case-based insights for one lead
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

### Mark email as sent (v0 stub)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/emails/send \
  -H 'Content-Type: application/json' \
  -d '{"email_id": 1}'
```

## Cron/Manual outbound cycle
Run one manual cycle:
```bash
python -m backend.tools.run_outbound_cycle
```

Dry-run mode (no email/event rows written):
```bash
python -m backend.tools.run_outbound_cycle --dry-run
```

Example cron (every minute, throttled by config):
```bash
* * * * * cd /home/brieuc/AIAndYourProfession/Nekx-SEO-outbound-marketing && ./.venv/bin/python -m backend.tools.run_outbound_cycle >> /tmp/nekx-cron.log 2>&1
```

## Environment variables
- `NEKX_DB_PATH` (default: `data/nekx.db`)
- `NEKX_LEADS_XLSX_PATH` (default: `data/groningen_food_drink_leads.xlsx`)
- `NEKX_CASE_INSIGHTS_PATH` (default: `backend/data/case_insights.json`)
- `NEKX_EMAIL_MODE` (`gemini` or `template`, default: `gemini`)
- `NEKX_EMAIL_FALLBACK_MODE` (`fallback` or `strict`, default: `fallback`)
- `GOOGLE_API_KEY` (required only when Gemini mode is used)
- `NEKX_GEMINI_MODEL` (default: `gemini-2.5-flash`)
- `NEKX_SCHEDULER_CONFIG_PATH` (default: `data/scheduler_config.json`)

## Data model
Core tables:
- `leads`
- `seo_insights`
- `experiments`
- `email_variants`
- `email_events`
- `replies`
- `experiment_results`

## Tools
- `python -m backend.tools.reset_and_import_leads`
- `python -m backend.tools.add_prospect`
- `python -m backend.tools.view_db`
- `python -m backend.tools.demo_gemini`

## Notes
- Step 1 insights are case-based opportunities (not direct technical claims about the prospect website).
- Keep compliance elements in generated emails (identity + unsubscribe).
