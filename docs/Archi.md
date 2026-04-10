# Nekx SEO - System Architecture (Current)

## Summary
The system is a 5-module outbound loop backed by SQLite and FastAPI:

1. Lead sourcing/import
2. Case-based SEO opportunity generation
3. Email generation (Gemini-first)
4. Email sending (v0 stub)
5. Experiment tracking and analytics

## Current execution flow
```text
Lead source (Excel) -> SQLite leads
                    -> Step 1: case-based opportunity insights
                    -> Step 2: email generation (Gemini or template fallback)
                    -> Step 3: send stub + events
                    -> analytics + experiment comparison
```

## Step 1 replacement details
Because external client SEO API is not available yet, Step 1 uses a local snapshot:

- source file: `backend/data/case_insights.json`
- origin: provided Nekx result page HTML snapshot
- behavior: generate cautious, evidence-based opportunities from comparable client outcomes
- guardrail: do not assert direct technical errors on prospect websites

Generated entries are still stored in `seo_insights` to preserve the same downstream interface.

## API layer
Base prefix: `/api/v1`

- `POST /leads`
- `GET /leads`
- `GET /leads/{lead_id}`
- `PATCH /leads/{lead_id}`
- `POST /seo/analyze`
- `GET /seo/{lead_id}`
- `POST /experiments`
- `GET /experiments`
- `POST /emails/generate`
- `GET /emails/{email_id}`
- `POST /emails/send`
- `POST /webhooks/email`
- `GET /analytics/summary`

No breaking endpoint changes were introduced.

## Data model
### leads
Prospect records used by the experiment engine.

### seo_insights
Stores Step 1 outputs. In current mode these are case-based opportunity statements.

### experiments
Experiment variants (`segment x messaging_angle x email_format`).

### email_variants
Generated content per `(lead_id, experiment_id)`.

### email_events
Provider lifecycle events (currently includes `sent` from stub flow).

### replies
Captured reply content + sentiment metadata.

### experiment_results
Aggregated performance metrics per experiment.

## Services
- `backend/services/seo_service.py`: case-based insight generation engine
- `backend/services/email_service.py`: unified email service with mode/fallback behavior
- `backend/services/gemini_service.py`: Gemini client and prompt formatting

## Tooling
- `backend/tools/reset_and_import_leads.py`: reset outreach tables, import leads, seed baseline experiments
- `backend/tools/view_db.py`: inspect SQLite content
- `backend/tools/add_prospect.py`: add one lead manually
- `backend/tools/demo_gemini.py`: quick generation smoke test
- `backend/tools/run_outbound_cycle.py`: one cron/manual outbound cycle with scheduler throttle + logs

## Configuration
- `NEKX_EMAIL_MODE=gemini|template`
- `NEKX_EMAIL_FALLBACK_MODE=fallback|strict`
- `GOOGLE_API_KEY`
- `NEKX_GEMINI_MODEL`
- `NEKX_CASE_INSIGHTS_PATH`
- `NEKX_LEADS_XLSX_PATH`
- `NEKX_DB_PATH`
- `NEKX_SCHEDULER_CONFIG_PATH` (JSON config path for outbound cycle cadence/logging)

## Future upgrade path
When client API access becomes available, Step 1 can switch to real website audits while keeping the same table + route contracts.
