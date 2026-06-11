from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv(".env")
    load_dotenv(".env.local")
except Exception:
    pass

from backend.config import settings


SAFE_EMAIL = "be.mevel@st.hanze.nl"
SEO_ISSUES = [
    "missing meta description",
    "weak title tag",
    "no local keywords on homepage",
    "no Google Business Profile mention",
    "missing structured data",
    "slow mobile page",
    "weak call-to-action",
    "no location-specific landing page",
    "poor heading structure",
    "thin homepage content",
]


@dataclass(frozen=True)
class VariantPlan:
    segment: str
    segment_label: str
    side: str
    value_proposition: str
    variant_label: str
    count: int
    opened: int
    replies: int
    positives: int
    demos: int


@dataclass
class CampaignEmail:
    simulation_id: str
    lead: dict[str, Any]
    plan: VariantPlan
    subject: str
    body: str
    opened: bool
    reply_sentiment: str | None
    reply_text: str | None
    provider_id: str | None = None
    email_id: int | None = None
    experiment_id: int | None = None
    ab_test_id: int | None = None

    @property
    def expected_action(self) -> str:
        if self.reply_sentiment == "demo_interest":
            return "open_and_reply_demo_interest"
        if self.reply_sentiment == "positive":
            return "open_and_reply_positive"
        if self.reply_sentiment == "not_interested":
            return "open_and_reply_not_interested"
        if self.opened:
            return "open_only"
        return "sent_only"


PLANS = [
    VariantPlan("multi_location", "Multi-Location Businesses", "A", "time_savings", "Time Savings", 11, 5, 1, 0, 0),
    VariantPlan("multi_location", "Multi-Location Businesses", "B", "scalability", "Scalability", 11, 7, 2, 1, 0),
    VariantPlan("premium_fine_dining", "Premium / Fine Dining", "A", "loss_framing", "Loss Framing", 10, 7, 2, 1, 1),
    VariantPlan("premium_fine_dining", "Premium / Fine Dining", "B", "growth_framing", "Growth Framing", 11, 5, 1, 0, 0),
    VariantPlan("independent_local", "Independent Local Businesses", "A", "convenience", "Convenience", 10, 6, 2, 1, 0),
    VariantPlan("independent_local", "Independent Local Businesses", "B", "expertise", "Expertise", 11, 5, 1, 1, 0),
]


