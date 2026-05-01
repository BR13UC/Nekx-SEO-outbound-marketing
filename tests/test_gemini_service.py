import json

from backend.services.gemini_service import GeminiEmailGenerator


LONG_BODY = (
    "Hi Acme,\n\n"
    "Comparable client cases suggest there may be a practical opportunity to improve local SEO visibility. "
    "Could we share a short walkthrough with a few concrete next steps?\n\n"
    "Best,\nNekx SEO\n\nUnsubscribe: reply with unsubscribe."
)


def _parser() -> GeminiEmailGenerator:
    return GeminiEmailGenerator.__new__(GeminiEmailGenerator)


def test_parse_response_accepts_strict_json():
    subject, body = _parser()._parse_response(
        json.dumps({"subject": "Local SEO idea", "body": LONG_BODY}),
        "Acme",
    )

    assert subject == "Local SEO idea"
    assert body == LONG_BODY


def test_parse_response_accepts_fenced_json():
    raw = "```json\n" + json.dumps({"subject": "Fenced subject", "body": LONG_BODY}) + "\n```"

    subject, body = _parser()._parse_response(raw, "Acme")

    assert subject == "Fenced subject"
    assert body == LONG_BODY


def test_parse_response_falls_back_for_truncated_fenced_json():
    raw = '```json\n{"subject": "Broken subject", "body": "Beste team van Acme,\\n\\nMijn naam is [Jouw'

    subject, body = _parser()._parse_response(raw, "Acme")

    assert subject == "Quick SEO growth idea for Acme"
    assert "Could we share a quick SEO growth idea" in body
    assert "```json" not in body
    assert '"body"' not in body


def test_parse_response_keeps_non_json_text_readable():
    raw = "Hello Acme,\n\nThis is a plain text outreach draft."

    subject, body = _parser()._parse_response(raw, "Acme")

    assert subject == "Quick SEO growth idea for Acme"
    assert body == raw


def test_parse_response_empty_uses_safe_fallback():
    subject, body = _parser()._parse_response("", "Acme")

    assert subject == "Quick SEO growth idea for Acme"
    assert "Could we share a quick SEO growth idea" in body
