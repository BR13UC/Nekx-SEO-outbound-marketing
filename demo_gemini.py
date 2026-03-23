#!/usr/bin/env python3
"""
Demo - Gemini AI for Nekx SEO
Generates personalized emails for 3 real Dutch companies.
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


#3 Dutch companies with realistic SEO issues
DUTCH_COMPANIES = [
    {
        "company": "Restaurant De Drie Gezusters",
        "website": "https://dedrie.nl",
        "industry": "restaurant",
        "seo_issues": [
            "Homepage is missing a meta description (shows blank in Google results)",
            "Page load time is 4.8 seconds on mobile — Google threshold is 2.5s",
            "No structured data (schema.org/Restaurant) — Google can't show opening hours or menu in search",
            "Only 3 pages are indexed — the menu page is blocked by robots.txt",
        ],
        "messaging_angle": "local visibility in Groningen",
        "email_format": "short",
    },
    {
        "company": "Bakkerij Van der Berg",
        "website": "https://bakkerijvandenberg.nl",
        "industry": "bakery / local retail",
        "seo_issues": [
            "Google Business Profile is not linked to the website",
            "No HTTPS — site still runs on HTTP, causing 'Not Secure' warning in browsers",
            "Title tags on 8 product pages are duplicates of each other",
            "Zero backlinks from local Groningen directories or food blogs",
        ],
        "messaging_angle": "getting found by locals searching 'bakery near me'",
        "email_format": "medium",
    },
    {
        "company": "Adviesbureau Hoffman & Partners",
        "website": "https://hoffmanpartners.nl",
        "industry": "B2B consulting / financial advisory",
        "seo_issues": [
            "Website has no blog or content — competing firms rank for 'belastingadvies Groningen' with articles",
            "Core Web Vitals score: LCP 6.1s (Poor) — likely due to unoptimized hero image",
            "No internal linking between service pages — Google can't establish topical authority",
            "Contact page is not indexed — missing from Google entirely",
        ],
        "messaging_angle": "generating leads through organic search instead of paid ads",
        "email_format": "medium",
    },
]


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'═' * 70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'═' * 70}{Colors.ENDC}\n")


def print_email(subject: str, body: str, company: str):
    print(c(Colors.CYAN, f"\n  Company : {company}"))
    print(c(Colors.BOLD, f"  SUBJECT : ") + subject)
    print(c(Colors.YELLOW, "  " + "─" * 66))
    for line in body.splitlines():
        print(f"  {line}")
    print(c(Colors.YELLOW, "  " + "─" * 66))


def run_demo():
    print_header("NEKX SEO — GEMINI EMAIL GENERATOR")

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

    print(c(Colors.GREEN, f"  Gemini connected. Generating {len(DUTCH_COMPANIES)} personalized emails...\n"))

    results = []

    for i, company_data in enumerate(DUTCH_COMPANIES, 1):
        company_name = company_data["company"]
        print(c(Colors.BOLD, f"  [{i}/{len(DUTCH_COMPANIES)}] Generating email for {company_name}..."))

        try:
            subject, body = generator.generate_email(
                company=company_data["company"],
                website=company_data["website"],
                industry=company_data["industry"],
                seo_issues=company_data["seo_issues"],
                messaging_angle=company_data["messaging_angle"],
                email_format=company_data["email_format"],
            )
            results.append((company_name, subject, body))
            print(c(Colors.GREEN, f"  Done ({len(body.split())} words)\n"))

        except Exception as e:
            print(c(Colors.RED, f"  Error for {company_name}: {e}\n"))
            results.append((company_name, "ERROR", str(e)))

        if i < len(DUTCH_COMPANIES):
            time.sleep(1)

    #Print all results 
    print_header("GENERATED EMAILS")

    for company_name, subject, body in results:
        print_email(subject, body, company_name)

    #Summary
    print_header("SUMMARY")
    for company_name, subject, body in results:
        status = c(Colors.GREEN, "✓") if subject != "ERROR" else c(Colors.RED, "✗")
        words = len(body.split()) if subject != "ERROR" else 0
        print(f"  {status}  {company_name:<40} {words} words  |  subject: {subject[:50]}")

    cost = generator.estimate_cost(len(DUTCH_COMPANIES))
    print(f"\n  Estimated cost: ${cost['total_cost_usd']} USD ({cost['note']})\n")


if __name__ == "__main__":
    try:
        run_demo()
    except KeyboardInterrupt:
        print(c(Colors.YELLOW, "\n\n  Interrupted. Goodbye!\n"))
        sys.exit(0)