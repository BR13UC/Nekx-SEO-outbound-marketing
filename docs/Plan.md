# Nekx SEO – Technical Plan

- [System Goal](#system-goal)
- [System Architecture](#system-architecture)
- [1. Lead Sourcing](#1-lead-sourcing)
- [2. SEO Analysis](#2-seo-analysis)
- [3. Email Generation](#3-email-generation)
- [4. Email Sending](#4-email-sending)
- [5. Experiment Engine](#5-experiment-engine)
- [System Workflow](#system-workflow)
- [Technological Stack](#technological-stack)

## System Goal

The goal of the system is to automatically test:

- different **target audiences**
- different **email messages**
- different **email formats**

and identify which combinations generate the best results.

The system should progressively learn and converge toward the most effective outreach strategy.

---

# System Architecture

The system consists of five main modules.

---

# 1. Lead Sourcing

The system collects potential prospects.

Initial segments:

- Dutch SMBs (5–50 employees)
- Local businesses
- Privacy-focused organisations
- SEO / web agencies
- E-commerce companies

However, the system should experiment to determine which segments perform best.

### Lead Structure

- company
- contact_email
- segment
- website
- country
- industry


### Possible Lead Sources

Option 1 – Client-provided leads (ideal)

Nekx provides a list of companies to contact.

Option 2 – Generated leads

- Public company directories
- Company websites
- Google Maps / local listings
- LinkedIn scraping
- Client-provided lead lists

---

# 2. SEO Analysis

Before sending outreach emails, the system must gather insights about the prospect's website.

Two possible approaches exist.

### Option 1 – External SEO API (ideal)

Use a Nekx API or third-party SEO tool to obtain:

- SEO score
- missing metadata
- site performance issues
- schema markup issues
- content gaps

### Option 2 – Internal SEO Analysis

Generate simple SEO insights internally by analyzing:

- page titles
- meta descriptions
- page speed
- mobile friendliness
- structured data

This approach is technically more complex.

---

# 3. Email Generation

The system generates outreach emails based on an **experiment matrix**.

Each experiment tests combinations of:

- audience segment
- messaging angle
- SEO insight
- email format
- subject line
- call-to-action

### Example Experiment Matrix

| Segment | Messaging Angle | Version |
|--------|----------------|--------|
| SMB | Cost savings | A |
| SMB | AI visibility | B |
| Agencies | White-label execution | A |
| Local business | Local SEO automation | A |

### Messaging Angles

Possible angles include:

- Cost savings
- Time savings
- Data sovereignty (EU hosting)
- AI visibility
- Execution vs tools
- Local visibility

---

# 4. Email Sending

Emails are sent using an email delivery provider.

Possible tools:

- SMTP
- SendGrid
- Mailgun
- Resend

Required features:

- sending email variants
- open tracking
- reply tracking
- conversion tracking

Emails must comply with:

- GDPR
- Dutch telecom law
- business-only outreach policies

---

# 5. Experiment Engine

This module evaluates campaign performance.

It logs experiments and determines which strategies work best.

### Metrics Tracked

- open rate
- reply rate
- positive replies
- conversions

### Evaluation Model

Experiments are evaluated based on:
`Segment × Messaging Angle × Email Format`


The system progressively identifies the best-performing combinations.

---

# System Workflow

The system runs in cycles.

1. Collect new leads
2. Assign segment
3. Select experiment variant
4. Generate email
5. Send email
6. Track results
7. Update experiment scores
8. Adjust strategy

---

# Technological Stack

## Backend

Python  
FastAPI  
SQLite

### Why

Python is well suited for automation and AI workflows.

FastAPI provides a lightweight backend API.

SQLite allows simple storage of:

- leads
- experiments
- campaign results

---

## Automation

Cron jobs + Python scripts

### Why

Cron jobs allow scheduled tasks such as:

- collecting leads
- sending emails
- updating metrics
- recalculating experiment performance

If the system scales later, task queues like **Celery** could be introduced.

---

## Email Generation

OpenAI API

### Why

The OpenAI API allows dynamic generation of personalized outreach emails based on:

- company information
- messaging angle
- SEO insights

This makes rapid experimentation possible.

---

## Email Sending

Resend API

### Why

Resend provides a developer-friendly API for sending transactional emails and tracking events.

Features include:

- delivery tracking
- event logging
- easy integration with Python

---

## Analytics

SQLite + internal dashboard

### Why

All experiment data is stored in the database.

Metrics can be analyzed using SQL queries.

A lightweight dashboard can display:

- open rates
- reply rates
- conversions
- segment performance

---