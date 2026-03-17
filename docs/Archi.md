# Nekx SEO – System Architecture

- [High-Level Architecture](#high-level-architecture)
- [Status (MVP)](#status-mvp)
- [System Workflow](#system-workflow)
- [Core Modules](#core-modules)
    - [1. Lead Sourcing](#1-lead-sourcing)
    - [2. SEO Analysis Module](#2-seo-analysis-module)
    - [3. Email Generation Module](#3-email-generation-module)
    - [4. Email Sending Module](#4-email-sending-module)
    - [5. Experiment Engine](#5-experiment-engine)
- [Database Design](#database-design)
- [Database Schema](#database-schema)
    - [Table: leads](#table-leads)
    - [Table: seo_insights](#table-seo_insights)
    - [Table: experiments](#table-experiments)
    - [Table: email_variants](#table-email_variants)
    - [Table: email_events](#table-email_events)
    - [Table: replies](#table-replies)
    - [Table: experiment_results](#table-experiment_results)
- [API Design](#api-design)
- [Internal Automation Jobs](#internal-automation-jobs)
- [Future Scalability](#future-scalability)
- [Project Folder Structure](#project-folder-structure)

This document describes the architecture of the AI‑powered outreach system designed for Nekx SEO.

The system is designed as a **data‑driven experimentation engine** that continuously tests outreach strategies and learns which combinations generate the best results.

---

# High‑Level Architecture

The system is composed of five core modules:

1. Lead Sourcing
2. SEO Analysis
3. Email Generation
4. Email Sending
5. Experiment Engine

These modules operate in a loop where leads are collected, analyzed, contacted, and evaluated.

```
Lead Sources → Lead DB → SEO Analysis → Email Generation → Email Sending → Experiment Engine → Strategy Update
```

---

# Status (MVP)

As of **March 17, 2026**, this repository already includes an MVP backend implementation in `backend/`:

Implemented:

* FastAPI app with an `/api/v1` prefix and a health endpoint.
* SQLite database schema aligned with the tables documented below.
* REST endpoints for leads, SEO insights, experiments, email variants, webhooks, and analytics.

Intentionally stubbed for v0:

* Email provider integration (e.g., Resend): `/emails/send` currently marks an email as sent and logs a `sent` event in the DB.

Planned next steps (docs-only; not implemented yet):

* Real provider sending + event ingestion hardening (signature verification, idempotency).
* Stronger SEO analysis via external SEO API and/or richer internal checks.
* Production compliance additions (opt-out storage, retention/deletion workflows, auth).

---

# System Workflow

The system runs continuously in cycles:

1. Collect new leads
2. Store leads in database
3. Run SEO analysis on website
4. Select experiment variant
5. Generate outreach email
6. Send email
7. Track events (open, reply, conversion)
8. Update experiment performance
9. Improve strategy

---

# Core Modules

## 1. Lead Sourcing

Responsible for collecting potential prospects.

Possible sources:

* Public company directories
* Company websites
* Google Maps listings
* LinkedIn
* Client‑provided lead lists

Each lead is stored with structured data.

### Lead Data Model

```
company
contact_email
segment
website
country
industry
```

Example segments:

* Dutch SMBs
* Local businesses
* SEO agencies
* E‑commerce companies
* Privacy‑focused organizations

---

# 2. SEO Analysis Module

Before outreach, the system generates a **short SEO insight** about the company website.

Possible checks:

* missing meta tags
* missing structured data
* slow page speed
* weak titles or descriptions
* lack of AI visibility signals

Two approaches:

External SEO API (preferred)

or

Internal lightweight crawler.

These insights are stored and later used to personalize emails.

---

# 3. Email Generation Module

Emails are generated dynamically using the **OpenAI API**.

Inputs to generation:

```
company
segment
seo_issue
messaging_angle
experiment_variant
```

Example:

```
company: DentalCare Rotterdam
segment: local_business
seo_issue: missing structured data
angle: local visibility
```

The system generates a **short personalized outreach email**.

---

# 4. Email Sending Module

Emails are sent using a transactional email provider.

Chosen provider:

Resend API

Features required:

* send email variants
* open tracking
* reply tracking
* event logging

Each email is linked to an experiment and lead.

Note (current MVP): the `/emails/send` endpoint is a stub that updates `sent_at` and inserts a `sent` event.
Provider events (e.g., opened/replied) can be ingested via the email webhook.

---

# 5. Experiment Engine

The experiment engine evaluates campaign performance.

### Metrics

* open rate
* reply rate
* positive reply rate
* conversions

### Experiment Dimensions

```
Segment × Messaging Angle × Email Format
```

Example:

| Segment | Angle         | Format |
| ------- | ------------- | ------ |
| SMB     | Cost savings  | Short  |
| SMB     | AI visibility | Medium |
| Agency  | White label   | Short  |

The engine progressively identifies the **best‑performing combinations**.

---

# Database Design

The system uses a relational database.

Initial choice:

SQLite

Future scaling:

PostgreSQL

---

# Database Schema

## Table: leads

Stores all prospects.

```
lead_id (PK)
company
contact_email
website
segment
industry
country
source
created_at
status
```

status examples:

* new
* contacted
* replied
* converted

---

## Table: seo_insights

Stores SEO issues discovered during analysis.

```
insight_id (PK)
lead_id (FK)
issue_type
issue_description
severity
created_at
```

Example issue types:

* missing_meta
* missing_schema
* slow_pages
* weak_titles

---

## Table: experiments

Defines experiment variants.

```
experiment_id (PK)
segment
messaging_angle
email_format
subject_variant
created_at
active
```

---

## Table: email_variants

Stores generated emails.

```
email_id (PK)
lead_id (FK)
experiment_id (FK)
subject
content
created_at
sent_at
```

---

## Table: email_events

Tracks events from the email provider.

```
event_id (PK)
email_id (FK)
event_type
provider_id
event_time
```

Possible events:

* sent
* delivered
* opened
* replied
* bounced

---

## Table: replies

Stores email responses.

```
reply_id (PK)
email_id (FK)
lead_id (FK)
reply_text
sentiment
created_at
```

Sentiment values:

* positive
* neutral
* negative

---

## Table: experiment_results

Aggregated metrics per experiment.

```
result_id (PK)
experiment_id (FK)
opens
replies
positive_replies
conversions
updated_at
```

---

# API Design

The backend exposes REST endpoints to interact with the system.

Base path:

```
/api/v1/
```

---

# Lead Management Endpoints

### Create Lead

POST `/leads`

Input:

```
company
contact_email
website
segment
industry
country
```

---

### List Leads

GET `/leads`

Optional filters:

```
segment
industry
status
```

---

### Get Lead

GET `/leads/{lead_id}`

---

### Update Lead

PATCH `/leads/{lead_id}`

---

# SEO Analysis Endpoints

### Run SEO Analysis

POST `/seo/analyze`

Input:

```
lead_id
website
```

Output:

SEO insights stored in database.

---

### Get SEO Insights

GET `/seo/{lead_id}`

---

# Email Generation Endpoints

### Generate Email

POST `/emails/generate`

Input:

```
lead_id
experiment_id
```

Output:

Generated email stored in database.

---

### Get Email

GET `/emails/{email_id}`

---

# Email Sending Endpoints

### Send Email

POST `/emails/send`

Input:

```
email_id
```

Current v0 behavior:

* marks the email as sent (`sent_at`)
* logs a `sent` event in `email_events`
* does not call an external provider yet

---

### Email Webhook

POST `/webhooks/email`

Used by the email provider to send events.

Stores:

* opens
* replies
* bounces

Implementation note:

* `event_type="replied"` can optionally include `reply_text` (and `sentiment`) which will be inserted into `replies`.

---

# Experiment Engine Endpoints

### Create Experiment

POST `/experiments`

Input:

```
segment
messaging_angle
email_format
subject_variant
```

---

### List Experiments

GET `/experiments`

---

### Get Experiment Results

GET `/experiments/{id}/results`

---

# Analytics Endpoints

### Performance Summary

GET `/analytics/summary`

Returns:

Lightweight v0 counts (rates can be derived client-side):

* sent
* opened
* replied

---

### Segment Performance

GET `/analytics/segments`

---

### Messaging Performance

GET `/analytics/messaging`

---

# Internal Automation Jobs

These processes run via cron or workers.

Lead discovery job

```
collect leads → insert into leads table
```

SEO analysis job

```
analyze websites → store seo_insights
```

Email generation job

```
select leads + experiments → generate emails
```

Email sending job

```
send emails via provider
```

Metrics aggregation job

```
update experiment_results
```

---

# Future Scalability

If the system scales, improvements include:

Database

SQLite → PostgreSQL

Background jobs

Cron → Celery / Redis queue

Experiment optimization

* multi‑armed bandits
* Bayesian optimization

Lead generation

* automated scraping pipelines
* external lead APIs

---

# Project Folder Structure

Current repository structure (implemented today + planned `(futur)`), using the target layout style:

```
nekx-outreach-agent/
    backend/
        main.py
        config.py
        database.py
        requirements.txt

        models/ (futur)
            lead.py (futur)
            seo_insight.py (futur)
            experiment.py (futur)
            email_variant.py (futur)
            email_event.py (futur)
            reply.py (futur)

        routes/
            leads_routes.py
            seo_routes.py
            email_routes.py
            experiments_routes.py
            analytics_routes.py
            webhooks_routes.py

        schemas/
            lead_schema.py
            seo_schema.py
            email_schema.py
            experiment_schema.py
            webhook_schema.py

        services/
            lead_service.py (futur)
            seo_service.py
            email_service.py
            email_generation_service.py (futur)
            email_sending_service.py (futur)
            experiment_service.py (futur)
            analytics_service.py (futur)

        workers/ (futur)
            lead_discovery_worker.py (futur)
            seo_analysis_worker.py (futur)
            email_generation_worker.py (futur)
            email_sending_worker.py (futur)
            metrics_worker.py (futur)

        integrations/ (futur)
            openai_client.py (futur)
            resend_client.py (futur)

        utils/ (futur)
            logging.py (futur)
            helpers.py (futur)

        tools/
            add_prospect.py
            view_db.py

    data/
        nekx.db   (default local path via `NEKX_DB_PATH` override)

    migrations/ (futur)

    scripts/ (futur)
        seed_experiments.py (futur)
        seed_segments.py (futur)

    configs/ (futur)
        prompts/ (futur)
            email_prompt.txt (futur)

    docs/
        Archi.md
        Plan.md

    README.md
    AGENTS.md
    ARCHITECTURE.md (futur)
    PLAN.md (futur)
```

This structure separates:

* **routes** → API endpoints
* **services** → business logic
* **schemas** → request/response validation
* **tools** → local CLI helpers (DB ops)

---

# What Can Be Built Before Having All Project Inputs

Even without final project details, several components can already be developed.

## 1. Database Layer

You can already implement:

* schema evolution strategy (migrations) once needed
* seed scripts for experiments and segments

Tables that are safe to implement early:

* leads
* seo_insights
* experiments
* email_variants
* email_events
* replies
* experiment_results

---

## 2. Core API Skeleton

The backend API skeleton can be implemented early (and largely already exists).

Core endpoints:

```
POST   /api/v1/leads
GET    /api/v1/leads
GET    /api/v1/leads/{id}
PATCH  /api/v1/leads/{id}

POST   /api/v1/experiments
GET    /api/v1/experiments

POST   /api/v1/emails/generate
POST   /api/v1/emails/send
POST   /api/v1/webhooks/email
```

---

## 3. Experiment Engine Logic

You can implement the logic that selects which experiment to run.

For example:

* random experiment selection
* round-robin experiments
* weighted experiments

Later this can evolve into:

* multi-armed bandits
* Bayesian optimization

---

## 4. Email Prompt System

You can design the prompt templates used by the AI.

Example prompt inputs:

```
company
industry
seo_issue
messaging_angle
segment
```

This allows testing email generation early.

---

## 5. Mock / Stub Integrations

Before having real integrations you can build mock services.

Examples:

SEO analysis mock

```
returns fake SEO issues
```

Email sending stub (current v0 behavior)

```
marks emails as sent + logs events
```

This allows full system testing without external dependencies.

---

# Summary

The architecture enables development to start immediately even without all project inputs.

The following parts can be implemented right away:

* database schema + migration approach
* API skeleton
* experiment engine selection logic
* prompt templates
* background automation jobs

This preparation allows the team to move quickly once real data sources and integrations become available.
