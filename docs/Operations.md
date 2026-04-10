# Operations Guide

## 1) Reset + Import
```bash
python -m backend.tools.reset_and_import_leads \
  --db-path data/nekx.db \
  --xlsx-path data/groningen_food_drink_leads.xlsx
```

Expected outcome:
- outreach tables reset
- 64 leads imported
- baseline experiments seeded from discovered segments

## 2) Start API
```bash
uvicorn backend.main:app --reload
```

## 3) Generate case-based insights
```bash
curl -X POST http://127.0.0.1:8000/api/v1/seo/analyze \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1}'
```

## 4) Generate email
```bash
curl -X POST http://127.0.0.1:8000/api/v1/emails/generate \
  -H 'Content-Type: application/json' \
  -d '{"lead_id": 1, "experiment_id": 1}'
```

## 5) Mark email as sent (stub)
```bash
curl -X POST http://127.0.0.1:8000/api/v1/emails/send \
  -H 'Content-Type: application/json' \
  -d '{"email_id": 1}'
```

## 6) Run one outbound cycle (manual)
```bash
python -m backend.tools.run_outbound_cycle
```

Dry run:
```bash
python -m backend.tools.run_outbound_cycle --dry-run
```

## 7) Configure scheduler throttle
Default file: `data/scheduler_config.json`

```json
{
  "enabled": true,
  "min_interval_minutes": 30,
  "log_level": "INFO",
  "log_file_path": "data/outbound_scheduler.log"
}
```

## 8) Cron setup
Run every minute (actual send frequency controlled by `min_interval_minutes`):
```bash
* * * * * cd /home/brieuc/AIAndYourProfession/Nekx-SEO-outbound-marketing && ./.venv/bin/python -m backend.tools.run_outbound_cycle >> /tmp/nekx-cron.log 2>&1
```

## Troubleshooting
### GOOGLE_API_KEY missing
Symptom:
- Gemini mode cannot generate

Behavior:
- fallback mode (`NEKX_EMAIL_FALLBACK_MODE=fallback`): template is used automatically
- strict mode (`NEKX_EMAIL_FALLBACK_MODE=strict`): API returns generation error

### Import fails due to missing columns
Check the Excel header includes:
- `company`
- `contact_email`
- `website`
- `segment`

### DB path mismatch
Set `NEKX_DB_PATH` explicitly or pass `--db-path` to the import tool.

### Invalid scheduler JSON
Symptom:
- scheduler exits with code `2`

Behavior:
- logs a structured `invalid_json_config` error
- does not write outreach data
