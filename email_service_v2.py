"""
Improved email service with Gemini AI support
"""
from typing import Any, Dict, List, Tuple, Optional
from .gemini_service import GeminiEmailGenerator


class EmailService:
    """Email generation service with Template or AI choice"""
    
    def __init__(self, gemini_api_key: Optional[str] = None, use_ai: bool = False):
        """
        Initialize email service
        
        Args:
            gemini_api_key: Gemini API key (optional)
            use_ai: If True, use Gemini AI, otherwise templates
        """
        self.use_ai = use_ai
        self.gemini_generator = None
        
        if use_ai:
            try:
                self.gemini_generator = GeminiEmailGenerator(gemini_api_key)
            except Exception as e:
                print(f"Warning: Gemini AI unavailable: {e}")
                print("Using templates instead")
                self.use_ai = False
    
    def render_email(
        self,
        lead: Dict[str, Any],
        experiment: Dict[str, Any],
        insights: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """
        Generate email (Template or AI depending on configuration)
        
        Args:
            lead: Prospect data
            experiment: Experiment configuration
            insights: Detected SEO insights
        
        Returns:
            Tuple (subject, body)
        """
        if self.use_ai and self.gemini_generator:
            return self._render_with_ai(lead, experiment, insights)
        else:
            return self._render_with_template(lead, experiment, insights)
    
    def _render_with_ai(
        self,
        lead: Dict[str, Any],
        experiment: Dict[str, Any],
        insights: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """Generate email with Gemini AI"""
        
        company = lead.get("company", "there")
        website = lead.get("website", "")
        industry = lead.get("industry", "general")
        messaging_angle = experiment.get("messaging_angle", "SEO")
        email_format = experiment.get("email_format", "short")
        
        #Extract SEO issue descriptions
        seo_issues = [i.get("issue_description", "") for i in insights if i.get("issue_description")]
        
        if not seo_issues:
            seo_issues = ["No specific issues detected yet"]
        
        try:
            subject, body = self.gemini_generator.generate_email(
                company=company,
                website=website,
                industry=industry,
                seo_issues=seo_issues,
                messaging_angle=messaging_angle,
                email_format=email_format
            )
            return subject, body
        except Exception as e:
            print(f"Error with Gemini: {e}")
            print("Falling back to template")
            return self._render_with_template(lead, experiment, insights)
    
    def _render_with_template(
        self,
        lead: Dict[str, Any],
        experiment: Dict[str, Any],
        insights: List[Dict[str, Any]]
    ) -> Tuple[str, str]:
        """Generate email with template (original version)"""
        
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
            body += "\nPS: If any of the points above are already fixed, just reply and I'll adjust."
        
        return subject, body


#Global instance (will be configured at startup)
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService(use_ai=False)  #Default: templates
    return _email_service


def configure_email_service(use_ai: bool = False, gemini_api_key: Optional[str] = None):
    """Configure email service at app startup"""
    global _email_service
    _email_service = EmailService(gemini_api_key=gemini_api_key, use_ai=use_ai)


#Compatibility function with old code
def render_email(
    lead: Dict[str, Any],
    experiment: Dict[str, Any],
    insights: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """Wrapper function for compatibility"""
    service = get_email_service()
    return service.render_email(lead, experiment, insights)