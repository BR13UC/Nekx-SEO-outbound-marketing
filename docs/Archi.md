# Nekx SEO - System Architecture (Current)

## Summary
The system is a FastAPI + SQLite outbound experimentation loop with five modules:
1. Lead sourcing and storage.
2. SEO opportunity generation.
3. Email generation.
4. Email sending and event capture.
5. Experiment and A/B test analytics.

## Runtime Flow
```text
Lead source -> leads table
          -> SEO opportunity generation (case-based today)
          -> email generation (Gemini or template)
          -> send flow + email events
          -> analytics + experiment learning
```

## Execution Paths
### API-driven path
- Admin/API creates or updates leads and experiments.
- `/seo/analyze` creates insights in `seo_insights`.
- `/emails/generate` creates `email_variants` rows.
- `/emails/send` updates delivery status and event stream.

### Scheduler path
- Built-in scheduler thread starts with FastAPI app startup.
- Manual/cron runner is available via `backend.tools.run_outbound_cycle`.
- Scheduler config is JSON-based and supports throttling via `min_interval_minutes`.

## Current SEO Insight Strategy
External live SEO API access is not active yet. Step 1 uses a local benchmark snapshot:
- Source file: `backend/data/case_insights.json`
- Behavior: generate evidence-based opportunity statements
- Guardrail: no direct technical error claims without a live audit

This keeps the same downstream schema and API contracts while reducing claim risk.

## API Layer
Base prefix: `/api/v1`

### Leads and SEO
- `POST /leads`
- `GET /leads`
- `GET /leads/{lead_id}`
- `PATCH /leads/{lead_id}`
- `GET /leads/segments`
- `GET /leads/sources`
- `GET /leads/countries`
- `POST /seo/analyze`
- `GET /seo/{lead_id}`

### Experiments and A/B Tests
- `POST /experiments`
- `GET /experiments`
- `GET /experiments/options`
- `GET /experiments/{experiment_id}/results`
- `POST /ab-tests`
- `GET /ab-tests`
- `GET /ab-tests/{ab_test_id}/results`
- `GET /ab-tests/{ab_test_id}/details`

### Email, Webhooks, Analytics, Scheduler
- `POST /emails/generate`
- `GET /emails/{email_id}`
- `POST /emails/send`
- `POST /webhooks/email`
- `GET /analytics/summary`
- `GET /analytics/segments`
- `GET /analytics/messaging`
- `GET /analytics/recent-emails`
- `GET /analytics/queue`
- `GET /analytics/activity`
- `GET /analytics/cron-status`
- `GET /scheduler/config`
- `PATCH /scheduler/config`
- `POST /scheduler/run`

## Data Model
### `leads`
Prospect records and lifecycle status (`new`, `written`, `contacted`).

### `seo_insights`
Generated opportunity statements per lead.

### `experiments`
Baseline matrix dimensions (`segment`, `messaging_angle`, `email_format`) plus optional caps.

### `ab_tests` and `ab_test_variants`
A/B test definitions and side-specific variants (`A`, `B`) with allocation limits.

### `email_variants`
Generated outreach content linked to lead and experiment or A/B context.

### `email_events`
Delivery and engagement events (`ready`, `sent`, `opened`, `replied`) with provider IDs when available.

### `replies`
Captured replies and sentiment metadata.

### `experiment_results`
Aggregated per-experiment metrics.

## Service Responsibilities
- `backend/services/seo_service.py`: case-based opportunity generation.
- `backend/services/email_service.py`: main rendering orchestration and fallback behavior.
- `backend/services/gemini_service.py`: Gemini prompt composition and model invocation.

## Configuration
- `NEKX_EMAIL_MODE=gemini|template`
- `NEKX_EMAIL_FALLBACK_MODE=fallback|strict`
- `GOOGLE_API_KEY`
- `NEKX_GEMINI_MODEL`
- `NEKX_CASE_INSIGHTS_PATH`
- `NEKX_LEADS_XLSX_PATH`
- `NEKX_DB_PATH`
- `NEKX_SCHEDULER_CONFIG_PATH`

## Upgrade Path
When live SEO APIs are available, swap Step 1 analysis implementation while preserving contracts for:
- `seo_insights` table shape
- `/seo/analyze` and `/seo/{lead_id}` endpoints
- downstream email generation inputs
