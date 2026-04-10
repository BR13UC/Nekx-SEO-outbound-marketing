# Nekx SEO - Technical Plan

## Goal
Build a compliant, auditable outbound experimentation engine that improves outreach performance over time by learning which combinations of:
- segment
- messaging angle
- email format

perform best.

## Implementation Phases
### Phase 0 (Current)
- FastAPI + SQLite baseline operational.
- Lead CRUD, SEO insight generation, email generation, send stub, analytics endpoints.
- A/B testing entities and scheduling loop implemented.
- Admin cockpit available.

### Phase 1 (Near-term hardening)
- Improve event ingestion realism (provider webhooks and event reconciliation).
- Enforce stronger data quality checks on lead inputs.
- Expand test coverage around scheduler and attribution edges.
- Improve audit exports and retention/deletion operations.

### Phase 2 (Delivery integration)
- Replace send stub with real provider integration (Resend preferred).
- Track provider IDs and status transitions end-to-end.
- Add retry, idempotency, and dead-letter/error observability.

### Phase 3 (SEO intelligence upgrade)
- Introduce external SEO API for live site checks.
- Keep case-based fallback when API unavailable.
- Preserve cautious language unless findings are confirmed.

### Phase 4 (Optimization)
- Add baseline-safe optimization (random within constraints first).
- Optionally introduce scoring or lightweight bandits after attribution reliability is proven.

## Module Plan
### 1) Lead Sourcing
Input channels:
- client-provided lead files (preferred)
- curated internal sourcing

Required fields:
- `company`
- `contact_email`
- `website`
- `segment`

Optional but recommended:
- `industry`
- `country`
- `source`

### 2) SEO Analysis
Current mode:
- case-benchmark opportunity statements from local snapshot.

Target mode:
- live SEO checks via external API.

Constraints:
- avoid fabricated technical assertions
- prefer actionable, concise insights (1-3 per lead)

### 3) Email Generation
Inputs:
- lead profile
- selected variant (`experiment` or `ab-test side`)
- SEO opportunities

Output constraints:
- concise and factual
- clear sender identity
- unsubscribe path
- cautious wording when insights are probabilistic

### 4) Email Sending
Current:
- stub send flow for lifecycle wiring.

Target:
- real provider, webhook processing, accurate sent/open/reply attribution.

### 5) Experiment Engine
Track and compare:
- sent rate
- open rate
- reply rate
- positive reply indicators

Attribution requirement:
- each email mapped to `lead_id` + variant context (`experiment_id` or `ab_test_id` + `ab_side`).

## Compliance and Governance
- GDPR principles: minimization, purpose, retention, deletion.
- Dutch B2B outreach requirements: relevance, identity, opt-out.
- Human-in-the-loop on irreversible or high-volume actions.

## Technology Stack
- Python
- FastAPI
- SQLite
- Gemini API (default model path) with template fallback

## Success Criteria
- Reliable end-to-end attribution for generated and sent emails.
- Measurable weekly learning on variant performance.
- No compliance regressions in generated outreach content.
