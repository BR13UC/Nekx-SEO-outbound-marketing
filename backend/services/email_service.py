from __future__ import annotations

from typing import Any, Dict, List, Tuple

from ..config import settings
from .gemini_service import GeminiEmailGenerator


class EmailService:
    def __init__(self) -> None:
        self._gemini: GeminiEmailGenerator | None = None

    def render_email(
        self,
        lead: Dict[str, Any],
        experiment: Dict[str, Any],
        insights: List[Dict[str, Any]],
        language: str = "en",
    ) -> Tuple[str, str]:
        chosen_language = (language or "en").strip() or "en"
        mode = settings.email_mode

        if mode == "template":
            return self._render_with_template(lead, experiment, insights, language=chosen_language)

        try:
            generator = self._get_gemini_generator()
            return generator.generate_email(lead, experiment, insights, language=chosen_language)
        except Exception as exc:
            if settings.strict_email_mode:
                raise RuntimeError(f"Gemini generation failed and strict mode is enabled: {exc}") from exc
            return self._render_with_template(lead, experiment, insights, language=chosen_language)

    def _get_gemini_generator(self) -> GeminiEmailGenerator:
        if self._gemini is not None:
            return self._gemini

        if not settings.gemini_api_key:
            raise RuntimeError("GOOGLE_API_KEY is missing for Gemini mode.")

        self._gemini = GeminiEmailGenerator(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
        )
        return self._gemini

    def _render_with_template(
        self,
        lead: Dict[str, Any],
        experiment: Dict[str, Any],
        insights: List[Dict[str, Any]],
        language: str = "en",
    ) -> Tuple[str, str]:
        company = lead.get("company", "there")
        website = lead.get("website", "")
        email_format = str(experiment.get("email_format", "short")).lower()

        subject = experiment.get("subject_variant") or f"Case-based SEO idea for {company}"

        if insights:
            bullets = "\n".join([f"- {i['issue_description']}" for i in insights])
        else:
            bullets = "- We may be able to improve local discoverability based on similar cases."

        prefix = "Hi"
        if language.lower().startswith("fr"):
            prefix = "Bonjour"
        elif language.lower().startswith("nl"):
            prefix = "Hallo"

        body = f"""{prefix} {company},

I looked at your market context around {website} and put together a few opportunities based on comparable client cases:
{bullets}

If useful, I can share a short walkthrough with practical next steps and expected impact ranges.

Best,
Nekx SEO

Unsubscribe: reply with \"unsubscribe\" and I will not contact you again.
"""

        if email_format == "medium":
            body += "\nPS: If any point is already handled, reply and I will adjust the recommendations."

        return subject, body


_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


def render_email(
    lead: Dict[str, Any],
    experiment: Dict[str, Any],
    insights: List[Dict[str, Any]],
    language: str = "en",
) -> Tuple[str, str]:
    service = get_email_service()
    return service.render_email(lead, experiment, insights, language=language)