REPLY_TEXT = {
    "not_interested": "Thanks for reaching out. We are not looking for SEO support right now, but good luck.",
    "positive": "Thanks, this looks relevant. Please send a bit more detail about how this would work.",
    "demo_interest": "This is interesting. Could we book a short demo or walkthrough next week?",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Populate and send the Nekx SEO Resend simulation.")
    parser.add_argument("--db-path", default=str(settings.db_path))
    parser.add_argument("--safe-email", default=SAFE_EMAIL)
    parser.add_argument("--from-email", default=SAFE_EMAIL)
    parser.add_argument("--send", action="store_true", help="Actually send the 64 messages through Resend.")
    parser.add_argument("--send-delay", type=float, default=0.2, help="Delay between Resend sends in seconds.")
    parser.add_argument("--send-log-path", default="data/resend_simulation_send_log.json")
    parser.add_argument("--leads-json", help="Read the 64 leads from a JSON snapshot instead of SQLite.")
    parser.add_argument("--skip-persist", action="store_true", help="Generate/send and write the send log without DB writes.")
    parser.add_argument("--persist-from-log", help="Persist a previously generated send log into SQLite.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    db_path = Path(args.db_path)

    if args.persist_from_log:
        campaign = load_send_log(Path(args.persist_from_log))
        backup_path = backup_db(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            persist_campaign(conn, campaign)
            validate_campaign(conn)
            write_checklist(campaign, Path("data/simulation_open_reply_checklist.csv"))
            write_report(campaign, Path("docs/SimulationData.md"), backup_path)
        finally:
            conn.close()
        print(f"Simulation populated from send log. DB backup: {backup_path}")
        print("Checklist: data/simulation_open_reply_checklist.csv")
        print("Report: docs/SimulationData.md")
        return

    if args.leads_json:
        leads = load_leads_json(Path(args.leads_json))
    else:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            leads = load_leads(conn)
        finally:
            conn.close()

    campaign = build_campaign(leads)
    render_campaign(campaign)

    if args.send:
        send_campaign(campaign, safe_email=args.safe_email, from_email=args.from_email, delay_seconds=args.send_delay)
    else:
        for email in campaign:
            email.provider_id = f"dry-run-{email.simulation_id.lower()}"

    write_send_log(campaign, Path(args.send_log_path))

    if args.skip_persist:
        print(f"Send log written: {args.send_log_path}")
        return

    backup_path = backup_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        persist_campaign(conn, campaign)
        validate_campaign(conn)
        write_checklist(campaign, Path("data/simulation_open_reply_checklist.csv"))
        write_report(campaign, Path("docs/SimulationData.md"), backup_path)
    finally:
        conn.close()

    print(f"Simulation populated. DB backup: {backup_path}")
    print("Checklist: data/simulation_open_reply_checklist.csv")
    print("Report: docs/SimulationData.md")


def backup_db(db_path: Path) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = db_path.with_name(f"{db_path.name}.bak-simulation-{stamp}")
    shutil.copy2(db_path, backup_path)
    return backup_path


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_leads(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM leads ORDER BY lead_id ASC").fetchall()
    leads = [dict(row) for row in rows]
    if len(leads) != 64:
        raise RuntimeError(f"Expected exactly 64 leads, found {len(leads)}")
    return leads


def load_leads_json(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Lead snapshot must contain a list.")
    leads = [dict(row) for row in raw]
    if len(leads) != 64:
        raise RuntimeError(f"Expected exactly 64 leads, found {len(leads)}")
    return leads


def build_campaign(leads: list[dict[str, Any]]) -> list[CampaignEmail]:
    campaign: list[CampaignEmail] = []
    lead_index = 0
    sim_index = 1
    for plan in PLANS:
        for variant_index in range(plan.count):
            lead = dict(leads[lead_index])
            lead["segment"] = plan.segment
            lead["industry"] = plan.segment_label
            opened = variant_index < plan.opened
            reply_sentiment = None
            if variant_index < plan.replies:
                if variant_index < plan.demos:
                    reply_sentiment = "demo_interest"
                elif variant_index < plan.positives:
                    reply_sentiment = "positive"
                else:
                    reply_sentiment = "not_interested"
            campaign.append(
                CampaignEmail(
                    simulation_id=f"NEKX-SIM-{sim_index:03d}",
                    lead=lead,
                    plan=plan,
                    subject="",
                    body="",
                    opened=opened,
                    reply_sentiment=reply_sentiment,
                    reply_text=REPLY_TEXT.get(reply_sentiment),
                )
            )
            lead_index += 1
            sim_index += 1
    return campaign


def render_campaign(campaign: list[CampaignEmail]) -> None:
    from backend.services.email_service import render_email

    for email in campaign:
        insights = build_insights_for_email(email)
        experiment = {
            "messaging_angle": email.plan.value_proposition,
            "email_format": "short",
            "subject_variant": f"{email.plan.variant_label} idea for {email.lead['company']}",
        }
        subject, body = render_email(email.lead, experiment, insights, language="en")
        email.subject = f"[{email.simulation_id}] {subject}"
        email.body = (
            "Simulation data - not live campaign results.\n"
            f"Safe inbox test for {email.lead['company']}; this was not sent to the prospect.\n\n"
            f"{body.strip()}"
        )


def build_insights_for_email(email: CampaignEmail) -> list[dict[str, Any]]:
    idx = int(email.simulation_id.rsplit("-", 1)[1]) - 1
    first = SEO_ISSUES[idx % len(SEO_ISSUES)]
    second = SEO_ISSUES[(idx + 3) % len(SEO_ISSUES)]
    return [
        {
            "issue_type": slugify(first),
            "issue_description": f"Simulation opportunity: {first}.",
            "severity": 4,
        },
        {
            "issue_type": slugify(second),
            "issue_description": f"Simulation opportunity: {second}.",
            "severity": 3,
        },
    ]


def send_campaign(
    campaign: list[CampaignEmail],
    *,
    safe_email: str,
    from_email: str,
    delay_seconds: float,
) -> None:
    from backend.services.delivery_service import send_email_via_resend

    for index, email in enumerate(campaign):
        result = send_email_via_resend(
            to_email=safe_email,
            from_email=from_email,
            reply_to=safe_email,
            subject=email.subject,
            html_body=to_html_email(email.body),
            tags=[
                {"name": "simulation_id", "value": email.simulation_id},
                {"name": "segment", "value": email.plan.segment},
                {"name": "variant", "value": email.plan.side},
            ],
        )
        if not result["success"]:
            if index == 0:
                raise RuntimeError(f"Resend preflight failed before bulk sending: {result['error']}")
            raise RuntimeError(f"Resend send failed after {index} successful sends: {result['error']}")
        email.provider_id = str(result["provider_id"])
        if index == 0:
            print("Resend preflight accepted first campaign email; continuing bulk send.")
        print(f"sent {index + 1:02d}/64 {email.simulation_id} provider_id={email.provider_id}")
        if delay_seconds > 0 and index < len(campaign) - 1:
            time.sleep(delay_seconds)


def persist_campaign(conn: sqlite3.Connection, campaign: list[CampaignEmail]) -> None:
    now = utcnow_iso()
    conn.execute("BEGIN")
    try:
        reset_campaign_tables(conn)
        segment_tests = create_ab_tests(conn, now)
        experiments = create_experiments(conn, now)
        for email in campaign:
            email.ab_test_id = segment_tests[email.plan.segment]
            email.experiment_id = experiments[(email.plan.segment, email.plan.side)]
            conn.execute(
                """
                UPDATE leads
                SET segment = ?, industry = ?, country = ?, status = ?
                WHERE lead_id = ?
                """,
                (email.plan.segment, email.plan.segment_label, "Netherlands", "contacted", email.lead["lead_id"]),
            )
            insert_insights(conn, email, now)
            cur = conn.execute(
                """
                INSERT INTO email_variants (
                  lead_id, experiment_id, ab_test_id, ab_side, subject, content,
                  delivery_status, created_at, sent_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'sent', ?, ?)
                """,
                (
                    email.lead["lead_id"],
                    email.experiment_id,
                    email.ab_test_id,
                    email.plan.side,
                    email.subject,
                    email.body,
                    now,
                    now,
                ),
            )
            email.email_id = int(cur.lastrowid)
            insert_events_and_reply(conn, email, now)
        insert_experiment_results(conn, campaign, now)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def reset_campaign_tables(conn: sqlite3.Connection) -> None:
    tables = [
        "email_events",
        "replies",
        "email_variants",
        "seo_insights",
        "experiment_results",
        "ab_test_variants",
        "ab_tests",
        "experiments",
    ]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    placeholders = ",".join("?" for _ in tables)
    conn.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", tables)


def create_ab_tests(conn: sqlite3.Connection, now: str) -> dict[str, int]:
    created: dict[str, int] = {}
    grouped = {
        "multi_location": ("Nekx SEO simulation - Multi-Location Businesses", 22, 11, 11, ["messaging_angle"]),
        "premium_fine_dining": ("Nekx SEO simulation - Premium / Fine Dining", 21, 10, 11, ["messaging_angle"]),
        "independent_local": ("Nekx SEO simulation - Independent Local Businesses", 21, 10, 11, ["messaging_angle"]),
    }
    for segment, (name, total, max_a, max_b, dimensions) in grouped.items():
        cur = conn.execute(
            """
            INSERT INTO ab_tests (
              name, segment, country, comparison_mode, max_emails_total, max_emails_a, max_emails_b,
              winner_metric, changed_dimensions, created_at, active
            )
            VALUES (?, ?, 'Netherlands', 'simulation', ?, ?, ?, 'reply_rate', ?, ?, 1)
            """,
            (name, segment, total, max_a, max_b, json.dumps(dimensions), now),
        )
        ab_test_id = int(cur.lastrowid)
        created[segment] = ab_test_id
        for plan in [p for p in PLANS if p.segment == segment]:
            conn.execute(
                """
                INSERT INTO ab_test_variants (
                  ab_test_id, side, messaging_angle, email_format, subject_variant, language, created_at
                )
                VALUES (?, ?, ?, 'short', ?, 'en', ?)
                """,
                (ab_test_id, plan.side, plan.value_proposition, plan.variant_label, now),
            )
    return created


def create_experiments(conn: sqlite3.Connection, now: str) -> dict[tuple[str, str], int]:
    created: dict[tuple[str, str], int] = {}
    for plan in PLANS:
        cur = conn.execute(
            """
            INSERT INTO experiments (
              segment, messaging_angle, email_format, max_emails_total, subject_variant, created_at, active
            )
            VALUES (?, ?, 'short', ?, ?, ?, 1)
            """,
            (plan.segment, plan.value_proposition, plan.count, plan.variant_label, now),
        )
        created[(plan.segment, plan.side)] = int(cur.lastrowid)
    return created


def insert_insights(conn: sqlite3.Connection, email: CampaignEmail, now: str) -> None:
    for insight in build_insights_for_email(email):
        conn.execute(
            """
            INSERT INTO seo_insights (lead_id, issue_type, issue_description, severity, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                email.lead["lead_id"],
                insight["issue_type"],
                insight["issue_description"],
                insight["severity"],
                now,
            ),
        )


def insert_events_and_reply(conn: sqlite3.Connection, email: CampaignEmail, now: str) -> None:
    if email.email_id is None:
        raise RuntimeError("email_id missing before event insert")
    conn.execute(
        "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, 'sent', ?, ?)",
        (email.email_id, email.provider_id, now),
    )
    if email.opened:
        conn.execute(
            "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, 'opened', ?, ?)",
            (email.email_id, email.provider_id, now),
        )
    if email.reply_sentiment:
        conn.execute(
            "INSERT INTO email_events (email_id, event_type, provider_id, event_time) VALUES (?, 'replied', ?, ?)",
            (email.email_id, email.provider_id, now),
        )
        conn.execute(
            """
            INSERT INTO replies (email_id, lead_id, reply_text, sentiment, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (email.email_id, email.lead["lead_id"], email.reply_text, email.reply_sentiment, now),
        )


def insert_experiment_results(conn: sqlite3.Connection, campaign: list[CampaignEmail], now: str) -> None:
    for plan in PLANS:
        rows = [email for email in campaign if email.plan.segment == plan.segment and email.plan.side == plan.side]
        if not rows:
            continue
        conn.execute(
            """
            INSERT INTO experiment_results (
              experiment_id, opens, replies, positive_replies, conversions, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                rows[0].experiment_id,
                sum(1 for email in rows if email.opened),
                sum(1 for email in rows if email.reply_sentiment),
                sum(1 for email in rows if email.reply_sentiment in {"positive", "demo_interest"}),
                sum(1 for email in rows if email.reply_sentiment == "demo_interest"),
                now,
            ),
        )


def validate_campaign(conn: sqlite3.Connection) -> None:
    checks = {
        "sent": "SELECT COUNT(*) FROM email_variants WHERE delivery_status = 'sent'",
        "opened": "SELECT COUNT(DISTINCT email_id) FROM email_events WHERE event_type = 'opened'",
        "replied": "SELECT COUNT(*) FROM replies",
        "positive": "SELECT COUNT(*) FROM replies WHERE sentiment IN ('positive', 'demo_interest')",
        "demo": "SELECT COUNT(*) FROM replies WHERE sentiment = 'demo_interest'",
    }
    expected = {"sent": 64, "opened": 35, "replied": 9, "positive": 4, "demo": 1}
    for name, sql in checks.items():
        actual = int(conn.execute(sql).fetchone()[0])
        if actual != expected[name]:
            raise RuntimeError(f"Validation failed for {name}: expected {expected[name]}, got {actual}")

    split_rows = conn.execute(
        """
        SELECT l.segment, ev.ab_side, COUNT(*) AS sent
        FROM email_variants ev
        JOIN leads l ON l.lead_id = ev.lead_id
        GROUP BY l.segment, ev.ab_side
        """
    ).fetchall()
    actual_split = {(row["segment"], row["ab_side"]): int(row["sent"]) for row in split_rows}
    expected_split = {
        ("multi_location", "A"): 11,
        ("multi_location", "B"): 11,
        ("premium_fine_dining", "A"): 10,
        ("premium_fine_dining", "B"): 11,
        ("independent_local", "A"): 10,
        ("independent_local", "B"): 11,
    }
    if actual_split != expected_split:
        raise RuntimeError(f"Validation failed for A/B split: {actual_split}")

    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_errors:
        raise RuntimeError(f"Foreign key validation failed: {fk_errors}")


def write_checklist(campaign: list[CampaignEmail], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "simulation_id",
                "email_id",
                "provider_id",
                "company",
                "segment",
                "variant",
                "value_proposition",
                "subject",
                "expected_action",
                "reply_sentiment",
            ],
        )
        writer.writeheader()
        for email in campaign:
            writer.writerow(
                {
                    "simulation_id": email.simulation_id,
                    "email_id": email.email_id,
                    "provider_id": email.provider_id,
                    "company": email.lead["company"],
                    "segment": email.plan.segment,
                    "variant": email.plan.side,
                    "value_proposition": email.plan.value_proposition,
                    "subject": email.subject,
                    "expected_action": email.expected_action,
                    "reply_sentiment": email.reply_sentiment or "",
                }
            )


def write_send_log(campaign: list[CampaignEmail], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = []
    for email in campaign:
        payload.append(
            {
                "simulation_id": email.simulation_id,
                "lead": email.lead,
                "plan": {
                    "segment": email.plan.segment,
                    "segment_label": email.plan.segment_label,
                    "side": email.plan.side,
                    "value_proposition": email.plan.value_proposition,
                    "variant_label": email.plan.variant_label,
                    "count": email.plan.count,
                    "opened": email.plan.opened,
                    "replies": email.plan.replies,
                    "positives": email.plan.positives,
                    "demos": email.plan.demos,
                },
                "subject": email.subject,
                "body": email.body,
                "opened": email.opened,
                "reply_sentiment": email.reply_sentiment,
                "reply_text": email.reply_text,
                "provider_id": email.provider_id,
            }
        )
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def load_send_log(path: Path) -> list[CampaignEmail]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Send log must contain a list.")
    campaign: list[CampaignEmail] = []
    for item in raw:
        plan_data = item["plan"]
        plan = VariantPlan(
            segment=plan_data["segment"],
            segment_label=plan_data["segment_label"],
            side=plan_data["side"],
            value_proposition=plan_data["value_proposition"],
            variant_label=plan_data["variant_label"],
            count=int(plan_data["count"]),
            opened=int(plan_data["opened"]),
            replies=int(plan_data["replies"]),
            positives=int(plan_data["positives"]),
            demos=int(plan_data["demos"]),
        )
        campaign.append(
            CampaignEmail(
                simulation_id=item["simulation_id"],
                lead=item["lead"],
                plan=plan,
                subject=item["subject"],
                body=item["body"],
                opened=bool(item["opened"]),
                reply_sentiment=item.get("reply_sentiment"),
                reply_text=item.get("reply_text"),
                provider_id=item.get("provider_id"),
            )
        )
    if len(campaign) != 64:
        raise ValueError(f"Expected 64 send-log rows, found {len(campaign)}")
    return campaign


def write_report(campaign: list[CampaignEmail], path: Path, backup_path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    real_resend_sent = all(email.provider_id and not str(email.provider_id).startswith("dry-run-") for email in campaign)
    delivery_note = (
        "Real Resend provider IDs were recorded for all 64 campaign messages."
        if real_resend_sent
        else "Dry-run provider IDs are recorded. No real Resend campaign messages are represented by this file."
    )
    proof_sentence = (
        "send safe test messages through Resend"
        if real_resend_sent
        else "prepare safe test messages for Resend"
    )
    sample_emails = "\n\n".join(
        f"### {email.simulation_id} - {email.lead['company']}\n\n"
        f"Subject: {email.subject}\n\n"
        f"```text\n{email.body}\n```"
        for email in campaign[:3]
    )
    lines = [
        "# Nekx SEO Simulation Data",
        "",
        "Simulation data - not live campaign results.",
        "",
        f"- Database backup: `{backup_path}`",
        "- Sent mailbox: `be.mevel@st.hanze.nl`",
        "- Sender mailbox: `be.mevel@st.hanze.nl`",
        "- Total simulated leads/emails: 64",
        f"- Delivery status: {delivery_note}",
        "- Opens to perform for Resend evidence: 35",
        "- Replies to perform for report evidence: 9",
        "- Positive replies: 4",
        "- Demo interest replies: 1",
        "",
        "## A/B Matrix",
        "",
        "| Segment | Variant A | Variant B | Expected winner |",
        "| --- | --- | --- | --- |",
        "| Multi-Location Businesses | Time Savings | Scalability | B - Scalability |",
        "| Premium / Fine Dining | Loss Framing | Growth Framing | A - Loss Framing |",
        "| Independent Local Businesses | Convenience | Expertise | A - Convenience |",
        "",
        "## Results",
        "",
        "| Segment | Variant | Sent | Opened | Replies | Positive | Demo interest |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for plan in PLANS:
        rows = [email for email in campaign if email.plan.segment == plan.segment and email.plan.side == plan.side]
        lines.append(
            f"| {plan.segment_label} | {plan.side} - {plan.variant_label} | {len(rows)} | "
            f"{sum(1 for email in rows if email.opened)} | "
            f"{sum(1 for email in rows if email.reply_sentiment)} | "
            f"{sum(1 for email in rows if email.reply_sentiment in {'positive', 'demo_interest'})} | "
            f"{sum(1 for email in rows if email.reply_sentiment == 'demo_interest')} |"
        )
    lines.extend(
        [
            "",
            "## Checklist",
            "",
            "Use `data/simulation_open_reply_checklist.csv` to decide which messages to open and reply to in the safe inbox. Messages are identifiable by the `[NEKX-SIM-###]` subject prefix.",
            "",
            "## Sample Emails",
            "",
            sample_emails,
            "",
            "## Interpretation",
            "",
            f"This simulation proves that the workflow can process leads, generate email variants, {proof_sentence}, store provider IDs, and compare A/B performance across the three agreed segments. It does not prove real-world campaign performance because all engagement outcomes are simulated.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def to_html_email(body: str) -> str:
    escaped = html.escape(body).replace("\n", "<br>\n")
    return f"<div style=\"font-family:Arial,sans-serif;font-size:15px;line-height:1.45;color:#111827\">{escaped}</div>"


def slugify(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_").replace("/", "_")


if __name__ == "__main__":
    main()
