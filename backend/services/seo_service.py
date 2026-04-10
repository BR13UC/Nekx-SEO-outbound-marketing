from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Mapping

from ..config import settings


def _load_case_data() -> Dict[str, Any]:
    path = Path(settings.case_insights_path)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _random_improvement(case: Mapping[str, Any]) -> str:
    metrics = case.get("metrics", [])
    if not metrics:
        return "traffic and discoverability improved"

    metric = random.choice(metrics)
    label = str(metric.get("label", "SEO metric")).strip() or "SEO metric"
    value = str(metric.get("value", "")).strip()
    if value:
        return f"{label} improved by {value}"
    return f"{label} improved"


def analyze_lead_opportunities(lead: Mapping[str, Any], website: str | None = None) -> List[Dict[str, Any]]:
    # Temporary simplified behavior: pick one random proven client improvement.
    _ = website
    data = _load_case_data()
    cases = data.get("cases", [])
    company = str(lead.get("company") or "this company").strip()

    if not cases:
        return [
            {
                "issue_type": "case_based_random_improvement",
                "issue_description": (
                    f"Nekx has seen measurable SEO improvements in comparable clients; "
                    f"{company} could likely benefit from a similar quick-win approach."
                ),
                "severity": 5,
            }
        ]

    chosen_case = random.choice(cases)
    case_name = str(chosen_case.get("name", "a comparable client")).strip() or "a comparable client"
    improvement = _random_improvement(chosen_case)

    return [
        {
            "issue_type": "case_based_random_improvement",
            "issue_description": (
                f"A similar Nekx client ({case_name}) saw {improvement}. "
                f"This could be a practical SEO opportunity for {company} as well."
            ),
            "severity": 5,
        }
    ]
