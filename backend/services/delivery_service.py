import os
import resend
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
resend.api_key = os.getenv("RESEND_API_KEY")

    
def send_email_via_resend(to_email: str, subject: str, html_body: str) -> dict:
    try:
        from_address = os.getenv("NEKX_FROM_EMAIL", "onboarding@resend.dev")
        
        # Hardcode my own email to verified Resend email address here for sandbox testing
        test_receiver = "k.harleen15@yahoo.fr"
        
        params = {
            "from": f"Nekx SEO Agent <{from_address}>",
            "to": [test_receiver],
            "subject": subject,
            "html": html_body,
        }
        
        email_response = resend.Emails.send(params)
        logger.info(f"Email sent successfully: {email_response['id']}")
        
        return {
            "success": True,
            "provider_id": email_response["id"],
            "error": None
        }
    except Exception as e:
        logger.error(f"Error during Resend delivery: {e}")
        return {
            "success": False,
            "provider_id": None,
            "error": str(e)
        }