import argparse

from backend.database import connect, init_db
from backend.services.email_service import render_email


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate one email using current email service settings.")
    parser.add_argument("--lead-id", type=int, required=True)
    parser.add_argument("--experiment-id", type=int, required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    conn = connect()
    try:
        init_db(conn)
        lead = conn.execute("SELECT * FROM leads WHERE lead_id = ?", (args.lead_id,)).fetchone()
        experiment = conn.execute(
            "SELECT * FROM experiments WHERE experiment_id = ?",
            (args.experiment_id,),
        ).fetchone()
        insights = conn.execute(
            "SELECT * FROM seo_insights WHERE lead_id = ? ORDER BY severity DESC, created_at DESC LIMIT 3",
            (args.lead_id,),
        ).fetchall()

        if not lead:
            raise SystemExit("lead not found")
        if not experiment:
            raise SystemExit("experiment not found")

        subject, body = render_email(dict(lead), dict(experiment), [dict(i) for i in insights])
        print("SUBJECT:")
        print(subject)
        print("")
        print("BODY:")
        print(body)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
