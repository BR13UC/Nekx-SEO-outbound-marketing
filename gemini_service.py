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
            raise ValueError("GOOGLE_API_KEY missing.")
        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"

    def generate_email(
        self,
        company: str,
        website: str,
        industry: str,
        seo_issues: list[str],
        messaging_angle: str,
        email_format: str = "short",
        language: str = "en"
    ) -> tuple[str, str]:
        """
        Generate a personalized email with Gemini.

        Returns:
            Tuple (subject, body)
        """

        prompt = self._build_prompt(
            company, website, industry, seo_issues, messaging_angle, email_format, language
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
        return self._parse_response(response.text, company)

    def _build_prompt(self, company, website, industry, seo_issues, messaging_angle, email_format, language) -> str:
        lang_name = "Dutch (Nederlands)" if language == "nl" else "English"
        word_targets = {
            "short": "130 to 160 words",
             "medium": "200 to 260 words",
             "long": "300 to 380 words"
        }
        word_target = word_targets.get(email_format, "130 to 160 words")
        issues_text = "\n".join([f"- {issue}" for issue in seo_issues])

        opening_styles = [
            f"Open with a very specific observation you made on {company}'s website.",
            f"Open by referencing a common challenge for {industry} businesses in the Netherlands,particularly in Groningen.",
            f"Open with a short, concrete fact about how {industry} customers search on Google in 2025.",
            f"Open by briefly complimenting something genuinely good about {company} before raising the issues.",
        ]
        opening_instruction = random.choice(opening_styles)

        cta_styles = [
            "Close with a single, easy yes/no question.",
            "Close by offering a free 15-minute screen-share to walk through the fixes.",
            "Close by offering to send a one-page PDF summary.",
            "Close by asking if they have 10 minutes this week.",
        ]
        cta_instruction = random.choice(cta_styles)

        #PROMPT
        return f"""You are a senior SEO outreach specialist at Nekx SEO, a Dutch B2B agency.
        Write a complete, professional cold outreach email in {lang_name} to a prospect.
        
        ━━━ PROSPECT DETAILS ━━━
        Company name : {company}
        Website      : {website}
        Industry     : {industry}
        Country      : Netherlands
        
        ━━━ SEO ISSUES FOUND ON THEIR SITE━━━
        {issues_text}
        
        ━━━ ANGLE & FORMAT ━━━
        Messaging angle : {messaging_angle}
        Target length   : {word_target}
        
        ━━━ WRITING RULES (follow every single one) ━━━
        1. {opening_instruction}
        2. Write the ENTIRE email (subject and body) in {lang_name.upper()}.
        3. Write like a smart human colleague, direct, warm, no corporate jargon.
        4. Mention at least TWO specific SEO issues from the list above by name.
        5. For each issue you mention, add ONE sentence explaining the concrete business impact.
        6. {cta_instruction}
        7. Sign off as: "Best,\\nThe Nekx SEO Team\\nnekx.nl"
        8. Subject line: under 55 characters, specific to this company.
        
        ━━━ OUTPUT FORMAT ━━━
        SUBJECT: [write the subject line here]
        BODY:
        [write the full email body here — include greeting, paragraphs, sign-off]
        Start now. Write the complete email without stopping early:"""
        
    
    def _parse_response(self, text, company):
        lines = text.strip().split('\n')
        subject, body_lines, in_body = "", [], False
        for line in lines:
            if line.upper().startswith("SUBJECT:"): subject = line[8:].strip().strip('"')
            elif line.upper().startswith("BODY:"): in_body = True
            elif in_body: body_lines.append(line)
        body = "\n".join(body_lines).strip()
        if not body: body = text # Fallback
        return subject, body