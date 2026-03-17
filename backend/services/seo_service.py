from __future__ import annotations

import re
import urllib.request
from typing import Dict, List


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_CANONICAL_RE = re.compile(r'<link[^>]+rel=["\']canonical["\']', re.IGNORECASE)
_SCHEMA_RE = re.compile(r'application/ld\+json', re.IGNORECASE)


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "nekx-outreach-agent/0.1"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read()
        # Best-effort decode; HTML meta charset parsing is out of scope for v0.
        return raw.decode("utf-8", errors="replace")


def analyze_website(website: str) -> List[Dict]:
    url = website.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    insights: List[Dict] = []
    try:
        html = _fetch(url)
    except Exception as e:
        return [
            {
                "issue_type": "fetch_error",
                "issue_description": f"Could not fetch homepage ({e.__class__.__name__}).",
                "severity": 5,
            }
        ]

    title = _TITLE_RE.search(html)
    if not title or not title.group(1).strip():
        insights.append(
            {
                "issue_type": "missing_title",
                "issue_description": "Homepage is missing a <title> tag (or it is empty).",
                "severity": 8,
            }
        )

    meta_desc = _META_DESC_RE.search(html)
    if not meta_desc:
        insights.append(
            {
                "issue_type": "missing_meta_description",
                "issue_description": "Homepage appears to be missing a meta description.",
                "severity": 6,
            }
        )

    if not _CANONICAL_RE.search(html):
        insights.append(
            {
                "issue_type": "missing_canonical",
                "issue_description": "Homepage appears to be missing a canonical link tag.",
                "severity": 4,
            }
        )

    if not _SCHEMA_RE.search(html):
        insights.append(
            {
                "issue_type": "missing_schema",
                "issue_description": "No JSON-LD structured data detected on the homepage.",
                "severity": 3,
            }
        )

    return insights[:3] or [
        {"issue_type": "no_findings", "issue_description": "No basic issues detected on the homepage.", "severity": 1}
    ]
