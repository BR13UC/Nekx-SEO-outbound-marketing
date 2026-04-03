#!/usr/bin/env python3
"""
Demo - Gemini AI for Nekx SEO
Generates personalized emails using A/B testing for the Bakery segment
"""
import os
import sys
import time

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def c(color, text):
    return f"{color}{text}{Colors.ENDC}"

#CONFIGURATION
LANGUAGE = "en"
ANGLE_A = "local visibility and getting found by neighbors"
ANGLE_B = "technical performance, speed and mobile optimization"

#SEGMENT: BAKERY
BAKERY_SEGMENT = [
    {
        "company": "Bakkerij De Groot",
        "website": "https://degrootbakker.nl",
        "industry": "bakery",
        "seo_issues": [
            "Slow mobile speed (4.5s load time)",
            "Google Business Profile not linked to website"
        ],
        "email_format": "short",
        "variant": "A" #LOCAL VISIBILITY TEST
    },
    {
        "company": "Bakkerij Janssen",
        "website": "https://janssen-bakker.nl",
        "industry": "bakery",
        "seo_issues": [
            "Website is not secure (Missing HTTPS)",
            "Duplicate title tags on product pages"
        ],
        "email_format": "medium",
        "variant": "B" #TECHNICAL TEST
    }
]

def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'═' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")

def print_email(subject: str, body: str, company: str, variant: str):
    color = Colors.GREEN if variant == "A" else Colors.BLUE
    print(c(Colors.CYAN, f"\n  Company : {company} ") + c(color, f"({variant})"))
    print(c(Colors.BOLD, f"  SUBJECT : ") + subject)
    print(c(Colors.YELLOW, "  " + "─" * 66))
    for line in body.splitlines():
        print(f"  {line}")
    print(c(Colors.YELLOW, "  " + "─" * 66))

def run_demo():
    print_header("NEKX SEO — GEMINI EMAIL GENERATOR (BAKERY SEGMENT)")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(c(Colors.RED, "  GOOGLE_API_KEY not found in environment."))
        print(c(Colors.YELLOW, "  Set it with:  export GOOGLE_API_KEY='your-key-here'"))
        sys.exit(1)

    try:
        from gemini_service import GeminiEmailGenerator
        generator = GeminiEmailGenerator(api_key)
    except ImportError:
        print(c(Colors.RED, "  gemini_service.py not found. Make sure it's in the same folder."))
        sys.exit(1)

    print(c(Colors.GREEN, f"  Gemini connected. Generating {len(BAKERY_SEGMENT)} personalized emails...\n"))

    results = []

    for i, data in enumerate(BAKERY_SEGMENT, 1):
        company_name = data["company"]
        variant = data["variant"]
        angle = ANGLE_A if variant == "A" else ANGLE_B
        
        print(c(Colors.BOLD, f"  [{i}/{len(BAKERY_SEGMENT)}] Generating {variant} for {company_name}..."))

        try:
            #Call the Gemini service using the variant-specific angle
            subject, body = generator.generate_email(
                company=data["company"],
                website=data["website"],
                industry=data["industry"],
                seo_issues=data["seo_issues"],
                messaging_angle=angle,
                email_format=data["email_format"],
                language=LANGUAGE
            )
            results.append((company_name, subject, body, variant))
            print(c(Colors.GREEN, f"  Done ({len(body.split())} words)\n"))

        except Exception as e:
            print(c(Colors.RED, f"  Error for {company_name}: {e}\n"))
            results.append((company_name, "ERROR", str(e), variant))

        if i < len(BAKERY_SEGMENT):
            time.sleep(1)

    #Viewing generated emails
    for company_name, subject, body, variant in results:
        if subject != "ERROR":
            print_email(subject, body, company_name, variant)

    #Summary
    print_header("SUMMARY")
    for company_name, subject, body, variant in results:
        status = c(Colors.GREEN, "✓") if subject != "ERROR" else c(Colors.RED, "✗")
        words = len(body.split()) if subject != "ERROR" else 0
        v_label = c(Colors.GREEN if variant == "A" else Colors.BLUE, variant)
        print(f"  {status}  [{v_label}] {company_name:<30} {words:>3} words | subject: {subject[:40]}...")
if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print(c(Colors.YELLOW, "\n\n  Interrupted. Goodbye!\n"))
        sys.exit(0)