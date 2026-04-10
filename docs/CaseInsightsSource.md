# Case Insights Source Mapping

## Purpose
This document explains how Step 1 insight generation is currently sourced while direct client SEO API access is unavailable.

## Input source
- Raw source: Nekx result page HTML snapshot provided in project conversation
- Structured snapshot: `backend/data/case_insights.json`

## Extracted benchmark blocks
### Global counters
- Cases: 4
- Screenings: 648K
- Clicks: 11.7K
- Measurement period: 3 months

### Case 1 - Dental Care Drenthe
- Homepage visitors: +41%
- Team page visitors: +192%
- Erica location visitors: +292%
- Meppel location visitors: +294%
- Qualitative note: 0 hours of own work

### Case 2 - SealteQ
- SealteQ South (Geleen) visitors: +236%
- Working with visitors: +43%
- DE: Fundament Sanierung visitors: +1620%
- Kwaaitaal floor visitors: +655%

### Case 3 - Beauty Institute Amice
- Homepage visitors: +55%
- Cryolipolysis visitors: +33%
- About us visitors: +125%
- Clicks: +21%

### Case 4 - Kardewu
- Homepage visitors: +31%
- Philing's course visitors: +25%
- Clicks: +29%
- General screenings: +44%

## How Step 1 uses these values
`backend/services/seo_service.py` maps lead segment/industry to tags and selects comparable cases.

It then creates 1-3 opportunity statements with these rules:
- evidence-based benchmark references
- cautious language (`may`, `could`, `likely`)
- no direct claim of discovered technical errors without live audit

## Upgrade path
When live SEO data is available, keep this file as fallback benchmark context and route primary analysis to the real API.
