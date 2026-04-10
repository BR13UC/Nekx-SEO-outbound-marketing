from __future__ import annotations

import json
from typing import Any, Dict, List

from google import genai
from google.genai import types


class GeminiEmailGenerator:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_email(
        self,
        lead: Dict[str, Any],
        experiment: Dict[str, Any],
        insights: List[Dict[str, Any]],
        language: str = "en",
    ) -> tuple[str, str]:
        prompt = self._build_prompt(lead, experiment, insights, language=language)

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.8,
                top_p=0.95,
                max_output_tokens=1200,
            ),
        )
        return self._parse_response(response.text, lead.get("company", "your company"))

    def _build_prompt(
        self,
        lead: Dict[str, Any],
        experiment: Dict[str, Any],
        insights: List[Dict[str, Any]],
        language: str = "en",
    ) -> str:
        company = str(lead.get("company") or "there")
        website = str(lead.get("website") or "")
        industry = str(lead.get("industry") or lead.get("segment") or "business")
        angle = str(experiment.get("messaging_angle") or "SEO growth")
        email_format = str(experiment.get("email_format") or "short").lower()

        length_hint = {
            "short": "120-170 words",
            "medium": "190-260 words",
            "long": "300-380 words",
        }.get(email_format, "120-170 words")

        insights_text = "\n".join(
            f"- {i.get('issue_description', '')}" for i in insights if i.get("issue_description")
        ) or "- No case-based insights available yet."

        target_language = (language or "en").strip() or "en"

        return f"""You are an SEO outreach specialist at Nekx SEO.

Write one personalized B2B cold email in language code "{target_language}".

Prospect:
- Company: {company}
- Website: {website}
- Industry/segment: {industry}

Experiment style:
- Messaging angle: {angle}
- Target length: {length_hint}

Context insights (from comparable client cases):
{insights_text}

Important compliance and quality rules:
1. Do NOT claim you audited this prospect website directly.
2. Present insights as probable opportunities based on comparable cases.
3. Use cautious language: may, could, likely, opportunity.
4. Include clear sender identity: Nekx SEO.
5. Include a simple unsubscribe line.
6. Keep tone human, concrete, and non-spammy.
7. Mention at most 2-3 concrete opportunities.
8. End with one low-friction CTA question.

Return STRICT JSON with this schema only:
{{"subject": "...", "body": "..."}}
"""

    def _parse_response(self, raw_text: str, company: str) -> tuple[str, str]:
        text = (raw_text or "").strip()
        if not text:
            return (f"Quick SEO growth idea for {company}", "Hi,\n\nCould we share a quick SEO growth idea?")

        try:
            parsed = json.loads(text)
            subject = str(parsed.get("subject") or "").strip()
            body = str(parsed.get("body") or "").strip()
            if subject and body:
                return subject, body
        except Exception:
            pass

        subject = ""
        body_lines: list[str] = []
        in_body = False
        for line in text.splitlines():
            upper = line.upper().strip()
            if upper.startswith("SUBJECT:"):
                subject = line.split(":", 1)[1].strip().strip('"')
                continue
            if upper.startswith("BODY:"):
                in_body = True
                continue
            if in_body:
                body_lines.append(line)

        body = "\n".join(body_lines).strip() if body_lines else text
        if not subject:
            subject = f"Quick SEO growth idea for {company}"
        return subject, body
