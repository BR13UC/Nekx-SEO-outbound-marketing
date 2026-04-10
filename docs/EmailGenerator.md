# Email Generation Module (Current)

The unified email generation flow now lives fully in `backend/services/`:

- `backend/services/email_service.py`
- `backend/services/gemini_service.py`

## Modes
- `NEKX_EMAIL_MODE=gemini` (default)
- `NEKX_EMAIL_MODE=template`

Fallback behavior:
- `NEKX_EMAIL_FALLBACK_MODE=fallback` (default): fallback to template on Gemini errors
- `NEKX_EMAIL_FALLBACK_MODE=strict`: raise error instead of fallback

## Local smoke test
```bash
python -m backend.tools.demo_gemini --lead-id 1 --experiment-id 1
```

The service keeps compliance constraints in prompt/template output:
- clear sender identity
- unsubscribe instruction
- cautious wording for case-based opportunities
