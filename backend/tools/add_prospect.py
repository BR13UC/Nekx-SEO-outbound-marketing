import argparse

from backend.database import connect, init_db, utcnow_iso


def prompt_required(value: str | None, label: str) -> str:
    if value:
        return value.strip()
    while True:
        typed = input(f"{label}: ").strip()
        if typed:
            return typed
        print(f"{label} is required.")


def prompt_optional(value: str | None, label: str) -> str | None:
    if value is not None:
        clean = value.strip()
        return clean or None
    typed = input(f"{label} (optional): ").strip()
    return typed or None


def insert_prospect(args: argparse.Namespace) -> int:
    company = prompt_required(args.company, "Company")
    contact_email = prompt_required(args.contact_email, "Contact email")
    website = prompt_required(args.website, "Website")
    segment = prompt_required(args.segment, "Segment")
    industry = prompt_optional(args.industry, "Industry")
    country = prompt_optional(args.country, "Country")
    source = prompt_optional(args.source, "Source")
    status = (args.status or "new").strip() or "new"

    conn = connect()
    try:
        init_db(conn)
        now = utcnow_iso()
        cur = conn.execute(
            """
            INSERT INTO leads (company, contact_email, website, segment, industry, country, source, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (company, contact_email, website, segment, industry, country, source, now, status),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Add a new prospect lead to the local database.")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--contact-email", help="Contact email")
    parser.add_argument("--website", help="Company website URL")
    parser.add_argument("--segment", help="Target segment")
    parser.add_argument("--industry", help="Industry")
    parser.add_argument("--country", help="Country")
    parser.add_argument("--source", help="Lead source")
    parser.add_argument("--status", default="new", help="Lead status (default: new)")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    lead_id = insert_prospect(args)
    print(f"✅ Prospect added with lead_id={lead_id}")


if __name__ == "__main__":
    main()
