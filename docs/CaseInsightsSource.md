# Case Insights Source Mapping

## Purpose
This document describes how Step 1 SEO opportunity generation currently works while live external SEO APIs are not yet integrated.

## Input Source
- Raw source: Nekx case/result page snapshot provided during project setup.
- Structured data file: `backend/data/case_insights.json`.

## Benchmark Blocks (Current Snapshot)
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
- Qualitative note: 0 hours own work

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

## How Step 1 Uses This Data
`backend/services/seo_service.py` maps lead segment/industry to comparable case tags, then generates 1-3 concise opportunity statements.

Rules:
- reference benchmark evidence
- use cautious language (`may`, `could`, `likely`)
- do not claim direct technical errors without live audit evidence

Generated outputs are stored in `seo_insights` so downstream routes remain unchanged.

## Upgrade Path
When live SEO data is integrated:
- keep this dataset as fallback context
- route primary analysis to external API results
- preserve cautious language when confidence is partial
