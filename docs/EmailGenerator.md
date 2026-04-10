# Email Generation Module (Current)

The email generation stack is implemented in:
- `backend/services/email_service.py`
- `backend/services/gemini_service.py`

## Modes
- `NEKX_EMAIL_MODE=gemini` (default)
- `NEKX_EMAIL_MODE=template`

Fallback behavior:
- `NEKX_EMAIL_FALLBACK_MODE=fallback` (default): fallback to template on Gemini errors.
- `NEKX_EMAIL_FALLBACK_MODE=strict`: return generation error instead of fallback.

## Inputs Used by Generator
- lead profile (`company`, `website`, `segment`, optional `industry`, `country`)
- variant context (experiment or A/B variant attributes)
- up to 3 SEO opportunities from `seo_insights`

## Output Contract
- one subject line
- one concise email body
- compliance elements included:
  - sender identity
  - unsubscribe path/instruction

## Guardrails
- no fabricated technical findings
- cautious language for case-based opportunities (`may`, `could`, `likely`)
- concise, practical CTA

## Local Smoke Test
```bash
python -m backend.tools.demo_gemini --lead-id 1 --experiment-id 1
```

## Operational Advice
- Use `fallback` mode in local/dev environments for resilience.
- Use `strict` mode in controlled QA when validating model dependencies and error handling.
