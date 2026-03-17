from typing import Any, Dict, List, Tuple


def render_email(lead: Dict[str, Any], experiment: Dict[str, Any], insights: List[Dict[str, Any]]) -> Tuple[str, str]:
    # v0: deterministic template. OpenAI + Resend wiring comes next.
    company = lead.get("company", "there")
    website = lead.get("website", "")
    angle = experiment.get("messaging_angle", "SEO")
    email_format = experiment.get("email_format", "short")

    subject = experiment.get("subject_variant") or f"Quick {angle} idea for {company}"

    bullets = ""
    if insights:
        bullets = "\n".join([f"- {i['issue_description']}" for i in insights])
    else:
        bullets = "- (No insights yet. Run /seo/analyze first.)"

    body = f"""Hi {company},

I took a quick look at {website} and noticed:
{bullets}

If helpful, I can share a 5 minute walkthrough of how to address these (and how we automate parts of it in Nekx).

Best,
Nekx SEO

Unsubscribe: reply with "unsubscribe" and I will not contact you again.
"""

    if str(email_format).lower() == "medium":
        body += "\nPS: If any of the points above are already fixed, just reply and I’ll adjust."

    return subject, body
