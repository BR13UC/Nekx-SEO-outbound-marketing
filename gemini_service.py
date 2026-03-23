"""
Service for generating emails with Google Gemini AI
"""
import os
import random
from typing import Any, Optional

from google import genai
from google.genai import types


class GeminiEmailGenerator:
    """Email generator with Gemini AI"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY missing. Add it to .env or pass as parameter.")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"

    def generate_email(
        self,
        company: str,
        website: str,
        industry: str,
        seo_issues: list[str],
        messaging_angle: str,
        email_format: str = "short"
    ) -> tuple[str, str]:
        """
        Generate a personalized email with Gemini.

        Returns:
            Tuple (subject, body)
        """
        prompt = self._build_prompt(
            company, website, industry, seo_issues, messaging_angle, email_format
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.85,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
            )
        )

        subject, body = self._parse_response(response.text, company)
        return subject, body

    def _build_prompt(
        self,
        company: str,
        website: str,
        industry: str,
        seo_issues: list[str],
        messaging_angle: str,
        email_format: str
    ) -> str:
        """Build a varied, personalized prompt for Gemini."""

        word_targets = {
            "short":  "130 to 160 words",
            "medium": "200 to 260 words",
            "long":   "300 to 380 words",
        }
        word_target = word_targets.get(email_format, "130 to 160 words")

        issues_text = "\n".join([f"- {issue}" for issue in seo_issues])

        opening_styles = [
            f"Open with a very specific observation you made on {company}'s website (mention a real page or element).",
            f"Open by referencing a common challenge for {industry} businesses in the Netherlands right now.",
            f"Open with a short, concrete fact about how {industry} customers search on Google in 2025.",
            f"Open by briefly complimenting something genuinely good about {company} before raising the issues.",
        ]
        opening_instruction = random.choice(opening_styles)

        cta_styles = [
            "Close with a single, easy yes/no question (e.g. 'Would it be useful if I sent you a quick breakdown?').",
            "Close by offering a free 15-minute screen-share to walk through the fixes — no pitch, just value.",
            "Close by offering to send a one-page PDF summary of the issues and recommended fixes.",
            "Close by asking if they have 10 minutes this week — suggest two specific days.",
        ]
        cta_instruction = random.choice(cta_styles)

        prompt = f"""You are a senior SEO outreach specialist at Nekx SEO, a Dutch B2B agency.
Write a complete, professional cold outreach email in English to a prospect.

━━━ PROSPECT DETAILS ━━━
Company name : {company}
Website      : {website}
Industry     : {industry}
Country      : Netherlands

━━━ SEO ISSUES FOUND ON THEIR SITE ━━━
{issues_text}

━━━ ANGLE & FORMAT ━━━
Messaging angle : {messaging_angle}
Target length   : {word_target} — count carefully, do NOT stop early

━━━ WRITING RULES (follow every single one) ━━━
1. {opening_instruction}
2. Write like a smart human colleague — direct, warm, no corporate jargon.
3. Mention at least TWO specific SEO issues from the list above by name.
4. For each issue you mention, add ONE sentence explaining the concrete business impact.
5. {cta_instruction}
6. End with a P.S. line that adds a small extra piece of value or creates mild urgency.
7. Sign off as: "Best,\\nThe Nekx SEO Team\\nnekx.nl"
8. Add an unsubscribe line at the very end: "To unsubscribe, reply with 'unsubscribe'."
9. NEVER use: "I hope this email finds you well", "synergy", "leverage", "game-changer".
10. Subject line: under 55 characters, specific to this company, NOT generic.

━━━ OUTPUT FORMAT — FOLLOW EXACTLY ━━━
SUBJECT: [write the subject line here]
BODY:
[write the full email body here — include greeting, paragraphs, sign-off, P.S., unsubscribe]

Start now. Write the complete email without stopping early:"""

        return prompt

    def _parse_response(self, response_text: str, company: str) -> tuple[str, str]:
        """Parse Gemini response to extract subject and body."""

        lines = response_text.strip().split('\n')
        subject = ""
        body_lines = []
        in_body = False

        for line in lines:
            stripped = line.strip()
            if not in_body and stripped.upper().startswith("SUBJECT:"):
                subject = stripped[len("SUBJECT:"):].strip()
                #Remove surrounding quotes if Gemini added them
                subject = subject.strip('"').strip("'")
            elif not in_body and stripped.upper().startswith("BODY:"):
                in_body = True
            elif in_body:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        #Fallback: if BODY: tag was missing, take everything after the subject line
        if not body and subject:
            after_subject = False
            fallback_lines = []
            for line in lines:
                if after_subject:
                    fallback_lines.append(line)
                if line.strip().upper().startswith("SUBJECT:"):
                    after_subject = True
            body = "\n".join(fallback_lines).strip()

        if not subject:
            subject = f"Quick SEO win for {company}"
        if not body:
            body = response_text.strip()

        return subject, body

    def estimate_cost(self, num_emails: int) -> dict[str, Any]:
        avg_input_chars = 1100
        avg_output_chars = 900

        total_input_chars = num_emails * avg_input_chars
        total_output_chars = num_emails * avg_output_chars

        input_cost = (total_input_chars / 1000) * 0.00025
        output_cost = (total_output_chars / 1000) * 0.0005
        total_cost = input_cost + output_cost

        return {
            "num_emails": num_emails,
            "total_cost_usd": round(total_cost, 4),
            "cost_per_email_usd": round(total_cost / num_emails, 6),
            "note": "Gemini 2.5 Flash — generous free tier.",
            "free_tier_info": "10 requests/minute free"
        }


def create_gemini_generator(api_key: Optional[str] = None) -> GeminiEmailGenerator:
    return GeminiEmailGenerator(api_key)